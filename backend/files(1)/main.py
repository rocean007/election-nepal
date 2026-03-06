#!/usr/bin/env python3
"""
main.py — Nepal Election 2082 Scraper CLI
==========================================

Usage:
  python main.py                        # scrape everything
  python main.py --mode full            # scrape all (default)
  python main.py --mode parties         # only party seat summary
  python main.py --mode constituencies  # all 165 constituencies
  python main.py --mode pr              # proportional representation
  python main.py --mode constituency --id 45   # single constituency
  python main.py --mode live            # just the live-summary JSON
  python main.py --const 1 5 10 45     # specific constituency IDs
  python main.py --images               # also download photos
  python main.py --watch 60            # repeat every N seconds
  python main.py --format json         # output format (json|csv|both)
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    Progress, SpinnerColumn, BarColumn,
    TextColumn, TimeElapsedColumn, TaskProgressColumn,
)
from rich import box

from config import JSON_DIR, CSV_DIR, IMAGES_DIR, LOG_DIR, ALL_CONSTITUENCY_IDS
from utils import get_logger, ensure_dirs
from scraper import (
    scrape_party_seats,
    scrape_constituency_list,
    scrape_constituency,
    scrape_pr_results,
)
from async_scraper import run_async_scraper
from exporter import (
    export_live_summary,
    export_all_constituencies_json,
    export_party_seats_json,
    export_constituency_detail_json,
    export_candidates_csv,
    export_party_summary_csv,
    export_constituency_summary_csv,
    print_summary,
)
from image_downloader import download_candidate_images

log     = get_logger("main")
console = Console()


# ─────────────────────────────────────────────────────────────────
# BANNER
# ─────────────────────────────────────────────────────────────────

BANNER = """
[bold white]  ██████╗███╗  ██╗    ███████╗ ██████╗██████╗  █████╗ ██████╗ ███████╗██████╗[/]
[bold red]  ██╔══╝████╗ ██║    ██╔════╝██╔════╝██╔══██╗██╔══██╗██╔══██╗██╔════╝██╔══██╗[/]
[bold red]  █████╗██╔██╗██║    ███████╗██║     ██████╔╝███████║██████╔╝█████╗  ██████╔╝[/]
[bold white]  ██╔══╝██║╚████║    ╚════██║██║     ██╔══██╗██╔══██║██╔═══╝ ██╔══╝  ██╔══██╗[/]
[bold red]  ██████╗██║ ╚███║    ███████║╚██████╗██║  ██║██║  ██║██║     ███████╗██║  ██║[/]
[bold white]  ╚═════╝╚═╝  ╚═╝    ╚══════╝ ╚═════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝     ╚══════╝╚═╝  ╚═╝[/]

  [dim]🇳🇵  प्रतिनिधि सभा निर्वाचन २०८२  |  House of Representatives Election 2082[/]
  [dim]     Source: result.election.gov.np  |  Election Commission of Nepal[/]
