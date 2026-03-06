"""
exporter.py — Export scraped data to JSON, CSV, and summary reports.

Supports:
  - Structured JSON (machine-readable, API-ready)
  - Flat CSV (for pandas / Excel analysis)
  - Summary report (human-readable text)
"""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from config import JSON_DIR, CSV_DIR, PROVINCES
from utils import get_logger, ensure_dirs, sanitize_filename

log = get_logger("exporter")


# ─────────────────────────────────────────────────────────────────
# JSON EXPORT
# ─────────────────────────────────────────────────────────────────

def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def export_json(data: Any, filename: str, subdir: str = JSON_DIR) -> Path:
    """Write data to a pretty-printed JSON file. Returns path."""
    ensure_dirs(subdir)
    path = Path(subdir) / filename
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    log.info(f"[green]JSON saved:[/] {path}  ({path.stat().st_size // 1024} KB)")
    return path


def export_live_summary(
    party_seats:      list[dict],
    constituencies:   list[dict],
    pr_results:       list[dict],
) -> Path:
    """
    Build and export the canonical live-summary JSON.
    This is the root payload for the public API.
    """
    declared = [c for c in constituencies if c.get("status") == "declared"]
    counting = [c for c in constituencies if c.get("status") == "counting"]
    pending  = [c for c in constituencies if c.get("status") == "pending"]

    # Merge FPTP + PR into combined seat totals
    pr_by_party = {r["party_id"]: r["seats"] for r in pr_results}
    combined: list[dict] = []
    for p in party_seats:
        pid  = p["party_id"]
        pr_s = pr_by_party.get(pid, 0)
        combined.append({
            **p,
            "pr_seats": pr_s,
            "total_seats": p["total_fptp"] + pr_s,
        })
    combined.sort(key=lambda x: x["total_seats"], reverse=True)

    summary = {
        "meta": {
            "updated_at":   _timestamp(),
            "source":       "result.election.gov.np",
            "election":     "प्रतिनिधि सभा निर्वाचन २०८२",
            "election_en":  "Nepal House of Representatives Election 2082",
            "date":         "2026-03-05",
        },
        "seats": {
            "total":          275,
            "fptp_total":     165,
            "pr_total":       110,
            "majority_mark":  138,
        },
        "progress": {
            "constituencies_total":    165,
            "constituencies_declared": len(declared),
            "constituencies_counting": len(counting),
            "constituencies_pending":  len(pending),
            "declared_pct":            round(len(declared) / 165 * 100, 1),
        },
        "leading_party": combined[0] if combined else None,
        "party_standings": combined,
        "provinces": [
            {
                "province_no":    pno,
                "name":           pinfo["name"],
                "name_np":        pinfo["name_np"],
                "constituencies": [
                    c for c in constituencies
                    if c.get("province_no") == pno
                ],
            }
            for pno, pinfo in PROVINCES.items()
        ],
    }

    return export_json(summary, "live_summary.json")


def export_all_constituencies_json(constituencies: list[dict]) -> Path:
    payload = {
        "updated_at":    _timestamp(),
        "total":         len(constituencies),
        "constituencies": constituencies,
    }
    return export_json(payload, "constituencies.json")


def export_party_seats_json(party_seats: list[dict], pr_results: list[dict]) -> Path:
    pr_by_party = {r["party_id"]: r for r in pr_results}
    enriched = []
    for p in party_seats:
        pid  = p["party_id"]
        pr   = pr_by_party.get(pid, {})
        enriched.append({
            **p,
            "pr_votes":    pr.get("votes", 0),
            "pr_vote_pct": pr.get("vote_pct", 0.0),
            "pr_seats":    pr.get("seats", 0),
            "total_seats": p["total_fptp"] + pr.get("seats", 0),
        })
    enriched.sort(key=lambda x: x["total_seats"], reverse=True)
    payload = {"updated_at": _timestamp(), "parties": enriched}
    return export_json(payload, "party_seats.json")


