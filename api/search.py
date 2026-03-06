"""
GET /api/search?q=<name>
------------------------
Search candidates by name across all 165 constituencies.
Returns matching candidates with their constituency + vote info.

Query params:
  q        — candidate name (min 2 chars, Nepali or English)
  province — optional province filter (e.g. Bagmati)
  party    — optional party filter   (e.g. NC, CPN-UML, RSP)

Example:
  /api/search?q=Gagan
  /api/search?q=रेनु&province=Bagmati
  /api/search?q=sharma&party=NC

Response:
{
  "updated_at": "...",
  "query": "Gagan",
  "count": 3,
  "results": [
    {
      "rank":            1,
      "name_np":         "गगन थापा",
      "party_id":        "NC",
      "party_short":     "NC",
      "votes":           39854,
      "vote_pct":        42.1,
      "constituency_id": 45,
      "constituency_name": "...",
      "province_name":   "Bagmati",
      "status":          "counting"
    }
  ]
}
"""

from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import json, sys, os, concurrent.futures
sys.path.insert(0, os.path.dirname(__file__))

from _core import (
    scrape_constituency, timestamp, cors_headers,
    province_for, PROVINCES,
)

# Province name → number
_P2N = {info["name"].lower(): pno for pno, info in PROVINCES.items()}

# All 165 IDs
ALL_IDS = list(range(1, 166))


def search_candidates(
    query: str,
    province_filter: str | None,
    party_filter: str | None,
) -> list[dict]:
    query = query.lower().strip()

    # Determine which constituency IDs to search
    if province_filter:
        pno      = _P2N.get(province_filter.lower())
        ids_pool = [cid for cid in ALL_IDS if province_for(cid) == pno] if pno else ALL_IDS
    else:
        ids_pool = ALL_IDS

    def fetch_and_match(cid: int) -> list[dict]:
        try:
            r     = scrape_constituency(cid)
            found = []
            for cand in r.get("candidates", []):
                name = cand.get("name_np", "").lower()
                pid  = cand.get("party_id", "").lower()
                if query in name:
                    if party_filter and party_filter.lower() not in pid:
                        continue
                    found.append({
                        "rank":              cand["rank"],
                        "name_np":           cand["name_np"],
                        "party_id":          cand["party_id"],
                        "party_short":       cand["party_short"],
                        "party_color":       cand["party_color"],
                        "votes":             cand["votes"],
                        "vote_pct":          cand["vote_pct"],
                        "constituency_id":   cid,
                        "constituency_name": r.get("name_np", ""),
                        "province_name":     r.get("province_name", ""),
                        "status":            r.get("status", ""),
                        "photo_url":         cand.get("photo_url"),
                    })
            return found
        except Exception:
            return []

    # Parallel search — cap at 30 constituencies to stay within Vercel timeout
    cap  = min(len(ids_pool), 30)
    pool_ids = ids_pool[:cap]

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
        batch = list(pool.map(fetch_and_match, pool_ids))

    results = [item for sublist in batch for item in sublist]
    results.sort(key=lambda x: x["votes"], reverse=True)
    return results


class handler(BaseHTTPRequestHandler):

    def do_OPTIONS(self):
        self.send_response(200)
        for k, v in cors_headers().items():
            self.send_header(k, v)
        self.end_headers()

    def do_GET(self):
        params   = parse_qs(urlparse(self.path).query)
        q        = params.get("q",        [""])[0].strip()
        province = params.get("province", [None])[0]
        party    = params.get("party",    [None])[0]

        if len(q) < 2:
            body   = json.dumps({"error": "Query ?q= must be at least 2 characters."}).encode()
            status = 400
        else:
            try:
                results = search_candidates(q, province, party)
                data    = {
                    "updated_at": timestamp(),
                    "query":      q,
                    "filters":    {"province": province, "party": party},
                    "count":      len(results),
                    "results":    results,
                }
                body   = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
                status = 200
            except Exception as exc:
                body   = json.dumps({"error": str(exc)}).encode()
                status = 500

        self.send_response(status)
        for k, v in cors_headers().items():
            self.send_header(k, v)
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)
