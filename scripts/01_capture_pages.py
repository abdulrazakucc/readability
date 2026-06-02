#!/usr/bin/env python3
"""Capture raw HTML for every URL in an input list.

Input: a CSV at `data/urls.csv` with columns: procedure,url,notes
Output:
  - `data/raw/<page_id>.html` per URL
  - `data/raw/<page_id>.provenance.json` per URL
  - rows appended to `data/manifest.csv`

Idempotent: re-running skips URLs that already have a raw file unless --force.
"""

from __future__ import annotations

import argparse
import csv
import logging
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from src.config import RAW_DIR, MANIFEST_PATH, ensure_dirs, load_config  # noqa: E402
from src.scrape import capture, page_id, site_short_name  # noqa: E402
from src.provenance import git_sha, utc_now_iso  # noqa: E402

log = logging.getLogger("capture")


MANIFEST_COLUMNS = [
    "page_id",
    "procedure",
    "site",
    "url",
    "captured_at",
    "http_status",
    "raw_path",
    "cleaned_path",
    "word_count_raw",
    "word_count_cleaned",
    "include",
    "exclusion_reason",
    "notes",
    "git_sha_at_capture",
]


def _read_existing_manifest(path: Path) -> dict[str, dict]:
    if not path.exists():
        return {}
    by_id: dict[str, dict] = {}
    with path.open("r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            by_id[row["page_id"]] = row
    return by_id


def _write_manifest(path: Path, rows: dict[str, dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=MANIFEST_COLUMNS)
        w.writeheader()
        for r in rows.values():
            w.writerow({c: r.get(c, "") for c in MANIFEST_COLUMNS})


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--urls", default=str(REPO_ROOT / "data" / "urls.csv"))
    parser.add_argument("--config", default=None)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    ensure_dirs()
    cfg = load_config(args.config)

    urls_path = Path(args.urls)
    if not urls_path.exists():
        log.error("URL list not found at %s. Create it with columns: procedure,url,notes", urls_path)
        return 2

    rows_by_id = _read_existing_manifest(MANIFEST_PATH)

    with urls_path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            procedure = row["procedure"].strip().lower()
            url = row["url"].strip()
            notes = row.get("notes", "").strip()
            if not url:
                continue
            pid = page_id(url, procedure)

            if args.dry_run:
                log.info("[dry-run] would capture %s -> %s", url, pid)
                continue

            try:
                result = capture(
                    url=url,
                    procedure=procedure,
                    raw_dir=RAW_DIR,
                    user_agent=cfg.get("user_agent", default=None) or None,
                    timeout=int(cfg.get("request_timeout_seconds", default=30)),
                    polite_delay=float(cfg.get("polite_delay_seconds", default=1.5)),
                    force=args.force,
                )
            except Exception as exc:
                log.exception("failed to capture %s: %s", url, exc)
                continue

            rows_by_id[pid] = {
                **rows_by_id.get(pid, {}),
                "page_id": pid,
                "procedure": procedure,
                "site": site_short_name(url),
                "url": url,
                "captured_at": result.captured_at_utc,
                "http_status": result.status,
                "raw_path": str(result.raw_path.relative_to(REPO_ROOT)),
                "include": rows_by_id.get(pid, {}).get("include", ""),
                "exclusion_reason": rows_by_id.get(pid, {}).get("exclusion_reason", ""),
                "notes": notes or rows_by_id.get(pid, {}).get("notes", ""),
                "git_sha_at_capture": git_sha(REPO_ROOT),
            }
            log.info("captured %s (status=%d, %d bytes, skipped=%s)",
                     pid, result.status, result.bytes_size, result.skipped)

    if not args.dry_run:
        _write_manifest(MANIFEST_PATH, rows_by_id)
        log.info("manifest written: %s (%d rows)", MANIFEST_PATH, len(rows_by_id))
    return 0


if __name__ == "__main__":
    sys.exit(main())
