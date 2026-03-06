"""
scraper.py — Core scraping engine for result.election.gov.np

Strategy:
  1. Try plain requests + BeautifulSoup (fast, no JS needed for most pages)
  2. If the response looks empty / JS-gated, fall back to Playwright (headless Chromium)
  3. All methods are retried with exponential back-off
"""

from __future__ import annotations

import time
from typing import Any

import requests
from bs4 import BeautifulSoup

from config import (
    ECN_BASE_URL, ENDPOINTS, REQUEST_HEADERS,
    TIMEOUT_SECONDS, RATE_LIMIT_DELAY,
    PARTY_REGISTRY, CONSTITUENCY_PROVINCE, PROVINCES,
)
from utils import (
    get_logger, retry, normalize_text, clean_name,
    extract_number, deva_to_int, get_text, get_table_rows,
)

log = get_logger("scraper")

# ─────────────────────────────────────────────────────────────────
# SESSION
# ─────────────────────────────────────────────────────────────────

def make_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(REQUEST_HEADERS)
    # Persist cookies across requests (handles ASP.NET session tokens)
    return session


_SESSION: requests.Session | None = None


def get_session() -> requests.Session:
    global _SESSION
    if _SESSION is None:
        _SESSION = make_session()
        # Warm up: hit main page to get any session cookies
        try:
            _SESSION.get(ECN_BASE_URL, timeout=TIMEOUT_SECONDS)
        except Exception:
            pass
    return _SESSION


# ─────────────────────────────────────────────────────────────────
# LOW-LEVEL FETCH
# ─────────────────────────────────────────────────────────────────

@retry(max_attempts=4, backoff=2.0, exceptions=(requests.RequestException,))
def fetch_html(url: str, params: dict | None = None, data: dict | None = None) -> str:
    """
    Fetch a URL and return raw HTML.
    - GET if data is None, POST otherwise.
    - Rate-limited to be polite to the ECN server.
    """
    session = get_session()
    time.sleep(RATE_LIMIT_DELAY)

    if data:
        resp = session.post(url, params=params, data=data, timeout=TIMEOUT_SECONDS)
    else:
        resp = session.get(url, params=params, timeout=TIMEOUT_SECONDS)

    resp.raise_for_status()
    resp.encoding = "utf-8"
    log.debug(f"Fetched {url} → {resp.status_code} ({len(resp.text)} chars)")
    return resp.text


def parse(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "lxml")


# ─────────────────────────────────────────────────────────────────
# PLAYWRIGHT FALLBACK (for heavily JS-rendered pages)
# ─────────────────────────────────────────────────────────────────

