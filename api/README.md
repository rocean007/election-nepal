# 🇳🇵 Nepal Election 2082 — Public API (Vercel)

Real-time JSON API that scrapes **result.election.gov.np** and serves clean data to any website.  
Deployed on Vercel. **Public CORS** — any frontend can fetch it.

---

## 🚀 Deploy in 3 steps

```bash
# 1. Install Vercel CLI
npm i -g vercel

# 2. Clone / enter this folder
cd ecn_vercel

# 3. Deploy
vercel deploy --prod
```

Your API is live at `https://your-project.vercel.app`

---

## 📡 Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/live-summary` | Full snapshot — party standings, progress, provinces |
| GET | `/api/party-seats` | FPTP + PR seat breakdown per party |
| GET | `/api/constituency/45` | Full result for constituency #45 (1–165) |
| GET | `/api/province/Bagmati` | All constituencies in a province |
| GET | `/api/pr` | Proportional representation results |
| GET | `/api/search?q=Gagan` | Search candidates by name |
| GET | `/api/health` | Health check + endpoint list |

### Province names
`Koshi` · `Madhesh` · `Bagmati` · `Gandaki` · `Lumbini` · `Karnali` · `Sudurpashchim`

---

## 💻 Use from any website

### Vanilla JavaScript
```js
// Get party standings
const res  = await fetch("https://your-project.vercel.app/api/party-seats");
const data = await res.json();

data.parties.forEach(p => {
  console.log(`${p.party_short}: ${p.total_seats} seats`);
});
```

### React
```jsx
import { useEffect, useState } from "react";

const API = "https://your-project.vercel.app";

export default function PartySeats() {
  const [parties, setParties] = useState([]);

  useEffect(() => {
    fetch(`${API}/api/party-seats`)
      .then(r => r.json())
      .then(d => setParties(d.parties));
  }, []);

  return (
    <ul>
      {parties.map(p => (
        <li key={p.party_id} style={{ color: p.party_color }}>
          {p.party_short} — {p.total_seats} seats
        </li>
      ))}
    </ul>
  );
}
```

### Python (requests)
```python
import requests

r    = requests.get("https://your-project.vercel.app/api/live-summary")
data = r.json()

print("Leading party:", data["leading_party"]["party_short"])
print("Declared:", data["progress"]["constituencies_declared"], "/ 165")

for p in data["party_standings"][:5]:
    print(f"  {p['party_short']:10s} {p['total_seats']:3d} seats")
```

### cURL
```bash
curl https://your-project.vercel.app/api/live-summary | jq .
curl https://your-project.vercel.app/api/constituency/45
curl "https://your-project.vercel.app/api/search?q=Gagan&province=Bagmati"
```

---

## 📦 Example responses

### `/api/live-summary`
```json
{
  "meta": {
    "updated_at":  "2026-03-06T08:45:00Z",
    "source":      "result.election.gov.np",
    "election_en": "Nepal House of Representatives Election 2082",
    "election_np": "प्रतिनिधि सभा निर्वाचन, २०८२",
    "date":        "2026-03-05"
  },
  "seats": {
    "total": 275, "fptp_total": 165,
    "pr_total": 110, "majority_mark": 138
  },
  "leading_party": {
    "party_id": "CPN-UML", "party_short": "CPN-UML",
    "total_fptp": 59, "pr_seats": 28, "total_seats": 87
  },
  "party_standings": [ ... ],
  "provinces": [ ... ]
}
```

### `/api/constituency/45`
```json
{
  "updated_at":     "2026-03-06T08:45:00Z",
  "id":             45,
  "name_np":        "काठमाडौँ-४",
  "province_name":  "Bagmati",
  "status":         "counting",
  "total_votes":    94274,
  "total_candidates": 11,
  "winner": {
    "name":        "रवि लामिछाने",
    "party_short": "RSP",
    "votes":       42100,
    "margin":      2246
  },
  "candidates": [
    {
      "rank": 1, "name_np": "रवि लामिछाने",
      "party_id": "RSP", "party_short": "RSP",
      "party_color": "#3DB87A",
      "votes": 42100, "vote_pct": 44.66,
      "photo_url": "https://result.election.gov.np/..."
    }
  ]
}
```

---

## ⚙️ How caching works

Vercel's CDN caches each response for **60 seconds** (`s-maxage=60`).  
- First call in 60s → hits the scraper → fetches live from ECN  
- Subsequent calls → served from Vercel edge (instant, no ECN hit)  
- After 60s → next request re-scrapes  

This means the data is at most 60 seconds stale, while the ECN server is never hit more than once per minute per endpoint.

---

## 📁 Project structure

```
ecn_vercel/
├── vercel.json            ← Vercel config + CORS headers
├── requirements.txt       ← requests, beautifulsoup4, lxml
└── api/
    ├── _core.py           ← Shared scraping engine (all endpoints import this)
    ├── live-summary.py    ← GET /api/live-summary
    ├── party-seats.py     ← GET /api/party-seats
    ├── pr.py              ← GET /api/pr
    ├── health.py          ← GET /api/health
    ├── search.py          ← GET /api/search?q=
    ├── constituency/
    │   └── [id].py        ← GET /api/constituency/45
    └── province/
        └── [name].py      ← GET /api/province/Bagmati
```

---

## ⚠️ Notes

- Vercel **Hobby** plan: 10s function timeout. `live-summary` and `party-seats` are fine. `/province/[name]` scrapes ~25 pages in parallel — may be tight. Upgrade to **Pro** (60s timeout) if needed.
- ECN's server is under heavy load during counting. Retries are built in.
- All Devanagari (Nepali) text is preserved as UTF-8. Party names, candidate names, constituency names all come through in the original script.