"""


# ─────────────────────────────────────────────────────────────────
# SCRAPE MODES
# ─────────────────────────────────────────────────────────────────

def run_full(args: argparse.Namespace) -> None:
    """Scrape everything: parties, all 165 constituencies, PR results."""
    console.print("[bold cyan]Mode: FULL — Scraping all data[/]")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        console=console,
    ) as progress:

        # ── 1. Party seats ──
        t1 = progress.add_task("[cyan]Party seats…", total=1)
        party_seats = scrape_party_seats()
        progress.update(t1, completed=1)

        # ── 2. PR results ──
        t2 = progress.add_task("[cyan]PR results…", total=1)
        pr_results = scrape_pr_results()
        progress.update(t2, completed=1)

        # ── 3. All constituencies (async) ──
        const_ids = args.const if args.const else ALL_CONSTITUENCY_IDS
        t3 = progress.add_task(f"[cyan]Constituencies (async)…", total=len(const_ids))

        constituencies = run_async_scraper(const_ids, concurrency=args.concurrency)
        progress.update(t3, completed=len(const_ids))

    # ── Export ──
    _export(party_seats, constituencies, pr_results, args)

    # ── Images ──
    if args.images:
        download_candidate_images(constituencies, concurrency=args.concurrency)

    print_summary(party_seats, constituencies)


def run_parties(args: argparse.Namespace) -> None:
    console.print("[bold cyan]Mode: PARTIES[/]")
    party_seats = scrape_party_seats()
    pr_results  = scrape_pr_results()
    export_party_seats_json(party_seats, pr_results)
    if args.format in ("csv", "both"):
        export_party_summary_csv(party_seats, pr_results)
    print_summary(party_seats, [])


def run_constituencies(args: argparse.Namespace) -> None:
    console.print("[bold cyan]Mode: CONSTITUENCIES[/]")
    const_ids = args.const if args.const else ALL_CONSTITUENCY_IDS
    constituencies = run_async_scraper(const_ids, concurrency=args.concurrency)
    party_seats    = scrape_party_seats()
    pr_results     = scrape_pr_results()
    _export(party_seats, constituencies, pr_results, args)
    if args.images:
        download_candidate_images(constituencies)


def run_single(args: argparse.Namespace) -> None:
    cid = args.id
    if not cid:
        console.print("[red]--id required for single constituency mode[/]")
        sys.exit(1)
    console.print(f"[bold cyan]Mode: SINGLE CONSTITUENCY — ID {cid}[/]")
    result = scrape_constituency(cid)
    path   = export_constituency_detail_json(result)
    console.print_json(path.read_text(encoding="utf-8"))


def run_pr(args: argparse.Namespace) -> None:
    console.print("[bold cyan]Mode: PR RESULTS[/]")
    pr = scrape_pr_results()
    from exporter import export_json
    export_json(pr, "pr_results.json")
    console.print_json(str(pr)[:3000])


def run_live(args: argparse.Namespace) -> None:
    """Quick live-summary only — party seats + PR, no per-constituency detail."""
    console.print("[bold cyan]Mode: LIVE SUMMARY[/]")
    party_seats = scrape_party_seats()
    pr_results  = scrape_pr_results()
    path = export_live_summary(party_seats, [], pr_results)
    console.print(f"[green]Live summary written → {path}[/]")


# ─────────────────────────────────────────────────────────────────
# EXPORT HELPER
# ─────────────────────────────────────────────────────────────────

def _export(
    party_seats: list[dict],
    constituencies: list[dict],
    pr_results: list[dict],
    args: argparse.Namespace,
) -> None:
    fmt = args.format

    if fmt in ("json", "both"):
        export_live_summary(party_seats, constituencies, pr_results)
        export_all_constituencies_json(constituencies)
        export_party_seats_json(party_seats, pr_results)
        # Per-constituency detail files
        if args.individual_json:
            for c in constituencies:
                export_constituency_detail_json(c)
            console.print(f"[green]Individual JSON files written to {JSON_DIR}/constituencies/[/]")

    if fmt in ("csv", "both"):
        export_candidates_csv(constituencies)
        export_party_summary_csv(party_seats, pr_results)
        export_constituency_summary_csv(constituencies)

    console.print(f"\n[bold green]✓ Export complete[/]")
    console.print(f"  JSON → [dim]{JSON_DIR}/[/]")
    if fmt in ("csv", "both"):
        console.print(f"  CSV  → [dim]{CSV_DIR}/[/]")


# ─────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="🇳🇵  Nepal Election 2082 Scraper — result.election.gov.np",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument(
        "--mode", "-m",
        choices=["full", "parties", "constituencies", "constituency", "pr", "live"],
        default="full",
        help="What to scrape (default: full)",
    )
    p.add_argument(
        "--id", type=int, metavar="CONST_ID",
        help="Constituency ID for --mode constituency (1–165)",
    )
    p.add_argument(
        "--const", "-c", type=int, nargs="+", metavar="ID",
        help="Space-separated list of constituency IDs to scrape",
    )
    p.add_argument(
        "--format", "-f",
        choices=["json", "csv", "both"],
        default="both",
        help="Output format (default: both)",
    )
    p.add_argument(
        "--images", "-i", action="store_true",
        help="Also download candidate photos and party symbols",
    )
    p.add_argument(
        "--individual-json", action="store_true",
        help="Write a separate JSON file for each constituency",
    )
    p.add_argument(
        "--concurrency", type=int, default=5, metavar="N",
        help="Async concurrency limit (default: 5 — be polite)",
    )
    p.add_argument(
        "--watch", "-w", type=int, metavar="SECONDS",
        help="Re-run every N seconds (live monitoring mode)",
    )
    return p


def main() -> None:
    ensure_dirs(JSON_DIR, CSV_DIR, IMAGES_DIR, LOG_DIR,
                f"{JSON_DIR}/constituencies",
                f"{IMAGES_DIR}/candidates",
                f"{IMAGES_DIR}/symbols")

    console.print(Panel(BANNER, border_style="red", padding=(0, 2)))

    parser = build_parser()
    args   = parser.parse_args()

    dispatch = {
        "full":           run_full,
        "parties":        run_parties,
        "constituencies": run_constituencies,
        "constituency":   run_single,
        "pr":             run_pr,
        "live":           run_live,
    }

    runner = dispatch[args.mode]

    if args.watch:
        console.print(f"[bold yellow]⏱  Watch mode: refreshing every {args.watch}s (Ctrl-C to stop)[/]\n")
        while True:
            try:
                runner(args)
                console.print(f"[dim]Sleeping {args.watch}s…[/]")
                time.sleep(args.watch)
            except KeyboardInterrupt:
                console.print("\n[yellow]Watch mode stopped.[/]")
                break
    else:
        runner(args)


if __name__ == "__main__":
    main()
