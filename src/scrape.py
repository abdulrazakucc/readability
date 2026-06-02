"""Page capture: download a URL, save raw HTML + provenance sidecar.

Designed to be polite (User-Agent + delays) and resumable (skip if hash exists).
Does NOT do robots.txt enforcement — callers must verify they have the right to
scrape each site before running this at scale.
"""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

import requests

from .provenance import sha256_bytes, utc_now_iso, write_provenance

log = logging.getLogger(__name__)

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 "
    "(cardiac-ct-readability-research; contact via repo)"
)
DEFAULT_TIMEOUT = 30


SITE_SHORT_NAMES = {
    "radiologyinfo.org": "radinfo",
    "heart.org": "aha",
    "cardiosmart.org": "acc",
    "bhf.org.uk": "bhf",
    "mayoclinic.org": "mayo",
    "clevelandclinic.org": "cleveland",
    "hopkinsmedicine.org": "jhmi",
    "stanfordhealthcare.org": "stanford",
    "ucsfhealth.org": "ucsf",
    "brighamandwomens.org": "bwh",
}


def site_short_name(url: str) -> str:
    host = urlparse(url).netloc.lower().lstrip("www.")
    # Strip leading www.
    if host.startswith("www."):
        host = host[4:]
    for domain, short in SITE_SHORT_NAMES.items():
        if host.endswith(domain):
            return short
    # Fallback: first label of the registered domain
    return re.sub(r"[^a-z0-9]+", "", host.split(".")[0])


def page_id(url: str, procedure: str) -> str:
    site = site_short_name(url)
    hsh = sha256_bytes(url.encode("utf-8"))[:8]
    return f"{site}__{procedure}__{hsh}"


@dataclass
class CaptureResult:
    page_id: str
    url: str
    procedure: str
    status: int
    raw_path: Path
    provenance_path: Path
    captured_at_utc: str
    content_sha256: str
    bytes_size: int
    skipped: bool


def fetch_url(
    url: str,
    user_agent: str = DEFAULT_USER_AGENT,
    timeout: int = DEFAULT_TIMEOUT,
) -> tuple[int, bytes]:
    resp = requests.get(
        url,
        timeout=timeout,
        headers={"User-Agent": user_agent, "Accept-Language": "en-US,en;q=0.9"},
        allow_redirects=True,
    )
    return resp.status_code, resp.content


def capture(
    url: str,
    procedure: str,
    raw_dir: Path,
    user_agent: str = DEFAULT_USER_AGENT,
    timeout: int = DEFAULT_TIMEOUT,
    polite_delay: float = 1.5,
    force: bool = False,
) -> CaptureResult:
    pid = page_id(url, procedure)
    raw_path = raw_dir / f"{pid}.html"
    prov_path = raw_dir / f"{pid}.provenance.json"

    if raw_path.exists() and not force:
        # Resumable — read existing hash for the result object
        content_sha = sha256_bytes(raw_path.read_bytes())
        return CaptureResult(
            page_id=pid,
            url=url,
            procedure=procedure,
            status=200,
            raw_path=raw_path,
            provenance_path=prov_path,
            captured_at_utc=utc_now_iso(),
            content_sha256=content_sha,
            bytes_size=raw_path.stat().st_size,
            skipped=True,
        )

    if polite_delay > 0:
        time.sleep(polite_delay)

    status, body = fetch_url(url, user_agent=user_agent, timeout=timeout)
    captured_at = utc_now_iso()

    raw_path.write_bytes(body)
    content_sha = sha256_bytes(body)

    write_provenance(
        prov_path,
        {
            "page_id": pid,
            "url": url,
            "procedure": procedure,
            "captured_at_utc": captured_at,
            "http_status": status,
            "content_sha256": content_sha,
            "bytes_size": len(body),
            "user_agent": user_agent,
        },
    )

    return CaptureResult(
        page_id=pid,
        url=url,
        procedure=procedure,
        status=status,
        raw_path=raw_path,
        provenance_path=prov_path,
        captured_at_utc=captured_at,
        content_sha256=content_sha,
        bytes_size=len(body),
        skipped=False,
    )
