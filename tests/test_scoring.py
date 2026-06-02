"""Tests for the blinded review packet builder."""

from __future__ import annotations

from pathlib import Path

from src.scoring import build_packet, join_accuracy_scores
import pandas as pd


def _make_files(root: Path) -> tuple[Path, Path]:
    cleaned = root / "cleaned"
    rewrites = root / "rewrites"
    cleaned.mkdir()
    rewrites.mkdir()
    for pid in ["page-a", "page-b"]:
        (cleaned / f"{pid}.txt").write_text(f"original text for {pid}", encoding="utf-8")
        for mid in ["claude", "openai", "gemini"]:
            (rewrites / f"{pid}__{mid}.txt").write_text(f"{mid} rewrite of {pid}", encoding="utf-8")
    return cleaned, rewrites


def test_packet_and_key_roundtrip(tmp_path: Path):
    cleaned, rewrites = _make_files(tmp_path)
    out = tmp_path / "review"
    packet_path, key_path, entries = build_packet(
        page_ids=["page-a", "page-b"],
        model_ids=["claude", "openai", "gemini"],
        cleaned_dir=cleaned,
        rewrites_dir=rewrites,
        out_dir=out,
        seed=7,
    )
    assert len(entries) == 6
    blind_ids = [e.blind_id for e in entries]
    assert len(set(blind_ids)) == 6, "blind ids must be unique"

    # Simulate reviewer filling scores
    scored = pd.read_csv(packet_path)
    scored["accuracy_1_5"] = 4
    scored["completeness_1_5"] = 5
    scored["added_errors_1_5"] = 2
    scored_path = tmp_path / "scored.csv"
    scored.to_csv(scored_path, index=False)

    merged = join_accuracy_scores(scored_path, key_path)
    assert set(merged["page_id"]) == {"page-a", "page-b"}
    assert set(merged["model_id"]) == {"claude", "openai", "gemini"}
    assert (merged["accuracy_1_5"] == 4).all()


def test_packet_is_deterministic_with_seed(tmp_path: Path):
    cleaned, rewrites = _make_files(tmp_path)
    out1 = tmp_path / "r1"
    out2 = tmp_path / "r2"
    p1, _, e1 = build_packet(["page-a", "page-b"], ["claude", "openai", "gemini"],
                              cleaned, rewrites, out1, seed=11)
    p2, _, e2 = build_packet(["page-a", "page-b"], ["claude", "openai", "gemini"],
                              cleaned, rewrites, out2, seed=11)
    assert [e.blind_id for e in e1] == [e.blind_id for e in e2]
    assert [(e.page_id, e.model_id) for e in e1] == [(e.page_id, e.model_id) for e in e2]
