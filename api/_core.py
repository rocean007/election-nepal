"""
api/_core.py
============
Shared scraping engine used by every Vercel endpoint.
Scraped live from result.election.gov.np on each request.
Vercel edge cache (s-maxage=60) prevents hammering ECN.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import datetime, timezone
from typing import Any

import requests
from bs4 import BeautifulSoup

# ─────────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────────

ECN_BASE = "https://result.election.gov.np"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept":          "text/html,application/xhtml+xml,*/*;q=0.8",
    "Accept-Language": "ne,en-US;q=0.9,en;q=0.7",
    "Referer":         ECN_BASE,
}

TIMEOUT = 15   # seconds — Vercel functions time out at 10s on hobby, 60s on pro

# Province mapping
PROVINCES: dict[int, dict] = {
    1: {"name": "Koshi",          "name_np": "कोशी प्रदेश"},
    2: {"name": "Madhesh",        "name_np": "मधेश प्रदेश"},
    3: {"name": "Bagmati",        "name_np": "बागमती प्रदेश"},
    4: {"name": "Gandaki",        "name_np": "गण्डकी प्रदेश"},
    5: {"name": "Lumbini",        "name_np": "लुम्बिनी प्रदेश"},
    6: {"name": "Karnali",        "name_np": "कर्णाली प्रदेश"},
    7: {"name": "Sudurpashchim",  "name_np": "सुदूरपश्चिम प्रदेश"},
}

# Constituency → Province (1-indexed, 165 total)
def province_for(const_id: int) -> int:
    if   1  <= const_id <= 25:  return 1
    elif 26 <= const_id <= 45:  return 2
    elif 46 <= const_id <= 77:  return 3
    elif 78 <= const_id <= 100: return 4
    elif 101 <= const_id <= 128: return 5
    elif 129 <= const_id <= 144: return 6
    elif 145 <= const_id <= 165: return 7
    return 0

# Party registry (Nepali + English → normalised metadata)
PARTIES: dict[str, dict] = {
    "नेपाली काँग्रेस":                      {"id": "NC",      "short": "NC",      "color": "#2B6FD4", "en": "Nepali Congress"},
    "नेकपा (एमाले)":                        {"id": "CPN-UML", "short": "CPN-UML", "color": "#D94040", "en": "CPN (UML)"},
    "नेकपा (माओवादी केन्द्र)":              {"id": "CPN-MC",  "short": "Maoist",  "color": "#9B59D0", "en": "CPN (Maoist Centre)"},
    "राष्ट्रिय स्वतन्त्र पार्टी":           {"id": "RSP",     "short": "RSP",     "color": "#3DB87A", "en": "Rastriya Swatantra Party"},
    "राष्ट्रिय प्रजातन्त्र पार्टी":         {"id": "RPP",     "short": "RPP",     "color": "#E8A020", "en": "Rastriya Prajatantra Party"},
    "जनमत पार्टी":                          {"id": "JANMAT",  "short": "Janmat",  "color": "#E85A20", "en": "Janmat Party"},
    "लोकतान्त्रिक समाजवादी पार्टी नेपाल":  {"id": "LSP",     "short": "LSP",     "color": "#F59E0B", "en": "Loktantrik Samajwadi Party"},
    "नागरिक उन्मुक्ति पार्टी":              {"id": "NUP",     "short": "NUP",     "color": "#06B6D4", "en": "Nagarik Unmukti Party"},
    "नेकपा (एकीकृत समाजवादी)":             {"id": "CPN-US",  "short": "CPN-US",  "color": "#7C3AED", "en": "CPN (Unified Socialist)"},
    "स्वतन्त्र":                            {"id": "IND",     "short": "IND",     "color": "#6B7280", "en": "Independent"},
    # English fallbacks
    "Nepali Congress":              {"id": "NC",      "short": "NC",      "color": "#2B6FD4", "en": "Nepali Congress"},
    "CPN (UML)":                    {"id": "CPN-UML", "short": "CPN-UML", "color": "#D94040", "en": "CPN (UML)"},
    "CPN (Maoist Centre)":          {"id": "CPN-MC",  "short": "Maoist",  "color": "#9B59D0", "en": "CPN (Maoist Centre)"},
    "Rastriya Swatantra Party":     {"id": "RSP",     "short": "RSP",     "color": "#3DB87A", "en": "Rastriya Swatantra Party"},
    "Rastriya Prajatantra Party":   {"id": "RPP",     "short": "RPP",     "color": "#E8A020", "en": "Rastriya Prajatantra Party"},
    "Independent":                  {"id": "IND",     "short": "IND",     "color": "#6B7280", "en": "Independent"},
}

# ─────────────────────────────────────────────────────────────────
# TEXT HELPERS
# ─────────────────────────────────────────────────────────────────

_DEVA = str.maketrans("०१२३४५६७८९", "0123456789")

def norm(text: str) -> str:
    if not text:
        return ""
    text = unicodedata.normalize("NFC", text)
    return re.sub(r"\s+", " ", text).strip()

def to_int(text: str) -> int | None:
    if not text:
        return None
    cleaned = re.sub(r"[^\d०-९]", "", text).translate(_DEVA)
    try:
        return int(cleaned) if cleaned else None
    except ValueError:
        return None

def cell_text(tag) -> str:
    return norm(tag.get_text(separator=" ")) if tag else ""

def resolve_party(raw: str) -> dict:
    name = norm(raw)
    if name in PARTIES:
        return PARTIES[name]
    for key, meta in PARTIES.items():
        if key in name or name in key:
            return meta
    return {"id": "OTHER", "short": norm(raw)[:10], "color": "#888888", "en": norm(raw)}

def timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

# ─────────────────────────────────────────────────────────────────
# HTTP
# ─────────────────────────────────────────────────────────────────

_session: requests.Session | None = None

def session() -> requests.Session:
    global _session
    if _session is None:
        _session = requests.Session()
        _session.headers.update(HEADERS)
        # Warm-up hit to capture ASP.NET session cookie
        try:
            _session.get(ECN_BASE, timeout=TIMEOUT)
        except Exception:
            pass
    return _session

def fetch(url: str, params: dict | None = None) -> BeautifulSoup | None:
    try:
        r = session().get(url, params=params, timeout=TIMEOUT)
        r.raise_for_status()
        r.encoding = "utf-8"
        return BeautifulSoup(r.text, "lxml")
    except Exception:
        return None

# ─────────────────────────────────────────────────────────────────
# SCRAPE: PARTY SEATS
# ─────────────────────────────────────────────────────────────────

def scrape_party_seats() -> list[dict]:
    soup = fetch(ECN_BASE + "/")
    if not soup:
        return []

    results: list[dict] = []
    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        if len(rows) < 3:
            continue
        for tr in rows[1:]:
            cells = tr.find_all(["td", "th"])
            if len(cells) < 2:
                continue
            texts = [cell_text(c) for c in cells]
            party_raw = texts[0]
            if not party_raw or len(party_raw) < 2:
                continue
            nums = [n for n in (to_int(t) for t in texts[1:]) if n is not None]
            if not nums:
                continue
            meta = resolve_party(party_raw)
            results.append({
                "party_id":      meta["id"],
                "party_short":   meta["short"],
                "party_name_en": meta["en"],
                "party_name_np": party_raw,
                "party_color":   meta["color"],
                "fptp_won":      nums[0] if len(nums) > 0 else 0,
                "fptp_leading":  nums[1] if len(nums) > 1 else 0,
                "total_fptp":    (nums[0] if len(nums) > 0 else 0) + (nums[1] if len(nums) > 1 else 0),
            })
        if results:
            break

    return sorted(results, key=lambda x: x["total_fptp"], reverse=True)

# ─────────────────────────────────────────────────────────────────
# SCRAPE: SINGLE CONSTITUENCY
# ─────────────────────────────────────────────────────────────────

def scrape_constituency(const_id: int) -> dict:
    url  = f"{ECN_BASE}/NationalResult.aspx"
    soup = fetch(url, params={"constNo": const_id})

    pno   = province_for(const_id)
    pinfo = PROVINCES.get(pno, {})

    if not soup:
        return {
            "id": const_id, "status": "error",
            "province_no": pno, "province_name": pinfo.get("name",""),
            "candidates": [], "total_votes": 0,
        }

    # Name from heading
    name_np = ""
    for tag in soup.find_all(["h1","h2","h3","h4"]):
        t = norm(tag.get_text())
        if t and len(t) > 3:
            name_np = t
            break

    # Candidates from table
    candidates: list[dict] = []
    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        if len(rows) < 2:
            continue
        batch: list[dict] = []
        for tr in rows:
            cells = tr.find_all("td")
            if len(cells) < 2:
                continue
            texts = [cell_text(c) for c in cells]

            # Votes — last numeric column
            votes = None
            for t in reversed(texts):
                v = to_int(t)
                if v is not None:
                    votes = v
                    break
            if votes is None:
                continue

            party_raw  = texts[1] if len(texts) > 1 else ""
            party_meta = resolve_party(party_raw)

            # Photos
            imgs       = tr.find_all("img")
            photo_url  = None
            symbol_url = None
            for img in imgs:
                src = img.get("src", "")
                if "photo" in src.lower() or "candidate" in src.lower():
                    photo_url  = ECN_BASE + "/" + src.lstrip("/")
                elif "symbol" in src.lower():
                    symbol_url = ECN_BASE + "/" + src.lstrip("/")

            batch.append({
                "name_np":       norm(texts[0]),
                "party_name_np": norm(party_raw),
                "party_id":      party_meta["id"],
                "party_short":   party_meta["short"],
                "party_color":   party_meta["color"],
                "votes":         votes,
                "photo_url":     photo_url,
                "symbol_url":    symbol_url,
            })

        if batch:
            candidates = batch
            break

    candidates.sort(key=lambda c: c["votes"], reverse=True)
    total_votes = sum(c["votes"] for c in candidates)
    for i, c in enumerate(candidates):
        c["rank"]     = i + 1
        c["vote_pct"] = round(c["votes"] / total_votes * 100, 2) if total_votes else 0.0

    page_text = norm(soup.get_text()).lower()
    if "घोषित" in page_text or "declared" in page_text:
        status = "declared"
    elif total_votes > 0:
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
        "name_np":          name_np,
        "province_no":      pno,
        "province_name":    pinfo.get("name", ""),
        "province_name_np": pinfo.get("name_np", ""),
        "status":           status,
        "total_votes":      total_votes,
        "total_candidates": len(candidates),
        "winner":           winner,
        "candidates":       candidates,
        "source_url":       f"{ECN_BASE}/NationalResult.aspx?constNo={const_id}",
    }

# ─────────────────────────────────────────────────────────────────
# SCRAPE: PR RESULTS
# ─────────────────────────────────────────────────────────────────

def scrape_pr() -> list[dict]:
    soup = fetch(ECN_BASE + "/PRResult.aspx")
    if not soup:
        return []

    results: list[dict] = []
    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        if len(rows) < 3:
            continue
        for tr in rows[1:]:
            cells = tr.find_all("td")
            if len(cells) < 2:
                continue
            texts    = [cell_text(c) for c in cells]
            party_raw = texts[0]
            if not party_raw or len(party_raw) < 2:
                continue
            nums  = [n for n in (to_int(t) for t in texts[1:]) if n is not None]
            meta  = resolve_party(party_raw)
            pct   = 0.0
            for t in texts:
                if "%" in t:
                    try:
                        pct = float(t.replace("%","").strip())
                    except ValueError:
                        pass
            results.append({
                "party_id":      meta["id"],
                "party_short":   meta["short"],
                "party_name_np": party_raw,
                "party_name_en": meta["en"],
                "party_color":   meta["color"],
                "votes":         nums[0] if nums else 0,
                "vote_pct":      pct,
                "seats":         nums[-1] if len(nums) > 1 else 0,
            })
        if results:
            break

    return sorted(results, key=lambda r: r["votes"], reverse=True)

# ─────────────────────────────────────────────────────────────────
# CORS RESPONSE BUILDER
# ─────────────────────────────────────────────────────────────────

def cors_headers() -> dict:
    return {
        "Access-Control-Allow-Origin":  "*",
        "Access-Control-Allow-Methods": "GET, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
        "Content-Type":                 "application/json; charset=utf-8",
        "Cache-Control":                "s-maxage=60, stale-while-revalidate=120",
    }
