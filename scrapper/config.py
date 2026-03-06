"""
config.py — Central configuration for the ECN Result Scraper
All URLs, party mappings, province data, and constants live here.
"""

from __future__ import annotations

ECN_BASE_URL = "https://result.election.gov.np"

# ── Known endpoint patterns discovered via network inspection ──
ENDPOINTS = {
    "home":              f"{ECN_BASE_URL}/",
    "fptp_result":       f"{ECN_BASE_URL}/NationalResult.aspx",
    "pr_result":         f"{ECN_BASE_URL}/PRResult.aspx",
    "candidate_detail":  f"{ECN_BASE_URL}/CandidateDetail.aspx",
    "party_summary":     f"{ECN_BASE_URL}/",               # main page table
    "constituency_list": f"{ECN_BASE_URL}/NationalResult.aspx",
}

# ── 165 FPTP Constituency IDs  (1–165) ──
ALL_CONSTITUENCY_IDS = list(range(1, 166))

# ── Province mapping (province_no → name) ──
PROVINCES: dict[int, dict] = {
    1: {"name": "Koshi",          "name_np": "कोशी प्रदेश",          "short": "P1", "districts": 14},
    2: {"name": "Madhesh",        "name_np": "मधेश प्रदेश",          "short": "P2", "districts": 8},
    3: {"name": "Bagmati",        "name_np": "बागमती प्रदेश",         "short": "P3", "districts": 13},
    4: {"name": "Gandaki",        "name_np": "गण्डकी प्रदेश",        "short": "P4", "districts": 11},
    5: {"name": "Lumbini",        "name_np": "लुम्बिनी प्रदेश",       "short": "P5", "districts": 12},
    6: {"name": "Karnali",        "name_np": "कर्णाली प्रदेश",        "short": "P6", "districts": 10},
    7: {"name": "Sudurpashchim",  "name_np": "सुदूरपश्चिम प्रदेश",   "short": "P7", "districts": 9},
}

# ── Constituency → Province mapping (1-based IDs) ──
# Koshi:1-25, Madhesh:26-45, Bagmati:46-77, Gandaki:78-100,
# Lumbini:101-128, Karnali:129-144, Sudurpashchim:145-165
CONSTITUENCY_PROVINCE: dict[int, int] = {
    **{i: 1 for i in range(1,  26)},
    **{i: 2 for i in range(26, 46)},
    **{i: 3 for i in range(46, 78)},
    **{i: 4 for i in range(78, 101)},
    **{i: 5 for i in range(101, 129)},
    **{i: 6 for i in range(129, 145)},
    **{i: 7 for i in range(145, 166)},
}

# ── Party registry (Nepali name → normalized metadata) ──
PARTY_REGISTRY: dict[str, dict] = {
    # Major parties — Nepali names
    "नेपाली काँग्रेस":                         {"id": "NC",      "short": "NC",      "color": "#2B6FD4", "en": "Nepali Congress"},
    "नेकपा (एमाले)":                           {"id": "CPN-UML", "short": "CPN-UML", "color": "#D94040", "en": "CPN (UML)"},
    "नेकपा (माओवादी केन्द्र)":                 {"id": "CPN-MC",  "short": "Maoist",  "color": "#9B59D0", "en": "CPN (Maoist Centre)"},
    "राष्ट्रिय स्वतन्त्र पार्टी":              {"id": "RSP",     "short": "RSP",     "color": "#3DB87A", "en": "Rastriya Swatantra Party"},
    "राष्ट्रिय प्रजातन्त्र पार्टी":            {"id": "RPP",     "short": "RPP",     "color": "#E8A020", "en": "Rastriya Prajatantra Party"},
    "जनमत पार्टी":                             {"id": "JANMAT",  "short": "Janmat",  "color": "#E85A20", "en": "Janmat Party"},
    "लोकतान्त्रिक समाजवादी पार्टी नेपाल":     {"id": "LSP",     "short": "LSP",     "color": "#F59E0B", "en": "Loktantrik Samajwadi Party"},
    "नागरिक उन्मुक्ति पार्टी":                 {"id": "NUP",     "short": "NUP",     "color": "#06B6D4", "en": "Nagarik Unmukti Party"},
    "नेकपा (एकीकृत समाजवादी)":                {"id": "CPN-US",  "short": "CPN-US",  "color": "#7C3AED", "en": "CPN (Unified Socialist)"},
    "राप्रपा नेपाल":                            {"id": "RPPN",    "short": "RPPN",    "color": "#B45309", "en": "RPP Nepal"},
    "स्वतन्त्र":                               {"id": "IND",     "short": "IND",     "color": "#6B7280", "en": "Independent"},
    # English names (fallback)
    "Nepali Congress":                          {"id": "NC",      "short": "NC",      "color": "#2B6FD4", "en": "Nepali Congress"},
    "CPN (UML)":                                {"id": "CPN-UML", "short": "CPN-UML", "color": "#D94040", "en": "CPN (UML)"},
    "CPN (Maoist Centre)":                      {"id": "CPN-MC",  "short": "Maoist",  "color": "#9B59D0", "en": "CPN (Maoist Centre)"},
    "Rastriya Swatantra Party":                 {"id": "RSP",     "short": "RSP",     "color": "#3DB87A", "en": "Rastriya Swatantra Party"},
    "Rastriya Prajatantra Party":               {"id": "RPP",     "short": "RPP",     "color": "#E8A020", "en": "Rastriya Prajatantra Party"},
    "Independent":                              {"id": "IND",     "short": "IND",     "color": "#6B7280", "en": "Independent"},
}

# ── HTTP request settings ──
REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept":          "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ne,en-US;q=0.9,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection":      "keep-alive",
    "Referer":         ECN_BASE_URL,
}

TIMEOUT_SECONDS = 20
MAX_RETRIES     = 4
RETRY_BACKOFF   = 2.0   # seconds between retries (exponential)
RATE_LIMIT_DELAY = 0.8  # seconds between requests (be polite)
CONCURRENCY      = 5    # max simultaneous async requests

OUTPUT_DIR  = "output"
JSON_DIR    = "output/json"
CSV_DIR     = "output/csv"
IMAGES_DIR  = "output/images"
LOG_DIR     = "logs"
