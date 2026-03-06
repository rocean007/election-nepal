"""
GET /api/health
---------------
Health check — confirms the API is alive and ECN is reachable.

Response:
{
  "status":      "ok",
  "ecn_reachable": true,
  "updated_at":  "2026-03-06T08:45:00Z",
  "endpoints": [ ... ]
}
"""

from http.server import BaseHTTPRequestHandler
import json, sys, os
sys.path.insert(0, os.path.dirname(__file__))

from _core import cors_headers, timestamp, ECN_BASE, session

ENDPOINT_DOCS = [
    {"path": "/api/live-summary",        "desc": "Full party standings + progress snapshot"},
    {"path": "/api/party-seats",         "desc": "FPTP + PR seat breakdown per party"},
    {"path": "/api/constituency/[id]",   "desc": "Single constituency full result (id: 1–165)"},
    {"path": "/api/province/[name]",     "desc": "All constituencies for a province"},
    {"path": "/api/pr",                  "desc": "Proportional representation results"},
    {"path": "/api/search?q=name",       "desc": "Search candidates by name"},
    {"path": "/api/health",              "desc": "This endpoint — health check"},
]


class handler(BaseHTTPRequestHandler):

    def do_OPTIONS(self):
        self.send_response(200)
        for k, v in cors_headers().items():
            self.send_header(k, v)
        self.end_headers()

    def do_GET(self):
        # Ping ECN
        ecn_ok = False
        try:
            r      = session().get(ECN_BASE, timeout=5)
            ecn_ok = r.status_code == 200
        except Exception:
            pass

        data = {
            "status":        "ok",
            "ecn_reachable": ecn_ok,
            "updated_at":    timestamp(),
            "source":        ECN_BASE,
            "cors":          "public (*)",
            "cache":         "60s edge cache (Vercel CDN)",
            "endpoints":     ENDPOINT_DOCS,
        }
        body = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")

        self.send_response(200)
        for k, v in cors_headers().items():
            self.send_header(k, v)
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)