def fetch_with_playwright(url: str, wait_selector: str = "table", timeout_ms: int = 25000) -> str:
    """
    Use Playwright headless Chromium to render a JS-heavy page.
    Returns the fully-rendered HTML.

    Requires: playwright install chromium
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        log.error("Playwright not installed. Run: pip install playwright && playwright install chromium")
        raise

    log.info(f"[yellow]Using Playwright for {url}[/]")
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page(
            user_agent=REQUEST_HEADERS["User-Agent"],
            extra_http_headers={"Accept-Language": "ne,en-US;q=0.9"},
        )
        page.goto(url, wait_until="networkidle", timeout=timeout_ms)
        try:
            page.wait_for_selector(wait_selector, timeout=timeout_ms)
        except Exception:
            log.warning(f"Selector '{wait_selector}' not found — returning page as-is")
        html = page.content()
        browser.close()
    return html


# ─────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────

def _is_empty_page(html: str) -> bool:
    """Heuristic: page has no table data and is short."""
    return len(html) < 3000 or "<table" not in html.lower()


def _resolve_party(raw_name: str) -> dict:
    """Look up a party name in the registry, return metadata or a stub."""
    name = normalize_text(raw_name)
    if name in PARTY_REGISTRY:
        return PARTY_REGISTRY[name]
    # Fuzzy: check if any known key is a substring
    for key, meta in PARTY_REGISTRY.items():
        if key in name or name in key:
            return meta
    return {"id": "OTHER", "short": name[:10], "color": "#888888", "en": name}


# ─────────────────────────────────────────────────────────────────
# SCRAPER: PARTY SEATS (main page)
# ─────────────────────────────────────────────────────────────────

def scrape_party_seats() -> list[dict]:
    """
    Scrape the main page party-wise FPTP summary table.
    Returns list of dicts: { party_id, party_name, party_name_np,
                              fptp_won, fptp_leading, total_fptp }
    """
    log.info("Scraping party seats summary…")
    html = fetch_html(ENDPOINTS["home"])

    if _is_empty_page(html):
        log.warning("Main page looks empty — trying Playwright")
        html = fetch_with_playwright(ENDPOINTS["home"])

    soup = parse(html)
    results: list[dict] = []

    # ECN main page has a "दलगत स्थिति" summary table
    # We look for any table where rows have a party name + numeric columns
    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        if len(rows) < 3:
            continue

        # Check if this looks like a party results table
        header_text = normalize_text(rows[0].get_text()).lower() if rows else ""
        has_party_col = any(kw in header_text for kw in ["दल", "party", "पार्टी"])

        for tr in rows[1:]:
            cells = tr.find_all(["td", "th"])
            if len(cells) < 3:
                continue
            texts = [get_text(c) for c in cells]

            # First cell should be a party name (contains non-ASCII or known keyword)
            party_raw = texts[0]
            if not party_raw or len(party_raw) < 2:
                continue

            nums = [extract_number(t) for t in texts[1:]]
            nums = [n for n in nums if n is not None]
            if not nums:
                continue

            party_meta = _resolve_party(party_raw)
            fptp_won     = nums[0] if len(nums) > 0 else 0
            fptp_leading = nums[1] if len(nums) > 1 else 0
            total_fptp   = fptp_won + fptp_leading

            results.append({
                "party_id":       party_meta["id"],
                "party_short":    party_meta["short"],
                "party_name_en":  party_meta["en"],
                "party_name_np":  party_raw,
                "party_color":    party_meta["color"],
                "fptp_won":       fptp_won,
                "fptp_leading":   fptp_leading,
                "total_fptp":     total_fptp,
            })

        if results:
            break   # found the right table

    log.info(f"  → {len(results)} parties found")
    return results


# ─────────────────────────────────────────────────────────────────
# SCRAPER: CONSTITUENCY LIST
# ─────────────────────────────────────────────────────────────────

def scrape_constituency_list() -> list[dict]:
    """
    Scrape the list of all 165 constituencies with basic metadata.
    Returns: [ { id, name_np, district, province_no, province_name, link } ]
    """
    log.info("Scraping constituency list…")
    html = fetch_html(ENDPOINTS["constituency_list"])

    if _is_empty_page(html):
        html = fetch_with_playwright(ENDPOINTS["constituency_list"])

    soup = parse(html)
    constituencies: list[dict] = []

    for tr in soup.find_all("tr"):
        cells = tr.find_all(["td", "th"])
        if len(cells) < 2:
            continue
        link_tag = tr.find("a", href=True)
        if not link_tag:
            continue

        href  = link_tag["href"]
        texts = [get_text(c) for c in cells]

        # Extract constituency ID from query string e.g. ?constNo=12
        import re
        id_match = re.search(r"constNo=(\d+)", href, re.I)
        const_id = int(id_match.group(1)) if id_match else None

        if const_id is None:
            # Try to parse from text
            num = extract_number(texts[0])
            const_id = num

        if const_id is None:
            continue

        province_no = CONSTITUENCY_PROVINCE.get(const_id, 0)
        province_info = PROVINCES.get(province_no, {})

        constituencies.append({
            "id":            const_id,
            "name_np":       normalize_text(texts[0]) if texts else "",
            "district":      normalize_text(texts[1]) if len(texts) > 1 else "",
            "province_no":   province_no,
            "province_name": province_info.get("name", ""),
            "url":           f"{ECN_BASE_URL}/{href.lstrip('/')}",
        })

    # Fallback: if we got nothing, generate stubs for all 165
    if not constituencies:
        log.warning("Could not parse constituency list — generating stubs")
        for cid in range(1, 166):
            pno = CONSTITUENCY_PROVINCE.get(cid, 0)
            pinfo = PROVINCES.get(pno, {})
            constituencies.append({
                "id":            cid,
                "name_np":       f"निर्वाचन क्षेत्र {cid}",
                "district":      "",
                "province_no":   pno,
                "province_name": pinfo.get("name", ""),
                "url":           f"{ECN_BASE_URL}/NationalResult.aspx?constNo={cid}",
            })

    constituencies.sort(key=lambda x: x["id"])
    log.info(f"  → {len(constituencies)} constituencies")
    return constituencies


# ─────────────────────────────────────────────────────────────────
# SCRAPER: SINGLE CONSTITUENCY RESULT
# ─────────────────────────────────────────────────────────────────

def scrape_constituency(const_id: int) -> dict:
    """
    Full result for a single constituency.

    Returns:
    {
        id, name_np, district, province_no, province_name,
        status,          # "declared" | "counting" | "pending"
        total_votes,
        total_candidates,
        reported_pct,    # % of ballots counted (if available)
        winner: { name, party_id, party_short, votes, margin },
        candidates: [
            { rank, name_np, party_name_np, party_id, party_short,
              party_color, votes, vote_pct, photo_url, symbol_url }
        ]
    }
    """
    url = f"{ECN_BASE_URL}/NationalResult.aspx?constNo={const_id}"
    log.debug(f"Scraping constituency {const_id}: {url}")

    html = fetch_html(url)
    if _is_empty_page(html):
        html = fetch_with_playwright(url, wait_selector="table")

    soup = parse(html)
    province_no  = CONSTITUENCY_PROVINCE.get(const_id, 0)
    province_info = PROVINCES.get(province_no, {})

    # ── Parse constituency name from heading ──
    const_name = ""
    for tag in soup.find_all(["h1", "h2", "h3", "h4", "strong"]):
        t = normalize_text(tag.get_text())
        if t and len(t) > 3:
            const_name = t
            break

    # ── Parse candidate table ──
    candidates: list[dict] = []
    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        if len(rows) < 2:
            continue

        data_rows = []
        for tr in rows:
            cells = tr.find_all("td")
            if len(cells) < 3:
                continue
            texts = [get_text(c) for c in cells]

            # Find vote count: first column that is purely numeric
            vote_val = None
            for t in reversed(texts):   # votes usually in last columns
                v = extract_number(t)
                if v is not None and v >= 0:
                    vote_val = v
                    break

            if vote_val is None:
                continue

            # Photo / symbol images
            imgs = tr.find_all("img")
            photo_src  = None
            symbol_src = None
            for img in imgs:
                src = img.get("src", "")
                if "photo" in src.lower() or "candidate" in src.lower():
                    photo_src = ECN_BASE_URL + "/" + src.lstrip("/")
                elif "symbol" in src.lower() or "chinha" in src.lower():
                    symbol_src = ECN_BASE_URL + "/" + src.lstrip("/")

            cand_name  = clean_name(texts[0]) if texts else ""
            party_raw  = texts[1] if len(texts) > 1 else ""
            party_meta = _resolve_party(party_raw)

            data_rows.append({
                "name_np":       cand_name,
                "party_name_np": normalize_text(party_raw),
                "party_id":      party_meta["id"],
                "party_short":   party_meta["short"],
                "party_color":   party_meta["color"],
                "votes":         vote_val,
                "photo_url":     photo_src,
                "symbol_url":    symbol_src,
            })

        if data_rows:
            candidates = data_rows
            break

    # Sort by votes descending, assign rank and percentage
    candidates.sort(key=lambda c: c["votes"], reverse=True)
    total_votes = sum(c["votes"] for c in candidates)

    for i, c in enumerate(candidates):
        c["rank"]     = i + 1
        c["vote_pct"] = round(c["votes"] / total_votes * 100, 2) if total_votes else 0.0

    # Determine status
    if candidates and candidates[0]["votes"] > 0:
        # Heuristic: if top candidate has >0 votes, at least counting
        # Try to find "declared" / "घोषित" text on page
        page_text = normalize_text(soup.get_text()).lower()
        if "घोषित" in page_text or "declared" in page_text or "विजयी" in page_text:
            status = "declared"
        else:
            status = "counting"
    else:
        status = "pending"

    winner = None
    if candidates:
        top = candidates[0]
        margin = top["votes"] - candidates[1]["votes"] if len(candidates) > 1 else top["votes"]
        winner = {
            "name":        top["name_np"],
            "party_id":    top["party_id"],
            "party_short": top["party_short"],
            "votes":       top["votes"],
            "margin":      margin,
        }

    return {
        "id":               const_id,
        "name_np":          const_name,
        "province_no":      province_no,
        "province_name":    province_info.get("name", ""),
        "province_name_np": province_info.get("name_np", ""),
        "status":           status,
        "total_votes":      total_votes,
        "total_candidates": len(candidates),
        "winner":           winner,
        "candidates":       candidates,
        "url":              url,
    }


# ─────────────────────────────────────────────────────────────────
# SCRAPER: PROPORTIONAL REPRESENTATION
# ─────────────────────────────────────────────────────────────────

def scrape_pr_results() -> list[dict]:
    """
    Scrape proportional representation (PR) results.
    Returns: [ { party_id, party_short, party_name_np, votes, vote_pct, seats } ]
    """
    log.info("Scraping PR results…")
    html = fetch_html(ENDPOINTS["pr_result"])

    if _is_empty_page(html):
        html = fetch_with_playwright(ENDPOINTS["pr_result"])

    soup = parse(html)
    results: list[dict] = []

    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        if len(rows) < 3:
            continue
        for tr in rows[1:]:
            cells = tr.find_all("td")
            if len(cells) < 2:
                continue
            texts = [get_text(c) for c in cells]
            party_raw  = texts[0]
            if not party_raw or len(party_raw) < 2:
                continue
            nums       = [extract_number(t) for t in texts[1:] if extract_number(t) is not None]
            party_meta = _resolve_party(party_raw)

            results.append({
                "party_id":      party_meta["id"],
                "party_short":   party_meta["short"],
                "party_name_np": normalize_text(party_raw),
                "party_name_en": party_meta["en"],
                "party_color":   party_meta["color"],
                "votes":         nums[0] if nums else 0,
                "vote_pct":      float(texts[2].replace("%", "")) if len(texts) > 2 and "%" in texts[2] else 0.0,
                "seats":         nums[-1] if len(nums) > 1 else 0,
            })
        if results:
            break

    results.sort(key=lambda r: r["votes"], reverse=True)
    log.info(f"  → {len(results)} parties in PR results")
    return results


# ─────────────────────────────────────────────────────────────────
# SCRAPER: CANDIDATE BIOGRAPHY / DETAIL
# ─────────────────────────────────────────────────────────────────

def scrape_candidate_detail(candidate_id: int | None = None,
                             const_id: int | None = None,
                             candidate_name: str | None = None) -> dict | None:
    """
    Scrape personal detail card for a candidate (schedule-10 modal).
    """
    url = ENDPOINTS["candidate_detail"]
    params: dict[str, Any] = {}
    if candidate_id:
        params["candID"] = candidate_id
    elif const_id:
        params["constNo"] = const_id

    html = fetch_html(url, params=params)
    if _is_empty_page(html):
        return None

    soup = parse(html)
    detail: dict[str, str] = {}

    # The detail modal has label:value patterns in table cells or definition lists
    for row in soup.find_all("tr"):
        cells = row.find_all("td")
        if len(cells) >= 2:
            label = normalize_text(cells[0].get_text())
            value = normalize_text(cells[1].get_text())
            if label:
                detail[label] = value

    # Photo
    photo = soup.find("img", {"id": lambda x: x and "photo" in x.lower()})
    if photo:
        src = photo.get("src", "")
        detail["photo_url"] = ECN_BASE_URL + "/" + src.lstrip("/") if src else None

    return detail if detail else None
