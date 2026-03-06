"""
utils.py — Shared utilities: logging, retry, text normalisation, HTML helpers
"""

from __future__ import annotations

import functools
import logging
import re
import sys
import time
import unicodedata
from pathlib import Path
from typing import Any, Callable

from rich.console import Console
from rich.logging import RichHandler

console = Console()


# ─────────────────────────────────────────────────────────────────
# LOGGING
# ─────────────────────────────────────────────────────────────────

def get_logger(name: str, log_dir: str = "logs") -> logging.Logger:
    """Return a Rich-formatted logger that also writes to a file."""
    Path(log_dir).mkdir(parents=True, exist_ok=True)
    log_file = Path(log_dir) / "scraper.log"

    logger = logging.getLogger(name)
    if logger.handlers:          # avoid duplicate handlers on re-import
        return logger

    logger.setLevel(logging.DEBUG)

    # Console handler (Rich — pretty colours)
    ch = RichHandler(console=console, rich_tracebacks=True, markup=True)
    ch.setLevel(logging.INFO)

    # File handler (plain text, full DEBUG)
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter("%(asctime)s  %(levelname)-8s  %(name)s  %(message)s"))

    logger.addHandler(ch)
    logger.addHandler(fh)
    return logger


# ─────────────────────────────────────────────────────────────────
# RETRY DECORATOR
# ─────────────────────────────────────────────────────────────────

def retry(
    max_attempts: int = 4,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,),
    logger_name: str = "retry",
) -> Callable:
    """
    Decorator: retry *max_attempts* times with exponential back-off.

    Usage:
        @retry(max_attempts=3, backoff=1.5)
        def fetch(url): ...
    """
    log = get_logger(logger_name)

    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            delay = backoff
            for attempt in range(1, max_attempts + 1):
                try:
                    return fn(*args, **kwargs)
                except exceptions as exc:
                    if attempt == max_attempts:
                        log.error(f"[bold red]{fn.__name__} failed after {max_attempts} attempts:[/] {exc}")
                        raise
                    log.warning(
                        f"[yellow]{fn.__name__} attempt {attempt}/{max_attempts} failed:[/] {exc} "
                        f"— retrying in {delay:.1f}s"
                    )
                    time.sleep(delay)
                    delay *= backoff
        return wrapper
    return decorator


# ─────────────────────────────────────────────────────────────────
# DEVANAGARI / TEXT HELPERS
# ─────────────────────────────────────────────────────────────────

# Devanagari digit → ASCII digit map
_DEVA_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")

def deva_to_int(text: str) -> int | None:
    """Convert Devanagari or ASCII digit string to int. Returns None on failure."""
    if not text:
        return None
    cleaned = text.translate(_DEVA_DIGITS).replace(",", "").replace(".", "").strip()
    try:
        return int(cleaned)
    except ValueError:
        return None


def normalize_text(text: str) -> str:
    """Strip, collapse whitespace, normalise Unicode."""
    if not text:
        return ""
    text = unicodedata.normalize("NFC", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def clean_name(name: str) -> str:
    """Normalise a candidate/party name."""
    name = normalize_text(name)
    # Remove common suffix noise from OCR/copy-paste
    name = re.sub(r"\s*\(.*?\)\s*$", "", name)
    return name


def extract_number(text: str) -> int | None:
    """Pull the first integer (Devanagari or ASCII) from a string."""
    if not text:
        return None
    digits = re.sub(r"[^\d०-९,]", "", text).replace(",", "")
    digits = digits.translate(_DEVA_DIGITS)
    try:
        return int(digits) if digits else None
    except ValueError:
        return None


# ─────────────────────────────────────────────────────────────────
# HTML HELPERS
# ─────────────────────────────────────────────────────────────────

def get_text(tag) -> str:
    """Safe .get_text() with normalization."""
    if tag is None:
        return ""
    return normalize_text(tag.get_text(separator=" "))


def get_table_rows(soup, table_index: int = 0) -> list[list[str]]:
    """
    Extract all <tr> rows from the nth table on a page.
    Returns list of row-cell text lists, skipping header rows.
    """
    tables = soup.find_all("table")
    if table_index >= len(tables):
        return []

    rows: list[list[str]] = []
    for tr in tables[table_index].find_all("tr"):
        cells = [get_text(td) for td in tr.find_all(["td", "th"])]
        if cells:
            rows.append(cells)
    return rows


def find_table_with_header(soup, *header_keywords: str):
    """
    Find the first <table> whose first row contains all given keywords
    (case-insensitive, supports both English and Devanagari).
    """
    for table in soup.find_all("table"):
        first_row = table.find("tr")
        if not first_row:
            continue
        header_text = normalize_text(first_row.get_text()).lower()
        if all(kw.lower() in header_text for kw in header_keywords):
            return table
    return None


# ─────────────────────────────────────────────────────────────────
# FILE HELPERS
# ─────────────────────────────────────────────────────────────────

def ensure_dirs(*paths: str) -> None:
    """Create directories if they don't exist."""
    for p in paths:
        Path(p).mkdir(parents=True, exist_ok=True)


def sanitize_filename(name: str) -> str:
    """Make a string safe to use as a filename."""
    name = normalize_text(name)
    # Replace characters not safe in filenames
    name = re.sub(r'[\\/*?:"<>|]', "_", name)
    name = re.sub(r"\s+", "_", name)
    return name[:80]   # cap length
