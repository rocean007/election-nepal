"""
GET /api/live-summary
---------------------
Full dashboard snapshot — party standings, progress, province breakdown.
The root payload. Most websites only need this one endpoint.

Response shape:
{
  "meta":     { updated_at, source, election_en, election_np },
  "seats":    { total, fptp_total, pr_total, majority_mark },
  "progress": { declared, counting, pending, declared_pct },
  "leading_party": { ... },
  "party_standings": [ ... ],
  "provinces": [ ... ]
}
"""

from http.server import BaseHTTPRequestHandler
import json
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from _core import (
    scrape_party_seats, scrape_pr, timestamp,
    PROVINCES, province_for, cors_headers,
)


def build_summary() -> dict:
    party_seats = scrape_party_seats()
    pr_results  = scrape_pr()

    # Merge FPTP + PR
    pr_map = {r["party_id"]: r["seats"] for r in pr_results}
    standings = []
    for p in party_seats:
        pr_s = pr_map.get(p["party_id"], 0)
        standings.append({
            **p,
            "pr_seats":    pr_s,
            "total_seats": p["total_fptp"] + pr_s,
        })
    standings.sort(key=lambda x: x["total_seats"], reverse=True)

    return {
        "meta": {
            "updated_at":  timestamp(),
            "source":      "result.election.gov.np",
            "election_en": "Nepal House of Representatives Election 2082",
            "election_np": "प्रतिनिधि सभा निर्वाचन, २०८२",
            "date":        "2026-03-05",
        },
        "seats": {
            "total":          275,
            "fptp_total":     165,
            "pr_total":       110,
            "majority_mark":  138,
        },
        "leading_party":   standings[0] if standings else None,
        "party_standings": standings,
        "provinces": [
            {
                "province_no":  pno,
                "name":         pinfo["name"],
                "name_np":      pinfo["name_np"],
                "constituencies_total": sum(
                    1 for cid in range(1, 166) if province_for(cid) == pno
                ),
            }
            for pno, pinfo in PROVINCES.items()
        ],
    }


class handler(BaseHTTPRequestHandler):

    def do_OPTIONS(self):
        self.send_response(200)
        for k, v in cors_headers().items():
            self.send_header(k, v)
        self.end_headers()

    def do_GET(self):
        try:
            data    = build_summary()
            body    = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
            status  = 200
        except Exception as exc:
            body   = json.dumps({"error": str(exc)}).encode("utf-8")
            status = 500

        self.send_response(status)
        for k, v in cors_headers().items():
            self.send_header(k, v)
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)
