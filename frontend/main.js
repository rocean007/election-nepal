/* ============================================================
   NEPAL ELECTION 2082 — LIVE RESULTS DASHBOARD
   Main JavaScript Logic
   ============================================================ */

'use strict';

/* ── PARTY DEFINITIONS ──────────────────────────────────────── */
const PARTIES = {
  'CPN-UML': { name: 'CPN (UML)',              full: 'Communist Party of Nepal (UML)',   color: '#C0392B', abbr: 'UML'    },
  'NC':      { name: 'Nepali Congress',         full: 'Nepali Congress',                 color: '#2563C4', abbr: 'NC'     },
  'RSP':     { name: 'Rastriya Swatantra',      full: 'Rastriya Swatantra Party',        color: '#1A7D52', abbr: 'RSP'    },
  'CPN-MC':  { name: 'CPN Maoist Centre',       full: 'CPN (Maoist Centre)',             color: '#7B3FA0', abbr: 'Maoist' },
  'RPP':     { name: 'Rastriya Prajatantra',    full: 'Rastriya Prajatantra Party',      color: '#C07820', abbr: 'RPP'    },
  'LSP':     { name: 'Loktantrik Samajwadi',    full: 'Loktantrik Samajwadi Party',      color: '#E85A20', abbr: 'LSP'    },
  'IND':     { name: 'Independent',             full: 'Independent',                     color: '#4A5568', abbr: 'IND'    },
};

