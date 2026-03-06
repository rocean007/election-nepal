# 🇳🇵 Nepal Election 2082 — Python Scraper

Real-time scraper for **result.election.gov.np** — the official Election Commission of Nepal results portal.

---

## 📁 Structure

```
ecn_scraper/
├── main.py              ← CLI entry point — run this
├── config.py            ← All URLs, party map, province data
├── scraper.py           ← Core HTTP scraper (requests + BeautifulSoup)
├── async_scraper.py     ← Async aiohttp scraper for all 165 seats concurrently
├── exporter.py          ← JSON + CSV export
├── image_downloader.py  ← Async candidate photo/symbol downloader
├── utils.py             ← Logging, retry, Devanagari helpers
├── requirements.txt     ← pip dependencies
└── output/
    ├── json/
    │   ├── live_summary.json        ← Root API payload
    │   ├── constituencies.json      ← All 165 results
    │   ├── party_seats.json         ← Party FPTP + PR breakdown
    │   ├── pr_results.json          ← Proportional representation
    │   └── constituencies/          ← Per-constituency detail files
    │       ├── constituency_001.json
    │       └── ...
    ├── csv/
    │   ├── candidates.csv           ← All candidates flat (one row/candidate)
    │   ├── party_summary.csv        ← Party-level summary
    │   └── constituency_summary.csv ← Constituency winners
    └── images/
        ├── candidates/              ← Candidate photos
        └── symbols/                 ← Party election symbols
```

---

## ⚡ Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. (Optional) Install Playwright for JS-rendered pages
playwright install chromium

# 3. Run the scraper
python main.py                          # scrape everything
python main.py --mode parties           # only party seats
python main.py --mode live              # just the live-summary JSON
python main.py --const 45 46 47        # specific constituencies
python main.py --mode constituency --id 45   # single constituency detail
python main.py --watch 60              # re-run every 60s (live mode)
python main.py --images                # also download photos
python main.py --format json           # JSON only (skip CSV)
python main.py --individual-json       # write per-constituency JSON files
```

---

## 🔁 Scraping Strategy

The scraper uses a **two-layer approach**:

| Layer | When used | Speed |
|-------|-----------|-------|
| `requests` + `BeautifulSoup` | Most pages (ECN serves server-side HTML) | Fast — ~0.8s/page |
| `Playwright` (headless Chromium) | Pages that require JS rendering | ~3–5s/page |

The 165 constituencies are scraped **concurrently** using `aiohttp` + `asyncio` (default concurrency: 5, rate-limited to ~0.8s between requests).

---

## 📦 Output Files

### `live_summary.json`
The root payload — everything in one file. Ideal for powering dashboards.

```json
{
  "meta": {
    "updated_at": "2026-03-06T08:45:00Z",
    "source": "result.election.gov.np",
    "election_en": "Nepal House of Representatives Election 2082"
  },
  "seats": { "total": 275, "fptp_total": 165, "pr_total": 110, "majority_mark": 138 },
  "progress": {
    "constituencies_declared": 12,
    "constituencies_counting": 153,
    "declared_pct": 7.3
  },
  "leading_party": { "party_id": "CPN-UML", "total_seats": 77 },
  "party_standings": [...],
  "provinces": [...]
}
```

### `candidates.csv`
Flat table — one row per candidate. Load directly into pandas or Excel.

| const_id | const_name | province_name | status | rank | candidate_name_np | party_short | votes | vote_pct | is_winner |
|----------|------------|---------------|--------|------|-------------------|-------------|-------|----------|-----------|

---

## 🛠️ Configuration (`config.py`)

| Setting | Default | Description |
|---------|---------|-------------|
| `RATE_LIMIT_DELAY` | `0.8s` | Delay between requests |
| `CONCURRENCY` | `5` | Async concurrency limit |
| `MAX_RETRIES` | `4` | Retry attempts per request |
| `TIMEOUT_SECONDS` | `20` | Request timeout |

Increase `CONCURRENCY` with caution — the ECN server is under heavy load during election night.

---

## 🔬 How to analyse the data

```python
import pandas as pd, json

# Party standings
with open("output/json/party_seats.json") as f:
    data = json.load(f)
df_parties = pd.DataFrame(data["parties"])
print(df_parties[["party_short", "fptp_won", "fptp_leading", "pr_seats", "total_seats"]])

# All candidates
df = pd.read_csv("output/csv/candidates.csv")
print(df[df["is_winner"] == True][["const_name", "candidate_name_np", "party_short", "votes"]])

# Province breakdown
print(df.groupby("province_name")["votes"].sum().sort_values(ascending=False))

# Close races (margin < 1000)
summary = pd.read_csv("output/csv/constituency_summary.csv")
close = summary[summary["winner_margin"] < 1000].sort_values("winner_margin")
print(close[["name_np", "winner_name", "winner_party", "winner_margin"]])
```

---

## 📝 Notes

- ECN's portal is heavily loaded during counting — the scraper retries automatically
- Some pages may be JS-rendered; Playwright handles these transparently as fallback
- Devanagari numbers (०-९) are normalised to ASCII automatically
- All Nepali text is stored as UTF-8; CSVs use UTF-8-BOM for Excel compatibility

---

*Educational/journalistic use only. Respect the Election Commission's server by not setting concurrency above 10.*
