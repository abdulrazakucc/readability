"""Blinded review packet builder and accuracy-score join.

For Aim 3:
- For each page, take the three rewrites and produce a blinded packet.
- Shuffle rewrite order using a seeded RNG (reproducibility).
- Strip model identifiers; assign each rewrite a `blind_id`.
- Emit `blind_key.csv` separately (never shipped to the reviewer).
- After reviewer returns scored sheets, `join_accuracy_scores` unblinds.
"""

from __future__ import annotations

import csv
import random
import string
from dataclasses import dataclass
from pathlib import Path

import pandas as pd


def _make_blind_id(rng: random.Random, length: int = 10) -> str:
    alphabet = string.ascii_uppercase + string.digits
    return "B-" + "".join(rng.choice(alphabet) for _ in range(length))


@dataclass
class PacketEntry:
    blind_id: str
    page_id: str
    model_id: str
    original_path: Path
    rewrite_path: Path


def build_packet(
    page_ids: list[str],
    model_ids: list[str],
    cleaned_dir: Path,
    rewrites_dir: Path,
    out_dir: Path,
    seed: int = 42,
) -> tuple[Path, Path, list[PacketEntry]]:
    """Build review packet and blind key.

    Returns (packet_csv_path, blind_key_csv_path, entries).
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    rng = random.Random(seed)

    entries: list[PacketEntry] = []
    for pid in page_ids:
        per_page: list[PacketEntry] = []
        for mid in model_ids:
            rewrite_path = rewrites_dir / f"{pid}__{mid}.txt"
            if not rewrite_path.exists():
                continue
            blind = _make_blind_id(rng)
            per_page.append(
                PacketEntry(
                    blind_id=blind,
                    page_id=pid,
                    model_id=mid,
                    original_path=cleaned_dir / f"{pid}.txt",
                    rewrite_path=rewrite_path,
                )
            )
        rng.shuffle(per_page)
        entries.extend(per_page)

    packet_path = out_dir / "review_packet.csv"
    blind_key_path = out_dir / "blind_key.csv"

    with packet_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "blind_id",
                "original_text_path",
                "rewrite_text_path",
                "accuracy_1_5",
                "completeness_1_5",
                "added_errors_1_5",
                "notes",
            ]
        )
        for e in entries:
            w.writerow(
                [
                    e.blind_id,
                    str(e.original_path),
                    str(e.rewrite_path),
                    "",
                    "",
                    "",
                    "",
                ]
            )

    with blind_key_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["blind_id", "page_id", "model_id"])
        for e in entries:
            w.writerow([e.blind_id, e.page_id, e.model_id])

    return packet_path, blind_key_path, entries


def join_accuracy_scores(
    scored_packet_path: Path,
    blind_key_path: Path,
) -> pd.DataFrame:
    """Join a returned scored packet (with the four numeric columns filled) to the blind key.

    Returns a DataFrame with columns:
      page_id, model_id, blind_id, accuracy_1_5, completeness_1_5, added_errors_1_5, notes
    """
    scored = pd.read_csv(scored_packet_path)
    key = pd.read_csv(blind_key_path)
    merged = scored.merge(key, on="blind_id", how="left", validate="one_to_one")
    return merged[
        [
            "page_id",
            "model_id",
            "blind_id",
            "accuracy_1_5",
            "completeness_1_5",
            "added_errors_1_5",
            "notes",
        ]
    ]