def export_constituency_detail_json(constituency: dict) -> Path:
    """Export single constituency to its own file."""
    cid      = constituency.get("id", "unknown")
    filename = f"constituency_{cid:03d}.json"
    payload  = {"updated_at": _timestamp(), **constituency}
    path     = Path(JSON_DIR) / "constituencies"
    ensure_dirs(str(path))
    p = path / filename
    with open(p, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return p


# ─────────────────────────────────────────────────────────────────
# CSV EXPORT
# ─────────────────────────────────────────────────────────────────

def export_candidates_csv(constituencies: list[dict]) -> Path:
    """
    Flat CSV with one row per candidate across all constituencies.
    Columns: const_id, const_name, province, district, status,
             rank, candidate_name, party_id, party_short, votes,
             vote_pct, is_winner
    """
    ensure_dirs(CSV_DIR)
    path = Path(CSV_DIR) / "candidates.csv"

    fieldnames = [
        "const_id", "const_name", "province_name", "province_no",
        "status", "total_votes",
        "rank", "candidate_name_np", "party_id", "party_short",
        "party_name_np", "votes", "vote_pct", "is_winner",
        "winner_margin", "photo_url",
    ]

    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()

        for const in constituencies:
            cid    = const.get("id")
            winner = const.get("winner")
            for cand in const.get("candidates", []):
                writer.writerow({
                    "const_id":        cid,
                    "const_name":      const.get("name_np", ""),
                    "province_name":   const.get("province_name", ""),
                    "province_no":     const.get("province_no", ""),
                    "status":          const.get("status", ""),
                    "total_votes":     const.get("total_votes", 0),
                    "rank":            cand.get("rank", ""),
                    "candidate_name_np": cand.get("name_np", ""),
                    "party_id":        cand.get("party_id", ""),
                    "party_short":     cand.get("party_short", ""),
                    "party_name_np":   cand.get("party_name_np", ""),
                    "votes":           cand.get("votes", 0),
                    "vote_pct":        cand.get("vote_pct", 0.0),
                    "is_winner":       cand.get("rank") == 1 and const.get("status") == "declared",
                    "winner_margin":   winner.get("margin", "") if winner and cand.get("rank") == 1 else "",
                    "photo_url":       cand.get("photo_url", ""),
                })

    log.info(f"[green]CSV saved:[/] {path}")
    return path


def export_party_summary_csv(party_seats: list[dict], pr_results: list[dict]) -> Path:
    """CSV of party-level summary."""
    ensure_dirs(CSV_DIR)
    path = Path(CSV_DIR) / "party_summary.csv"

    pr_by_party = {r["party_id"]: r for r in pr_results}
    rows = []
    for p in sorted(party_seats, key=lambda x: x.get("total_fptp", 0), reverse=True):
        pid = p["party_id"]
        pr  = pr_by_party.get(pid, {})
        rows.append({
            "party_id":      pid,
            "party_short":   p.get("party_short", ""),
            "party_name_en": p.get("party_name_en", ""),
            "party_name_np": p.get("party_name_np", ""),
            "fptp_won":      p.get("fptp_won", 0),
            "fptp_leading":  p.get("fptp_leading", 0),
            "fptp_total":    p.get("total_fptp", 0),
            "pr_votes":      pr.get("votes", 0),
            "pr_vote_pct":   pr.get("vote_pct", 0),
            "pr_seats":      pr.get("seats", 0),
            "total_seats":   p.get("total_fptp", 0) + pr.get("seats", 0),
        })

    df = pd.DataFrame(rows)
    df.to_csv(path, index=False, encoding="utf-8-sig")
    log.info(f"[green]CSV saved:[/] {path}")
    return path


def export_constituency_summary_csv(constituencies: list[dict]) -> Path:
    """One-row-per-constituency summary CSV."""
    ensure_dirs(CSV_DIR)
    path = Path(CSV_DIR) / "constituency_summary.csv"

    rows = []
    for c in sorted(constituencies, key=lambda x: x.get("id", 0)):
        winner = c.get("winner") or {}
        rows.append({
            "id":              c.get("id"),
            "name_np":         c.get("name_np", ""),
            "province_no":     c.get("province_no"),
            "province_name":   c.get("province_name", ""),
            "status":          c.get("status", ""),
            "total_votes":     c.get("total_votes", 0),
            "total_candidates":c.get("total_candidates", 0),
            "winner_name":     winner.get("name", ""),
            "winner_party":    winner.get("party_short", ""),
            "winner_votes":    winner.get("votes", 0),
            "winner_margin":   winner.get("margin", 0),
        })

    df = pd.DataFrame(rows)
    df.to_csv(path, index=False, encoding="utf-8-sig")
    log.info(f"[green]CSV saved:[/] {path}")
    return path


# ─────────────────────────────────────────────────────────────────
# TEXT SUMMARY REPORT
# ─────────────────────────────────────────────────────────────────

def print_summary(party_seats: list[dict], constituencies: list[dict]) -> None:
    """Print a Rich-formatted summary to terminal."""
    from rich.table import Table
    from rich.console import Console
    from rich import box

    con = Console()

    # ── Party table ──
    t = Table(title="🇳🇵  Party Seats — Nepal Election 2082", box=box.SIMPLE_HEAVY, border_style="dim")
    t.add_column("Rank", style="dim", justify="right")
    t.add_column("Party",       style="bold")
    t.add_column("FPTP Won",    justify="right")
    t.add_column("FPTP Leading",justify="right")
    t.add_column("FPTP Total",  justify="right", style="bold yellow")

    for i, p in enumerate(sorted(party_seats, key=lambda x: x.get("total_fptp", 0), reverse=True), 1):
        t.add_row(
            str(i),
            p.get("party_short", p.get("party_id", "")),
            str(p.get("fptp_won", 0)),
            str(p.get("fptp_leading", 0)),
            str(p.get("total_fptp", 0)),
        )

    con.print(t)

    # ── Progress ──
    dec = sum(1 for c in constituencies if c.get("status") == "declared")
    cnt = sum(1 for c in constituencies if c.get("status") == "counting")
    con.print(f"\n[bold]Constituencies:[/] {dec} declared, {cnt} counting, {165 - dec - cnt} pending / 165 total")
    con.print(f"[bold]Majority mark:[/] 138 / 275 seats\n")