/* ── DEMO DATA ──────────────────────────────────────────────── */
function getDemoData() {
  return {
    declared: 2,
    counting: 10,
    seats: [
      { id: 'CPN-UML', fptp: 47, pr: 30, total: 77 },
      { id: 'NC',      fptp: 38, pr: 26, total: 64 },
      { id: 'RSP',     fptp: 28, pr: 14, total: 42 },
      { id: 'CPN-MC',  fptp: 12, pr: 11, total: 23 },
      { id: 'RPP',     fptp:  9, pr:  7, total: 16 },
      { id: 'LSP',     fptp:  5, pr:  6, total: 11 },
      { id: 'IND',     fptp:  8, pr:  0, total:  8 },
    ],
    zones: [
      {
        id: 'KTM4', name: 'Kathmandu-4', district: 'Kathmandu', province: 'Bagmati',
        status: 'counting', reported: 78,
        candidates: [
          { name: 'Rabi Lamichhane',  party: 'RSP',    votes: 42100, img: null },
          { name: 'Gagan Thapa',      party: 'NC',     votes: 39854, img: null },
          { name: 'Bhim Rawal',       party: 'CPN-UML',votes: 12320, img: null },
        ]
      },
      {
        id: 'JHP5', name: 'Jhapa-5', district: 'Jhapa', province: 'Koshi',
        status: 'counting', reported: 65,
        candidates: [
          { name: 'Balendra Shah',  party: 'RSP',    votes: 34215, img: null },
          { name: 'KP Sharma Oli', party: 'CPN-UML',votes: 31087, img: null },
          { name: 'Ram Kumar Rai', party: 'NC',     votes:  8432, img: null },
        ]
      },
      {
        id: 'CTW3', name: 'Chitwan-3', district: 'Chitwan', province: 'Bagmati',
        status: 'counting', reported: 55,
        candidates: [
          { name: 'Renu Dahal',      party: 'CPN-MC', votes: 27800, img: null },
          { name: 'Shekhar Koirala', party: 'NC',     votes: 26900, img: null },
          { name: 'Tek B. Gurung',   party: 'CPN-UML',votes: 14200, img: null },
        ]
      },
      {
        id: 'KVR2', name: 'Kavre-2', district: 'Kavre', province: 'Bagmati',
        status: 'declared', reported: 100,
        candidates: [
          { name: 'Ramesh Lekhak',   party: 'NC',     votes: 31500, img: null },
          { name: 'Pradeep Gyawali', party: 'CPN-UML',votes: 29400, img: null },
          { name: 'Bidur Karki',     party: 'RSP',    votes: 11800, img: null },
        ]
      },
      {
        id: 'SNS2', name: 'Sunsari-2', district: 'Sunsari', province: 'Koshi',
        status: 'counting', reported: 48,
        candidates: [
          { name: 'Shankar Pokhrel', party: 'CPN-UML',votes: 19200, img: null },
          { name: 'Shekhar Koirala', party: 'NC',     votes: 18100, img: null },
          { name: 'Dipak Kharal',    party: 'RSP',    votes:  9800, img: null },
        ]
      },
      {
        id: 'RPN4', name: 'Rupandehi-4', district: 'Rupandehi', province: 'Lumbini',
        status: 'counting', reported: 62,
        candidates: [
          { name: 'Khagaraj Adhikari', party: 'RPP',    votes: 22400, img: null },
          { name: 'Surendra Pandey',   party: 'CPN-UML',votes: 21900, img: null },
          { name: 'Prakash M. Singh',  party: 'NC',     votes: 18500, img: null },
        ]
      },
      {
        id: 'KSK1', name: 'Pokhara-1', district: 'Kaski', province: 'Gandaki',
        status: 'counting', reported: 82,
        candidates: [
          { name: 'Krishna Sitaula', party: 'NC',     votes: 38200, img: null },
          { name: 'Ram B. Thapa',    party: 'CPN-MC', votes: 26500, img: null },
          { name: 'Khadga B. Bisht', party: 'CPN-UML',votes: 19100, img: null },
        ]
      },
      {
        id: 'BHK1', name: 'Bhaktapur-1', district: 'Bhaktapur', province: 'Bagmati',
        status: 'declared', reported: 100,
        candidates: [
          { name: 'Sunil Prajapati',     party: 'RSP',    votes: 29800, img: null },
          { name: 'Narayan K. Shrestha', party: 'CPN-MC', votes: 27300, img: null },
          { name: 'Bidhan Giri',         party: 'CPN-UML',votes: 15700, img: null },
        ]
      },
      {
        id: 'SRL3', name: 'Sarlahi-3', district: 'Sarlahi', province: 'Madhesh',
        status: 'counting', reported: 39,
        candidates: [
          { name: 'Rajendra Mahato', party: 'LSP',    votes: 16800, img: null },
          { name: 'Anil Jha',        party: 'NC',     votes: 15900, img: null },
          { name: 'Umesh Yadav',     party: 'CPN-UML',votes: 11200, img: null },
        ]
      },
      {
        id: 'DHD2', name: 'Dhading-2', district: 'Dhading', province: 'Bagmati',
        status: 'counting', reported: 71,
        candidates: [
          { name: 'Ishwor Pokhrel',  party: 'CPN-UML',votes: 24700, img: null },
          { name: 'Dhan B. Shrestha',party: 'NC',     votes: 23100, img: null },
          { name: 'Sita Gurung',     party: 'RSP',    votes: 13400, img: null },
        ]
      },
      {
        id: 'RKM1', name: 'Rukum East-1', district: 'Rukum E.', province: 'Lumbini',
        status: 'counting', reported: 57,
        candidates: [
          { name: 'Agni Sapkota',      party: 'CPN-MC', votes: 18400, img: null },
          { name: 'Dilli B. Chaudhary',party: 'NC',     votes: 15200, img: null },
          { name: 'Bed P. Pandey',     party: 'CPN-UML',votes: 12900, img: null },
        ]
      },
      {
        id: 'RTH2', name: 'Rautahat-2', district: 'Rautahat', province: 'Madhesh',
        status: 'counting', reported: 44,
        candidates: [
          { name: 'Bijay K. Gachhadar', party: 'NC',     votes: 14500, img: null },
          { name: 'Saroj K. Yadav',     party: 'LSP',    votes: 13800, img: null },
          { name: 'Dev K. Prasad',      party: 'CPN-UML',votes: 10200, img: null },
        ]
      },
      {
        id: 'KRN1', name: 'Karnali-1', district: 'Surkhet', province: 'Karnali',
        status: 'counting', reported: 33,
        candidates: [
          { name: 'Mahendra Bahadur',  party: 'CPN-UML',votes: 11200, img: null },
          { name: 'Rekha Sharma',      party: 'NC',     votes:  9800, img: null },
          { name: 'Jeevan Pariyar',    party: 'CPN-MC', votes:  7400, img: null },
        ]
      },
      {
        id: 'SDR1', name: 'Kailali-1', district: 'Kailali', province: 'Sudurpashchim',
        status: 'counting', reported: 51,
        candidates: [
          { name: 'Chitra Bahadur KC', party: 'RSP',    votes: 17800, img: null },
          { name: 'Lal Bahadur Kunwar',party: 'RPP',    votes: 15200, img: null },
          { name: 'Tulsi Bhatta',      party: 'NC',     votes: 12900, img: null },
        ]
      },
    ]
  };
}

/* ── HELPERS ────────────────────────────────────────────────── */
function getParty(id) {
  return PARTIES[id] || { name: id, full: id, color: '#888', abbr: id };
}

function fmt(n) {
  return n.toLocaleString('en-IN');
}

