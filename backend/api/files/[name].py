"""
GET /api/province/[name]
------------------------
All constituency winners/leaders for a given province.

Valid names (case-insensitive):
  Koshi, Madhesh, Bagmati, Gandaki, Lumbini, Karnali, Sudurpashchim

Example:  /api/province/Bagmati

Response:
{
  "updated_at":    "...",
  "province_name": "Bagmati",
  "province_no":   3,
  "total_constituencies": 32,
  "constituencies": [ { id, name_np, status, winner, total_votes } ]
}
"""

from http.server import BaseHTTPRequestHandler
import json, re, sys, os, concurrent.futures
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from api._core import (
    scrape_constituency, timestamp, cors_headers,
    PROVINCES, province_for,
)

# Constituency IDs per province
PROVINCE_CONST_IDS: dict[int, list[int]] = {
    pno: [cid for cid in range(1, 166) if province_for(cid) == pno]
    for pno in PROVINCES
}

# Name → province_no lookup (case-insensitive)
NAME_TO_PNO: dict[str, int] = {
    info["name"].lower(): pno for pno, info in PROVINCES.items()
}


def scrape_province_slim(pno: int) -> list[dict]:
    """Scrape all constituencies for a province, returning slim summaries."""
    ids = PROVINCE_CONST_IDS.get(pno, [])

    def fetch_slim(cid: int) -> dict:
        r = scrape_constituency(cid)
        return {
            "id":           r["id"],
            "name_np":      r["name_np"],
            "status":       r["status"],
            "total_votes":  r["total_votes"],
            "total_candidates": r["total_candidates"],
            "winner":       r.get("winner"),
            "source_url":   r["source_url"],
        }

    # Parallel fetch — Vercel allows up to ~50 threads per function
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(fetch_slim, ids))

    return sorted(results, key=lambda x: x["id"])


class handler(BaseHTTPRequestHandler):

    def do_OPTIONS(self):
        self.send_response(200)
        for k, v in cors_headers().items():
            self.send_header(k, v)
        self.end_headers()

    def do_GET(self):
        match = re.search(r"/province/([^/?]+)", self.path)

        if not match:
            body   = json.dumps({"error": "Missing province name. Use /api/province/Bagmati"}).encode()
            status = 400
        else:
            raw_name = match.group(1).strip()
            pno      = NAME_TO_PNO.get(raw_name.lower())

            if pno is None:
                valid  = list(NAME_TO_PNO.keys())
                body   = json.dumps({"error": f"Unknown province '{raw_name}'. Valid: {valid}"}).encode()
                status = 400
            else:
                try:
                    pinfo  = PROVINCES[pno]
                    consts = scrape_province_slim(pno)
                    data   = {
                        "updated_at":    timestamp(),
                        "province_no":   pno,
                        "province_name": pinfo["name"],
                        "province_name_np": pinfo["name_np"],
                        "total_constituencies": len(consts),
                        "constituencies": consts,
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
