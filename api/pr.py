"""
GET /api/pr
-----------
Proportional Representation (PR) results — votes and allocated seats per party.

Response:
{
  "updated_at":   "...",
  "total_pr_seats": 110,
  "parties": [
    {
      "party_id":      "CPN-UML",
      "party_short":   "CPN-UML",
      "party_name_np": "नेकपा (एमाले)",
      "party_name_en": "CPN (UML)",
      "party_color":   "#D94040",
      "votes":         1850000,
      "vote_pct":      27.4,
      "seats":         28
    },
    ...
  ]
}
"""

from http.server import BaseHTTPRequestHandler
import json, sys, os
sys.path.insert(0, os.path.dirname(__file__))

from _core import scrape_pr, timestamp, cors_headers


class handler(BaseHTTPRequestHandler):

    def do_OPTIONS(self):
        self.send_response(200)
        for k, v in cors_headers().items():
            self.send_header(k, v)
        self.end_headers()

    def do_GET(self):
        try:
            parties = scrape_pr()
            data    = {"updated_at": timestamp(), "total_pr_seats": 110, "parties": parties}
            body    = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
            status  = 200
        except Exception as exc:
            body   = json.dumps({"error": str(exc)}).encode()
            status = 500

        self.send_response(status)
        for k, v in cors_headers().items():
            self.send_header(k, v)
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)