function photoEl(img, name) {
  if (img) {
    return `<img src="images/${img}" alt="${name}" onerror="this.parentElement.textContent='👤'">`;
  }
  return '👤';
}

/* ── RENDER: SEATS BAR ──────────────────────────────────────── */
function renderSeatsBar(seats) {
  const bar = document.getElementById('seats-bar');
  bar.innerHTML = '<div class="majority-line"></div>';

  const total = 275;
  const sorted = [...seats].sort((a, b) => b.total - a.total);

  sorted.forEach(s => {
    if (!s.total) return;
    const p = getParty(s.id);
    const pct = (s.total / total) * 100;
    const seg = document.createElement('div');
    seg.className = 'bar-seg';
    seg.style.cssText = `width:${pct}%;background:${p.color}`;
    seg.title = `${p.abbr}: ${s.total} seats`;
    if (pct > 4.5) {
      seg.innerHTML = `<span class="bar-seg-lbl">${p.abbr}</span>`;
    }
    bar.appendChild(seg);
  });
}

/* ── RENDER: PARTY GRID ─────────────────────────────────────── */
function renderPartyGrid(seats) {
  const grid = document.getElementById('party-grid');
  grid.innerHTML = '';
  const sorted = [...seats].sort((a, b) => b.total - a.total);

  sorted.forEach(s => {
    const p = getParty(s.id);
    const chip = document.createElement('div');
    chip.className = 'party-chip';
    chip.style.setProperty('--pc', p.color);
    chip.innerHTML = `
      <div class="pc-abbr">${p.abbr}</div>
      <div class="pc-name">${p.name}</div>
      <div class="pc-seats">${s.total}</div>
      <div class="pc-label">Total Seats</div>
      <div class="pc-breakdown">
        <span>FPTP <strong>${s.fptp}</strong></span>
        <span>PR <strong>${s.pr}</strong></span>
      </div>
    `;
    grid.appendChild(chip);
  });
}

/* ── RENDER: LEAD TABLE ─────────────────────────────────────── */
function renderLeadTable(seats) {
  const table = document.getElementById('lead-table');
  table.innerHTML = '';
  const sorted = [...seats].sort((a, b) => b.total - a.total).slice(0, 7);

  sorted.forEach((s, i) => {
    const p = getParty(s.id);
    const row = document.createElement('div');
    row.className = 'lead-row';
    const rankClass = i === 0 ? 'rank-1' : i === 1 ? 'rank-2' : '';
    row.innerHTML = `
      <div class="lr-rank ${rankClass}">${i + 1}</div>
      <div class="lr-dot" style="background:${p.color}"></div>
      <div class="lr-name">${p.name}</div>
      <div class="lr-seats">${s.total}</div>
    `;
    table.appendChild(row);
  });

  // Majority meter — show leader's seats vs 138
  const leader = sorted[0];
  if (leader) {
    const p = getParty(leader.id);
    const pct = Math.min((leader.total / 138) * 100, 100);
    const meter = document.getElementById('majority-fill');
    if (meter) {
      meter.style.width = pct + '%';
      meter.style.background = `linear-gradient(90deg, ${p.color}88, ${p.color})`;
    }
    const note = document.getElementById('majority-note');
    if (note) {
      const gap = 138 - leader.total;
      if (gap > 0) {
        note.textContent = `${p.abbr} needs ${gap} more seats for majority`;
      } else {
        note.textContent = `${p.abbr} has secured majority`;
      }
    }
  }
}

