"""
GET /api/constituency/[id]
--------------------------
Full result for a single constituency by its numeric ID (1–165).

Examples:
  /api/constituency/45
  /api/constituency/101

Response:
{
  "updated_at":       "...",
  "id":               45,
  "name_np":          "...",
  "province_no":      3,
  "province_name":    "Bagmati",
  "province_name_np": "बागमती प्रदेश",
  "status":           "counting" | "declared" | "pending",
  "total_votes":      84500,
  "total_candidates": 12,
  "winner": {
    "name":        "...",
    "party_id":    "NC",
    "party_short": "NC",
    "votes":       34000,
    "margin":      2100
  },
  "candidates": [
    {
      "rank":          1,
      "name_np":       "...",
      "party_id":      "NC",
      "party_short":   "NC",
      "party_color":   "#2B6FD4",
      "votes":         34000,
      "vote_pct":      40.24,
      "photo_url":     "https://result.election.gov.np/...",
      "symbol_url":    "https://result.election.gov.np/..."
    },
    ...
  ],
  "source_url": "https://result.election.gov.np/NationalResult.aspx?constNo=45"
}
"""

from http.server import BaseHTTPRequestHandler
import json, re, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from api._core import scrape_constituency, timestamp, cors_headers


class handler(BaseHTTPRequestHandler):

    def do_OPTIONS(self):
        self.send_response(200)
        for k, v in cors_headers().items():
            self.send_header(k, v)
        self.end_headers()

    def do_GET(self):
        # Extract numeric ID from path  /api/constituency/45
        match = re.search(r"/constituency/(\d+)", self.path)

        if not match:
            body   = json.dumps({"error": "Missing constituency ID. Use /api/constituency/45"}).encode()
            status = 400
        else:
            const_id = int(match.group(1))
            if not (1 <= const_id <= 165):
                body   = json.dumps({"error": "ID must be between 1 and 165"}).encode()
                status = 400
            else:
                try:
                    result = scrape_constituency(const_id)
                    data   = {"updated_at": timestamp(), **result}
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
