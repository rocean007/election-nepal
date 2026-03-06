"""
async_scraper.py — High-speed async scraper using aiohttp + asyncio

Fetches all 165 constituencies concurrently (rate-limited).
Falls back to the sync Playwright scraper for JS-gated pages.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

import aiohttp
from bs4 import BeautifulSoup

from config import (
    ECN_BASE_URL, REQUEST_HEADERS, TIMEOUT_SECONDS,
    RATE_LIMIT_DELAY, CONCURRENCY, CONSTITUENCY_PROVINCE, PROVINCES,
    ALL_CONSTITUENCY_IDS,
)
from utils import get_logger, normalize_text, extract_number, clean_name, get_text
from scraper import _resolve_party, _is_empty_page, fetch_with_playwright

log = get_logger("async_scraper")


# ─────────────────────────────────────────────────────────────────
# ASYNC HTTP
# ─────────────────────────────────────────────────────────────────

async def async_fetch(
    session: aiohttp.ClientSession,
    url: str,
    params: dict | None = None,
    retries: int = 3,
    backoff: float = 2.0,
) -> str | None:
    """Async GET with retries and exponential back-off."""
    delay = backoff
    for attempt in range(1, retries + 1):
        try:
            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=TIMEOUT_SECONDS)) as resp:
                resp.raise_for_status()
                html = await resp.text(encoding="utf-8", errors="replace")
                log.debug(f"[async] {url} → {resp.status}")
                return html
        except Exception as exc:
            if attempt == retries:
                log.error(f"[async] Failed {url} after {retries} attempts: {exc}")
                return None
            log.warning(f"[async] Attempt {attempt}/{retries} failed for {url}: {exc} — waiting {delay:.1f}s")
            await asyncio.sleep(delay)
            delay *= backoff
    return None


# ─────────────────────────────────────────────────────────────────
# PARSE CONSTITUENCY PAGE
# ─────────────────────────────────────────────────────────────────

def _parse_constituency_html(html: str, const_id: int) -> dict:
    """Parse a rendered constituency page HTML into structured data."""
    soup = BeautifulSoup(html, "lxml")
    province_no   = CONSTITUENCY_PROVINCE.get(const_id, 0)
    province_info = PROVINCES.get(province_no, {})

    # ── Constituency name ──
    const_name = ""
    for tag in soup.find_all(["h1", "h2", "h3", "h4"]):
        t = normalize_text(tag.get_text())
        if t and len(t) > 3:
            const_name = t
            break

    # ── Candidates ──
    candidates: list[dict] = []
    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        if len(rows) < 2:
            continue
        data_rows: list[dict] = []
        for tr in rows:
            cells = tr.find_all("td")
            if len(cells) < 2:
                continue
            texts = [get_text(c) for c in cells]

            vote_val = None
            for t in reversed(texts):
                v = extract_number(t)
                if v is not None:
                    vote_val = v
                    break
            if vote_val is None:
                continue

            imgs       = tr.find_all("img")
            photo_src  = None
            symbol_src = None
            for img in imgs:
                src = img.get("src", "")
                if "photo" in src.lower() or "candidate" in src.lower():
                    photo_src = ECN_BASE_URL + "/" + src.lstrip("/")
                elif "symbol" in src.lower():
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

    candidates.sort(key=lambda c: c["votes"], reverse=True)
    total_votes = sum(c["votes"] for c in candidates)

    for i, c in enumerate(candidates):
        c["rank"]     = i + 1
        c["vote_pct"] = round(c["votes"] / total_votes * 100, 2) if total_votes else 0.0

    page_text = normalize_text(soup.get_text()).lower()
    if "घोषित" in page_text or "declared" in page_text:
        status = "declared"
    elif candidates and total_votes > 0:
        status = "counting"
    else:
        status = "pending"

    winner = None
    if candidates:
        top    = candidates[0]
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
        "url":              f"{ECN_BASE_URL}/NationalResult.aspx?constNo={const_id}",
    }


# ─────────────────────────────────────────────────────────────────
# ASYNC CONSTITUENCY WORKER
# ─────────────────────────────────────────────────────────────────

async def fetch_constituency(
    session: aiohttp.ClientSession,
    const_id: int,
    semaphore: asyncio.Semaphore,
    progress_callback=None,
) -> dict:
    url = f"{ECN_BASE_URL}/NationalResult.aspx?constNo={const_id}"

    async with semaphore:
        await asyncio.sleep(RATE_LIMIT_DELAY)
        html = await async_fetch(session, url)

    if html and not _is_empty_page(html):
        result = _parse_constituency_html(html, const_id)
    else:
        # JS-rendered — fall back to sync Playwright in a thread
        log.warning(f"[yellow]Constituency {const_id} needs Playwright[/]")
        loop = asyncio.get_event_loop()
        html = await loop.run_in_executor(None, fetch_with_playwright, url, "table")
        result = _parse_constituency_html(html, const_id) if html else {
            "id": const_id, "status": "error", "candidates": []
        }

    if progress_callback:
        progress_callback(const_id)

    return result


# ─────────────────────────────────────────────────────────────────
# MAIN ASYNC RUNNER
# ─────────────────────────────────────────────────────────────────

async def scrape_all_constituencies_async(
    const_ids: list[int] | None = None,
    concurrency: int = CONCURRENCY,
) -> list[dict]:
    """
    Scrape all (or selected) constituencies concurrently.

    Args:
        const_ids:   list of constituency IDs to scrape (default: all 165)
        concurrency: max simultaneous HTTP requests

    Returns: list of constituency result dicts
    """
    ids = const_ids or ALL_CONSTITUENCY_IDS
    semaphore = asyncio.Semaphore(concurrency)
    results: list[dict] = []
    completed = 0
    total = len(ids)

    def on_done(cid: int) -> None:
        nonlocal completed
        completed += 1
        log.info(f"  [{completed}/{total}] Constituency {cid} done")

    connector = aiohttp.TCPConnector(limit=concurrency, ssl=False)
    timeout   = aiohttp.ClientTimeout(total=TIMEOUT_SECONDS)

    async with aiohttp.ClientSession(
        headers=REQUEST_HEADERS,
        connector=connector,
        timeout=timeout,
    ) as session:
        tasks = [
            fetch_constituency(session, cid, semaphore, on_done)
            for cid in ids
        ]
        results = await asyncio.gather(*tasks, return_exceptions=False)

    results.sort(key=lambda r: r.get("id", 0))
    log.info(f"[green]Async scrape complete: {len(results)} constituencies[/]")
    return results


def run_async_scraper(const_ids: list[int] | None = None, concurrency: int = CONCURRENCY) -> list[dict]:
    """Sync wrapper around the async scraper — call this from synchronous code."""
    return asyncio.run(scrape_all_constituencies_async(const_ids, concurrency))