/* ── RENDER: ZONE CARD (TOURNAMENT FORMAT) ──────────────────── */
function buildZoneCard(zone, delay) {
  const cands = zone.candidates.slice(0, 3);
  const totalVotes = cands.reduce((s, c) => s + c.votes, 0) || 1;

  const [c1, c2, c3] = cands;
  const p1 = c1 ? getParty(c1.party) : null;
  const p2 = c2 ? getParty(c2.party) : null;
  const p3 = c3 ? getParty(c3.party) : null;

  const pct = (v) => ((v / totalVotes) * 100).toFixed(1);

  const statusClass = zone.status === 'declared' ? 'badge-declared' : 'badge-counting';
  const statusText  = zone.status === 'declared' ? '✓ Declared' : '⚡ Counting';

  // Vote track segments
  const trackHtml = cands.map(c => {
    const p = getParty(c.party);
    const w = pct(c.votes);
    return `<div class="vote-track-seg" style="width:${w}%;background:${p.color}"></div>`;
  }).join('');

  // Challenger cards
  const buildChallenger = (c, rank) => {
    if (!c) return '';
    const p = getParty(c.party);
    const rankLabel = rank === 2 ? '2nd Place' : '3rd Place';
    return `
      <div class="challenger-card rank-${rank}">
        <div class="ch-rank">${rankLabel}</div>
        <div class="ch-photo-name">
          <div class="ch-photo">${photoEl(c.img, c.name)}</div>
          <div class="ch-name">${c.name}</div>
        </div>
        <div class="ch-party">
          <div class="t-party-dot" style="background:${p.color}"></div>
          <span style="color:${p.color}">${p.abbr}</span>
        </div>
        <div class="ch-votes">${fmt(c.votes)}</div>
        <div class="ch-pct">${pct(c.votes)}% of counted</div>
      </div>
    `;
  };

  const card = document.createElement('div');
  card.className = 'zone-card';
  card.dataset.province = zone.province;
  card.style.animationDelay = delay + 's';

  card.innerHTML = `
    <div class="zone-header">
      <div>
        <div class="zone-name">${zone.name}</div>
        <div class="zone-meta">${zone.district} · ${zone.province}</div>
      </div>
      <div class="zone-status-badge ${statusClass}">${statusText}</div>
    </div>

    <div class="tournament-wrap">
      ${c1 ? `
        <div class="tournament-winner">
          <div class="t-rank-badge">🥇 Leading</div>
          <div class="t-candidate-inner">
            <div class="t-photo">${photoEl(c1.img, c1.name)}</div>
            <div class="t-info">
              <div class="t-name">${c1.name}</div>
              <div class="t-party-tag">
                <div class="t-party-dot" style="background:${p1.color}"></div>
                <span style="color:${p1.color};font-weight:700">${p1.abbr}</span>
                <span style="color:var(--text-3)">${p1.name}</span>
              </div>
            </div>
            <div class="t-votes-wrap">
              <div class="t-votes-num">${fmt(c1.votes)}</div>
              <div class="t-votes-pct">${pct(c1.votes)}%</div>
            </div>
          </div>
        </div>
      ` : ''}

      ${(c2 || c3) ? `
        <div class="vs-divider">
          <div class="vs-line"></div>
          <div class="vs-label">Challengers</div>
          <div class="vs-line"></div>
        </div>
        <div class="challengers-row">
          ${buildChallenger(c2, 2)}
          ${buildChallenger(c3, 3)}
        </div>
      ` : ''}
    </div>

    <div class="vote-track">${trackHtml}</div>

    <div class="zone-footer">
      <div class="zf-reported">${zone.reported}% votes counted</div>
      <div class="zf-progress">
        <div class="zf-bar"><div class="zf-fill" style="width:${zone.reported}%"></div></div>
        <div class="zf-pct-lbl">${zone.reported}%</div>
      </div>
    </div>
  `;

  return card;
}

/* ── FILTER & RENDER ZONES ──────────────────────────────────── */
let ALL_ZONES = [];
let ACTIVE_FILTER = 'all';

function filterZones(province, btn) {
  document.querySelectorAll('.fpill').forEach(b => b.classList.remove('active'));
  if (btn) btn.classList.add('active');
  ACTIVE_FILTER = province;
  renderZones();
}

function renderZones() {
  const grid = document.getElementById('zones-grid');
  grid.innerHTML = '';

  const filtered = ACTIVE_FILTER === 'all'
    ? ALL_ZONES
    : ALL_ZONES.filter(z => z.province === ACTIVE_FILTER);

  if (filtered.length === 0) {
    grid.innerHTML = `<div class="loader"><div>No constituencies found for this province.</div></div>`;
    return;
  }

  filtered.forEach((z, i) => {
    grid.appendChild(buildZoneCard(z, i * 0.04));
  });
}

// Expose to HTML onclick
window.filterZones = filterZones;

/* ── CLOCK ──────────────────────────────────────────────────── */
function updateClock() {
  const el = document.getElementById('clock');
  if (!el) return;
  el.textContent = new Date().toLocaleTimeString('en-US', {
    hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false
  });
}

/* ── INIT ───────────────────────────────────────────────────── */
function init() {
  const data = getDemoData();

  // Counts
  const decEl = document.getElementById('s-dec');
  const cntEl = document.getElementById('s-cnt');
  if (decEl) decEl.textContent = data.declared;
  if (cntEl) cntEl.textContent = data.counting;

  // Render components
  renderSeatsBar(data.seats);
  renderPartyGrid(data.seats);
  renderLeadTable(data.seats);

  // Zones
  ALL_ZONES = data.zones;
  renderZones();
}

/* ── START ──────────────────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
  init();
  updateClock();
  setInterval(updateClock, 1000);
  setInterval(init, 60000);
});