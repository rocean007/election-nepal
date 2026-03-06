"""
GET /api/party-seats
--------------------
Party-wise FPTP + PR seat breakdown.

Response:
{
  "updated_at": "...",
  "seats_total": 275,
  "majority_mark": 138,
  "parties": [
    {
      "party_id":      "CPN-UML",
      "party_short":   "CPN-UML",
      "party_name_en": "CPN (UML)",
      "party_name_np": "नेकपा (एमाले)",
      "party_color":   "#D94040",
      "fptp_won":      47,
      "fptp_leading":  12,
      "total_fptp":    59,
      "pr_seats":      28,
      "total_seats":   87
    },
    ...
  ]
}
"""

from http.server import BaseHTTPRequestHandler
import json, sys, os
sys.path.insert(0, os.path.dirname(__file__))

from _core import scrape_party_seats, scrape_pr, timestamp, cors_headers


class handler(BaseHTTPRequestHandler):

    def do_OPTIONS(self):
        self.send_response(200)
        for k, v in cors_headers().items():
            self.send_header(k, v)
        self.end_headers()

    def do_GET(self):
        try:
            party_seats = scrape_party_seats()
            pr_results  = scrape_pr()
            pr_map      = {r["party_id"]: r["seats"] for r in pr_results}

            parties = []
            for p in party_seats:
                pr_s = pr_map.get(p["party_id"], 0)
                parties.append({
                    **p,
                    "pr_seats":    pr_s,
                    "total_seats": p["total_fptp"] + pr_s,
                })
            parties.sort(key=lambda x: x["total_seats"], reverse=True)

            data   = {"updated_at": timestamp(), "seats_total": 275, "majority_mark": 138, "parties": parties}
            body   = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
            status = 200
        except Exception as exc:
            body   = json.dumps({"error": str(exc)}).encode("utf-8")
            status = 500

        self.send_response(status)
        for k, v in cors_headers().items():
            self.send_header(k, v)
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)
