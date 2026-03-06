"""
image_downloader.py — Download candidate photos and party symbols from ECN.

Saves to output/images/{candidates,symbols}/ with sanitised filenames.
Skips already-downloaded files for resumable runs.
"""

from __future__ import annotations

import asyncio
import hashlib
import mimetypes
from pathlib import Path

import aiofiles
import aiohttp

from config import IMAGES_DIR, REQUEST_HEADERS, TIMEOUT_SECONDS, CONCURRENCY
from utils import get_logger, ensure_dirs, sanitize_filename

log = get_logger("image_downloader")

CAND_DIR   = f"{IMAGES_DIR}/candidates"
SYMBOL_DIR = f"{IMAGES_DIR}/symbols"


def _url_to_filename(url: str, prefix: str = "") -> str:
    """Derive a safe filename from a URL."""
    path = url.split("?")[0].rstrip("/")
    ext  = Path(path).suffix or ".jpg"
    stem = sanitize_filename(Path(path).stem)
    if not stem:
        stem = hashlib.md5(url.encode()).hexdigest()[:12]
    return f"{prefix}{stem}{ext}"


async def _download_one(
    session: aiohttp.ClientSession,
    url: str,
    dest: Path,
    semaphore: asyncio.Semaphore,
) -> bool:
    """Download a single image. Returns True on success."""
    if dest.exists():
        return True   # already downloaded

    async with semaphore:
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=TIMEOUT_SECONDS)) as resp:
                if resp.status != 200:
                    return False
                content = await resp.read()
        except Exception as exc:
            log.warning(f"[yellow]Image download failed:[/] {url} — {exc}")
            return False

    async with aiofiles.open(dest, "wb") as f:
        await f.write(content)
    log.debug(f"Downloaded: {dest.name}")
    return True


async def _download_batch(urls_dests: list[tuple[str, Path]], concurrency: int) -> dict[str, bool]:
    """Download multiple images concurrently. Returns {url: success}."""
    semaphore = asyncio.Semaphore(concurrency)
    connector = aiohttp.TCPConnector(limit=concurrency, ssl=False)

    async with aiohttp.ClientSession(headers=REQUEST_HEADERS, connector=connector) as session:
        tasks = {
            url: _download_one(session, url, dest, semaphore)
            for url, dest in urls_dests
        }
        results = await asyncio.gather(*tasks.values(), return_exceptions=False)
        return dict(zip(tasks.keys(), results))


def download_candidate_images(constituencies: list[dict], concurrency: int = CONCURRENCY) -> int:
    """
    Download all candidate photos found in the scraped data.
    Returns count of newly downloaded images.
    """
    ensure_dirs(CAND_DIR, SYMBOL_DIR)

    pairs: list[tuple[str, Path]] = []
    for const in constituencies:
        for cand in const.get("candidates", []):
            # Photo
            photo_url = cand.get("photo_url")
            if photo_url and photo_url.startswith("http"):
                fname = _url_to_filename(photo_url, prefix="cand_")
                dest  = Path(CAND_DIR) / fname
                # Store resolved local path back into the data dict
                cand["photo_local"] = str(dest)
                pairs.append((photo_url, dest))

            # Symbol
            sym_url = cand.get("symbol_url")
            if sym_url and sym_url.startswith("http"):
                fname = _url_to_filename(sym_url, prefix="sym_")
                dest  = Path(SYMBOL_DIR) / fname
                cand["symbol_local"] = str(dest)
                pairs.append((sym_url, dest))

    if not pairs:
        log.info("No images to download.")
        return 0

    log.info(f"Downloading {len(pairs)} images (concurrency={concurrency})…")
    results = asyncio.run(_download_batch(pairs, concurrency))

    success = sum(1 for ok in results.values() if ok)
    failed  = len(results) - success
    log.info(f"[green]Images done:[/] {success} OK, {failed} failed")
    return success
