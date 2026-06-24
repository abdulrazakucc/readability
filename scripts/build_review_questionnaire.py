#!/usr/bin/env python3
"""Build a self-contained, interactive HTML questionnaire for Aim 3 clinical scoring.

One file works for all reviewers: each reviewer opens it in a browser, enters their
name/role, scores every blinded rewrite on the three 1-5 rubric dimensions, and
exports a CSV keyed by `blind_id`. That CSV joins straight back to
`data/review/blind_key.csv` to un-blind, so no spreadsheet is ever hand-edited and
the reproducibility floor stays intact.

Input:
  data/review/review_packet_with_text.csv   (built by scripts/06_build_review_packet.py)

Output:
  data/review/aim3_accuracy_questionnaire.html
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from src.config import REVIEW_DIR, ensure_dirs  # noqa: E402

log = logging.getLogger("questionnaire")

PACKET_NAME = "review_packet_with_text.csv"
OUTPUT_NAME = "aim3_accuracy_questionnaire.html"
PARTS_DIRNAME = "questionnaire_parts"
N_PARTS = 3


def load_items(packet_path: Path) -> list[dict]:
    with packet_path.open("r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    items = []
    for r in rows:
        items.append(
            {
                "blind_id": r["blind_id"],
                "original_text": r["original_text"],
                "rewrite_text": r["rewrite_text"],
            }
        )
    return items


def build_html(
    items: list[dict],
    *,
    store_key: str = "aim3_questionnaire_v1",
    csv_suffix: str = "",
    part_eyebrow: str = "",
    part_banner: str = "",
) -> str:
    """Render one self-contained questionnaire file.

    `store_key` and `csv_suffix` are made unique per split part so a reviewer who
    opens more than one part on the same device gets independent drafts and
    distinctly-named CSV downloads. With the defaults the output is byte-identical
    to the original single-file questionnaire.
    """
    # Embedded as JSON so the page is fully self-contained (no server, no fetch).
    items_json = json.dumps(items, ensure_ascii=False)
    return (
        _TEMPLATE.replace("/*__ITEMS__*/", items_json)
        .replace("__N_ITEMS__", str(len(items)))
        .replace("__STORE_KEY__", store_key)
        .replace("__CSV_SUFFIX__", csv_suffix)
        .replace("__PART_EYEBROW__", part_eyebrow)
        .replace("__PART_BANNER__", part_banner)
    )


def split_ranges(n: int, parts: int) -> list[tuple[int, int]]:
    """Contiguous, as-balanced-as-possible (start, end) slices over the fixed order.

    Splitting contiguously preserves the seeded randomized item order, so each part
    stays model-interleaved and blinding is unaffected.
    """
    base, rem = divmod(n, parts)
    ranges, start = [], 0
    for i in range(parts):
        size = base + (1 if i < rem else 0)
        ranges.append((start, start + size))
        start += size
    return ranges


def build_part_html(items: list[dict], part_no: int, parts: int, total: int, start: int) -> str:
    """Render one split part with its own storage key, CSV suffix, and banner."""
    n = len(items)
    first, last = start + 1, start + n
    eyebrow = f" &middot; Part {part_no} of {parts}"
    banner = (
        '<div class="part-banner">'
        f'<span class="pb-chip">Part {part_no} of {parts}</span>'
        f'<span class="pb-text">This set contains <b>{n}</b> rewrites '
        f"(items {first}&ndash;{last} of the full {total}). "
        "Two reviewers independently score this same set; please complete every item.</span>"
        "</div>"
    )
    return build_html(
        items,
        store_key=f"aim3_questionnaire_v1_part{part_no}of{parts}",
        csv_suffix=f"_part{part_no}of{parts}",
        part_eyebrow=eyebrow,
        part_banner=banner,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet", default=str(REVIEW_DIR / PACKET_NAME))
    parser.add_argument("--out", default=str(REVIEW_DIR / OUTPUT_NAME))
    parser.add_argument("--parts-dir", default=str(REVIEW_DIR / PARTS_DIRNAME))
    parser.add_argument("--parts", type=int, default=N_PARTS, help="number of split parts to emit")
    parser.add_argument(
        "--no-parts", action="store_true", help="only emit the full single-file questionnaire"
    )
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    ensure_dirs()

    packet_path = Path(args.packet)
    if not packet_path.exists():
        log.error("packet not found: %s (run scripts/06_build_review_packet.py first)", packet_path)
        return 1

    items = load_items(packet_path)

    # 1) The complete single-file questionnaire (unchanged deliverable).
    out_path = Path(args.out)
    out_path.write_text(build_html(items), encoding="utf-8")
    log.info("wrote full questionnaire with %d items -> %s", len(items), out_path)

    if args.no_parts:
        return 0

    # 2) Split parts: each is a standalone HTML file covering a contiguous slice of
    #    the fixed order, for handing to a separate pair of reviewers.
    total = len(items)
    parts_dir = Path(args.parts_dir)
    parts_dir.mkdir(parents=True, exist_ok=True)
    ranges = split_ranges(total, args.parts)
    for i, (start, end) in enumerate(ranges, start=1):
        subset = items[start:end]
        html = build_part_html(subset, i, args.parts, total, start)
        part_path = parts_dir / f"aim3_accuracy_questionnaire_part_{i}_of_{args.parts}.html"
        part_path.write_text(html, encoding="utf-8")
        log.info(
            "wrote part %d/%d: items %d-%d (%d) -> %s",
            i, args.parts, start + 1, end, len(subset), part_path,
        )

    log.info("Hand ONE part file to each reviewer pair. Each reviewer exports their own CSV.")
    return 0


# --------------------------------------------------------------------------------------
# The HTML template. `/*__ITEMS__*/` is replaced with the packet JSON and `__N_ITEMS__`
# with the item count. Kept as one string so the script emits a single portable file.
# --------------------------------------------------------------------------------------
_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Aim 3 — Clinical Accuracy Scoring</title>
<style>
  :root {
    --navy: #102a43;
    --navy-2: #243b53;
    --teal: #0b7285;
    --teal-2: #0ca5b8;
    --bg: #f5f7fa;
    --card: #ffffff;
    --line: #e2e8f0;
    --ink: #1f2933;
    --muted: #627d98;
    --amber: #b54708;
    --amber-bg: #fffaf0;
    --green: #0a7c52;
    --shadow: 0 1px 3px rgba(16,42,67,.08), 0 6px 20px rgba(16,42,67,.06);
    --radius: 14px;
  }
  * { box-sizing: border-box; }
  html { scroll-behavior: smooth; }
  body {
    margin: 0; background: var(--bg); color: var(--ink);
    font: 16px/1.6 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    -webkit-font-smoothing: antialiased; padding-bottom: 96px;
  }
  a { color: var(--teal); }

  /* ---- Hero ---- */
  .hero {
    background: linear-gradient(135deg, var(--navy) 0%, var(--navy-2) 55%, var(--teal) 140%);
    color: #fff; padding: 40px 24px 32px;
  }
  .hero-inner { max-width: 1180px; margin: 0 auto; }

  /* ---- Brand bar (Mayo Clinic) ---- */
  .brandbar {
    display: flex; align-items: flex-end; justify-content: space-between; gap: 16px;
    margin-bottom: 26px; padding-bottom: 18px; border-bottom: 1px solid rgba(255,255,255,.16);
  }
  .brand { display: flex; align-items: center; gap: 16px; }
  .mayo-mark { width: 70px; height: auto; display: block; }
  .wordmark {
    font-family: "Iowan Old Style", "Palatino Linotype", "Book Antiqua", Palatino, Georgia, serif;
    font-size: 28px; font-weight: 600; letter-spacing: .005em; color: #fff;
  }
  .brand-meta { text-align: right; line-height: 1.3; }
  .bm-label {
    display: block; font-size: 10px; text-transform: uppercase; letter-spacing: .12em;
    color: #9fd8e0; font-weight: 700;
  }
  .bm-name { display: block; font-size: 13px; color: #e8f1f8; font-weight: 600; }
  .eyebrow {
    text-transform: uppercase; letter-spacing: .14em; font-size: 12px; font-weight: 700;
    color: #9fd8e0; margin: 0 0 10px;
  }
  .hero h1 { margin: 0 0 8px; font-size: 30px; line-height: 1.2; font-weight: 800; }
  .hero p { margin: 0; max-width: 760px; color: #cfe0ee; font-size: 16px; }
  .hero .lead { color: #fff; font-weight: 600; margin-top: 14px; font-size: 17px; }

  .wrap { max-width: 1180px; margin: 0 auto; padding: 0 24px; }

  /* ---- Cards ---- */
  .card {
    background: var(--card); border: 1px solid var(--line); border-radius: var(--radius);
    box-shadow: var(--shadow); padding: 24px; margin: 22px 0;
  }
  .card h2 {
    margin: 0 0 14px; font-size: 19px; color: var(--navy); display: flex; align-items: center; gap: 10px;
  }
  .card h2 .num {
    display: inline-grid; place-items: center; width: 28px; height: 28px; border-radius: 50%;
    background: var(--teal); color: #fff; font-size: 14px; font-weight: 700;
  }

  /* ---- Reviewer identity ---- */
  .id-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; }
  .field label { display: block; font-size: 13px; font-weight: 700; color: var(--muted); margin-bottom: 6px; }
  .field input, .field select {
    width: 100%; padding: 11px 12px; border: 1px solid var(--line); border-radius: 9px;
    font-size: 15px; background: #fff; color: var(--ink);
  }
  .field input:focus, .field select:focus { outline: 2px solid var(--teal-2); border-color: var(--teal-2); }

  /* ---- Rubric ---- */
  .rubric { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; }
  .dim {
    border: 1px solid var(--line); border-radius: 12px; padding: 16px; background: #fbfdff;
  }
  .dim.reverse { background: var(--amber-bg); border-color: #f6d8a8; }
  .dim h3 { margin: 0 0 4px; font-size: 16px; color: var(--navy); }
  .dim .tag {
    font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: .06em;
    color: var(--green);
  }
  .dim.reverse .tag { color: var(--amber); }
  .dim .q { font-size: 13.5px; color: var(--muted); margin: 6px 0 12px; }
  .anchors { list-style: none; margin: 0; padding: 0; font-size: 13px; }
  .anchors li { display: flex; gap: 8px; padding: 4px 0; border-top: 1px dashed var(--line); }
  .anchors li:first-child { border-top: none; }
  .anchors .s {
    flex: 0 0 22px; height: 22px; border-radius: 6px; background: var(--navy); color: #fff;
    display: grid; place-items: center; font-weight: 700; font-size: 12px;
  }
  .dim.reverse .anchors .s { background: var(--amber); }
  .callout {
    margin-top: 16px; background: #eef6f8; border-left: 4px solid var(--teal);
    padding: 12px 16px; border-radius: 8px; font-size: 14px;
  }
  .callout.warn { background: var(--amber-bg); border-left-color: var(--amber); }

  ul.rules { margin: 6px 0 0; padding-left: 18px; }
  ul.rules li { margin: 5px 0; }

  /* ---- Part banner (only present on split parts) ---- */
  .part-banner {
    display: flex; align-items: center; gap: 14px; flex-wrap: wrap;
    margin-top: 20px; padding: 13px 18px; border-radius: 12px;
    background: rgba(255,255,255,.08); border: 1px solid rgba(255,255,255,.18);
  }
  .pb-chip {
    font-size: 12px; font-weight: 800; letter-spacing: .06em; text-transform: uppercase;
    color: var(--navy); background: #9fd8e0; padding: 6px 13px; border-radius: 999px; white-space: nowrap;
  }
  .pb-text { font-size: 14px; color: #e8f1f8; }
  .pb-text b { color: #fff; }

  /* ---- Item cards ---- */
  .item {
    background: var(--card); border: 1px solid var(--line); border-radius: var(--radius);
    box-shadow: var(--shadow); margin: 18px 0; overflow: hidden; scroll-margin-top: 16px;
  }
  .item-head {
    display: flex; align-items: center; justify-content: space-between; gap: 12px;
    padding: 14px 20px; background: #f0f4f8; border-bottom: 1px solid var(--line);
  }
  .item-head .left { display: flex; align-items: center; gap: 12px; }
  .item-head .right { display: flex; align-items: center; gap: 10px; }
  .expand-btn {
    border: 1px solid var(--line); background: #fff; color: var(--teal);
    font: inherit; font-size: 12.5px; font-weight: 700; padding: 6px 13px;
    border-radius: 999px; cursor: pointer; white-space: nowrap; transition: all .12s ease;
  }
  .expand-btn:hover { background: #f0fbfc; border-color: var(--teal-2); }
  .seq { font-weight: 800; color: var(--navy); font-size: 15px; }
  .badge {
    font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 12px;
    background: var(--navy); color: #fff; padding: 4px 10px; border-radius: 999px; letter-spacing: .03em;
  }
  .done-pill {
    font-size: 12px; font-weight: 700; padding: 4px 10px; border-radius: 999px;
    background: #e3f2ec; color: var(--green); display: none;
  }
  .item.complete .done-pill { display: inline-block; }
  .item.complete .item-head { background: #ecf7f1; }

  .texts { display: grid; grid-template-columns: 1fr 1fr; gap: 0; }
  .col { padding: 18px 20px; position: relative; }
  .col.orig { border-right: 1px solid var(--line); background: #fcfdfe; }
  .col h4 {
    margin: 0 0 10px; font-size: 12px; text-transform: uppercase; letter-spacing: .08em;
    color: var(--muted); display: flex; align-items: center; gap: 8px;
  }
  .col h4 .dot { width: 9px; height: 9px; border-radius: 50%; background: var(--muted); }
  .col.rewrite h4 .dot { background: var(--teal); }
  .text {
    white-space: pre-wrap; font-size: 15px; line-height: 1.72; max-height: 460px; overflow-y: auto;
    padding-right: 10px; color: #334e68;
  }
  .item.expanded .text { max-height: none; overflow-y: visible; }
  .text::-webkit-scrollbar { width: 8px; }
  .text::-webkit-scrollbar-thumb { background: #cbd6e2; border-radius: 8px; }
  /* fade cue at the bottom of a scrollable (collapsed) passage */
  .col .fade {
    display: none; position: absolute; left: 0; right: 0; bottom: 0; height: 56px; pointer-events: none;
    background: linear-gradient(to bottom, rgba(252,253,254,0), #fcfdfe 78%);
    border-radius: 0 0 12px 12px;
  }
  .col.rewrite .fade { background: linear-gradient(to bottom, rgba(255,255,255,0), #fff 78%); }
  .col.has-overflow .fade { display: block; }
  .item.expanded .col .fade { display: none; }

  .score-zone { padding: 20px; border-top: 1px solid var(--line); background: #f4f7fb; }
  .score-title {
    font-size: 12px; text-transform: uppercase; letter-spacing: .08em; font-weight: 800;
    color: var(--muted); margin: 0 0 12px;
  }
  .score-row { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; }

  /* Each dimension sits in its own panel with its own colour-coded border. */
  .scorer {
    background: #fff; border: 1px solid var(--line);
    border-top: 4px solid var(--accent, var(--teal));
    border-radius: 12px; padding: 14px 15px 16px;
    box-shadow: 0 1px 2px rgba(16,42,67,.05);
  }
  .scorer[data-dim="accuracy_1_5"]     { --accent: #2b6cb0; }
  .scorer[data-dim="completeness_1_5"] { --accent: #0a7c52; }
  .scorer[data-dim="added_errors_1_5"] { --accent: #b54708; background: #fffdf7; }

  .scorer-head { display: flex; align-items: center; gap: 8px; }
  .scorer-head .dim-dot { width: 11px; height: 11px; border-radius: 50%; background: var(--accent); flex: 0 0 auto; }
  .scorer-head .dim-name { font-size: 14.5px; font-weight: 800; color: var(--navy); }
  .scorer-head .dim-dir {
    margin-left: auto; font-size: 10px; font-weight: 800; text-transform: uppercase;
    letter-spacing: .05em; color: var(--accent); border: 1px solid currentColor;
    padding: 2px 7px; border-radius: 999px; opacity: .85;
  }
  .scorer .dim-sub { font-size: 12px; color: var(--muted); margin: 7px 0 12px; min-height: 30px; }

  .opts { display: flex; gap: 6px; }
  .opts label {
    flex: 1; text-align: center; border: 1px solid var(--line); border-radius: 9px;
    padding: 10px 0; cursor: pointer; font-weight: 700; color: var(--navy-2); user-select: none;
    transition: all .12s ease; font-size: 15px; background: #fff;
  }
  .opts input { position: absolute; opacity: 0; pointer-events: none; }
  .opts label:hover { border-color: var(--accent); background: #f7fbfd; }
  .opts input:checked + label,
  .opts label.checked { background: var(--accent); color: #fff; border-color: var(--accent); }
  .notes-wrap { margin-top: 16px; }
  .notes-wrap label { font-size: 13px; font-weight: 700; color: var(--navy); }
  .notes-wrap .hint { font-weight: 500; color: var(--muted); font-size: 12px; margin-left: 6px; }
  .notes-wrap textarea {
    width: 100%; margin-top: 6px; min-height: 48px; resize: vertical; padding: 10px 12px;
    border: 1px solid var(--line); border-radius: 9px; font: inherit; font-size: 14px;
  }
  .notes-wrap textarea:focus { outline: 2px solid var(--teal-2); border-color: var(--teal-2); }
  .notes-wrap.flag textarea { border-color: var(--amber); background: var(--amber-bg); }
  .flag-note { display: none; color: var(--amber); font-size: 12px; font-weight: 600; margin-top: 4px; }
  .notes-wrap.flag .flag-note { display: block; }

  /* ---- Sticky footer ---- */
  .footer {
    position: fixed; bottom: 0; left: 0; right: 0; z-index: 50;
    background: rgba(255,255,255,.96); backdrop-filter: blur(8px);
    border-top: 1px solid var(--line); box-shadow: 0 -4px 20px rgba(16,42,67,.08);
  }
  .footer-inner {
    max-width: 1180px; margin: 0 auto; padding: 12px 24px; display: flex;
    align-items: center; gap: 18px;
  }
  .progress { flex: 1; }
  .progress .meta { display: flex; justify-content: space-between; font-size: 13px; margin-bottom: 6px; }
  .progress .meta b { color: var(--navy); }
  .bar { height: 9px; background: #e2e8f0; border-radius: 999px; overflow: hidden; }
  .bar > span { display: block; height: 100%; width: 0%; background: linear-gradient(90deg, var(--teal), var(--teal-2)); transition: width .25s ease; }
  .btn {
    border: none; border-radius: 10px; padding: 12px 18px; font-size: 15px; font-weight: 700;
    cursor: pointer; white-space: nowrap;
  }
  .btn.primary { background: var(--teal); color: #fff; }
  .btn.primary:hover { background: #095e6e; }
  .btn.ghost { background: #eef2f6; color: var(--navy); }
  .btn.ghost:hover { background: #e1e8ef; }
  .saved-tag { font-size: 12px; color: var(--muted); min-width: 120px; }

  .topnote { font-size: 13px; color: var(--muted); margin-top: 8px; }

  @media (max-width: 760px) {
    .id-grid, .rubric, .texts, .score-row { grid-template-columns: 1fr; }
    .col.orig { border-right: none; border-bottom: 1px solid var(--line); }
    .hero h1 { font-size: 24px; }
    .brandbar { flex-wrap: wrap; gap: 12px; }
    .brand-meta { text-align: left; }
    .footer-inner { flex-wrap: wrap; }
  }
  @media print {
    .footer, .opts label:hover { display: none; }
    .item, .card { box-shadow: none; break-inside: avoid; }
  }
</style>
</head>
<body>

<header class="hero">
  <div class="hero-inner">
    <div class="brandbar">
      <div class="brand">
        <svg class="mayo-mark" viewBox="0 0 62 29" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
          <path d="M0 6 C0 3.7 1.6 2.5 4 2.5 H14 C16.4 2.5 18 3.7 18 6 V14 C18 19.6 12.2 23.8 9 26 C5.8 23.8 0 19.6 0 14 Z" fill="#ffffff"/>
          <path d="M22 6 C22 3.7 23.6 2.5 26 2.5 H36 C38.4 2.5 40 3.7 40 6 V14 C40 19.6 34.2 23.8 31 26 C27.8 23.8 22 19.6 22 14 Z" fill="#ffffff"/>
          <path d="M44 6 C44 3.7 45.6 2.5 48 2.5 H58 C60.4 2.5 62 3.7 62 6 V14 C62 19.6 56.2 23.8 53 26 C49.8 23.8 44 19.6 44 14 Z" fill="#ffffff"/>
        </svg>
        <span class="wordmark">MAYO CLINIC</span>
      </div>
      <div class="brand-meta">
        <span class="bm-label">Subspecialist reviewer</span>
        <span class="bm-name">Dr. Muhammad Naeem</span>
      </div>
    </div>
    <p class="eyebrow">Cardiac CT Patient-Education Readability Study · Aim 3__PART_EYEBROW__</p>
    <h1>Clinical Accuracy Scoring of AI-Rewritten Patient Pages</h1>
    <p>Three frontier AI models rewrote 26 online patient-education pages (coronary CTA, TAVR, LAAO/Watchman) to a 6th-grade reading level. Your job is the clinical question: <strong>when the AI made the page easier to read, did it keep the medicine correct and complete?</strong></p>
    <p class="lead">Score each rewrite against its own original on three 1&ndash;5 scales. You are blinded to which AI wrote it &mdash; that is by design.</p>
    __PART_BANNER__
  </div>
</header>

<div class="wrap">

  <!-- Reviewer identity -->
  <section class="card">
    <h2><span class="num">1</span> Your details</h2>
    <div class="id-grid">
      <div class="field">
        <label for="rev-name">Full name</label>
        <input id="rev-name" type="text" placeholder="e.g. Dr. Jane Smith" autocomplete="off">
      </div>
      <div class="field">
        <label for="rev-role">Role / specialty</label>
        <input id="rev-role" type="text" placeholder="e.g. Cardiothoracic radiologist" autocomplete="off">
      </div>
      <div class="field">
        <label for="rev-date">Date</label>
        <input id="rev-date" type="date">
      </div>
    </div>
    <p class="topnote">Your name is saved only on this device and written into the CSV you download. Nothing is uploaded anywhere.</p>
  </section>

  <!-- Instructions + rubric -->
  <section class="card">
    <h2><span class="num">2</span> How to score</h2>
    <ul class="rules">
      <li>Read the <strong>original</strong> (left) and the <strong>AI rewrite</strong> (right) for each item.</li>
      <li>Score the rewrite on all three dimensions below using whole numbers 1&ndash;5.</li>
      <li>Judge <strong>medical content only</strong> &mdash; not tone, not style, not reading level. Style concerns go in the notes box, never in the numbers.</li>
      <li>Score each rewrite against its <strong>own original only</strong>; do not compare rewrites to one another.</li>
      <li>The items are in a fixed randomized order so the models are interleaved &mdash; do not try to guess which AI wrote a passage.</li>
    </ul>

    <div class="rubric" style="margin-top:18px;">
      <div class="dim">
        <span class="tag">Higher is better</span>
        <h3>Accuracy</h3>
        <div class="q">Are all medical statements in the rewrite correct?</div>
        <ul class="anchors">
          <li><span class="s">5</span> Every statement accurate; no clinical misstatements.</li>
          <li><span class="s">4</span> One minor inaccuracy; no change to understanding.</li>
          <li><span class="s">3</span> One moderate inaccuracy; could confuse, not harm.</li>
          <li><span class="s">2</span> Multiple inaccuracies, or one that could drive a wrong decision.</li>
          <li><span class="s">1</span> Major inaccuracies likely to cause harm or refusal of care.</li>
        </ul>
      </div>

      <div class="dim">
        <span class="tag">Higher is better</span>
        <h3>Completeness</h3>
        <div class="q">Did the rewrite keep the key prep, risk, and safety points?</div>
        <ul class="anchors">
          <li><span class="s">5</span> All key prep / risk / safety points present.</li>
          <li><span class="s">4</span> All major points present; one minor point dropped.</li>
          <li><span class="s">3</span> One major point (prep step or risk) dropped.</li>
          <li><span class="s">2</span> Multiple major points dropped; materially less informative.</li>
          <li><span class="s">1</span> Omits most prep / risk / safety information.</li>
        </ul>
      </div>

      <div class="dim reverse">
        <span class="tag">Higher is worse &middot; reverse-coded</span>
        <h3>Added errors</h3>
        <div class="q">Did the rewrite invent claims not in the original?</div>
        <ul class="anchors">
          <li><span class="s">1</span> Nothing invented; only original content.</li>
          <li><span class="s">2</span> One trivial added claim (e.g. wellness platitude).</li>
          <li><span class="s">3</span> One non-trivial added medical claim.</li>
          <li><span class="s">4</span> Multiple added claims, or one clearly wrong invented claim.</li>
          <li><span class="s">5</span> Substantial fabricated medical content (hallucination).</li>
        </ul>
      </div>
    </div>

    <div class="callout warn">
      <strong>Please add a note</strong> whenever you score <strong>&le; 3 on Accuracy or Completeness</strong>, or <strong>&ge; 3 on Added errors</strong>. One line naming the specific problem (e.g. &ldquo;says contrast is iodine-free &mdash; wrong&rdquo; or &ldquo;dropped the 45-day anticoagulation instruction&rdquo;). These notes become the qualitative backbone of the paper.
    </div>
    <div class="callout">
      <strong>Blinding:</strong> the <code>blind&nbsp;ID</code> on each card does not encode the model. Please do not seek out the answer key or any automated scores until after you submit &mdash; they would anchor your judgment.
    </div>
  </section>

  <!-- Items -->
  <section class="card" style="background:transparent;border:none;box-shadow:none;padding:0;">
    <h2 style="padding-left:4px;"><span class="num">3</span> Score the rewrites (<span id="total-count">__N_ITEMS__</span> items)</h2>
    <div id="items"></div>
  </section>

</div>

<!-- Sticky footer -->
<div class="footer">
  <div class="footer-inner">
    <div class="progress">
      <div class="meta"><span>Progress</span><span><b id="done-n">0</b> of <b id="total-n">__N_ITEMS__</b> fully scored</span></div>
      <div class="bar"><span id="bar-fill"></span></div>
    </div>
    <span class="saved-tag" id="saved-tag">Not saved yet</span>
    <button class="btn ghost" id="btn-save">Save draft</button>
    <button class="btn primary" id="btn-export">Download my responses (CSV)</button>
  </div>
</div>

<script>
const ITEMS = /*__ITEMS__*/;
const DIMS = ["accuracy_1_5", "completeness_1_5", "added_errors_1_5"];
const DIM_META = [
  { key: "accuracy_1_5",     label: "Accuracy",     sub: "Are all medical statements in the rewrite correct?", dir: "higher = better", reverse: false },
  { key: "completeness_1_5", label: "Completeness", sub: "Did it keep the key prep, risk & safety points?",     dir: "higher = better", reverse: false },
  { key: "added_errors_1_5", label: "Added errors", sub: "Did it invent claims not in the original?",           dir: "higher = worse",  reverse: true },
];
const STORE_KEY = "__STORE_KEY__";
const FILE_SUFFIX = "__CSV_SUFFIX__";

function esc(s){ const d=document.createElement("div"); d.textContent=s; return d.innerHTML; }

// ---- Render item cards ----
const itemsEl = document.getElementById("items");
ITEMS.forEach((it, i) => {
  const card = document.createElement("div");
  card.className = "item";
  card.id = "item-" + it.blind_id;
  card.dataset.bid = it.blind_id;

  const scorers = DIM_META.map(d => {
    const opts = [1,2,3,4,5].map(v =>
      `<input type="radio" id="${d.key}_${it.blind_id}_${v}" name="${d.key}_${it.blind_id}" value="${v}">`
      + `<label for="${d.key}_${it.blind_id}_${v}">${v}</label>`
    ).join("");
    return `<div class="scorer" data-dim="${d.key}">
        <div class="scorer-head">
          <span class="dim-dot"></span>
          <span class="dim-name">${d.label}</span>
          <span class="dim-dir">${d.dir}</span>
        </div>
        <div class="dim-sub">${d.sub}</div>
        <div class="opts">${opts}</div>
      </div>`;
  }).join("");

  card.innerHTML = `
    <div class="item-head">
      <div class="left">
        <span class="seq">${i+1}.</span>
        <span class="badge">${esc(it.blind_id)}</span>
      </div>
      <div class="right">
        <button type="button" class="expand-btn">⤢ Expand passages</button>
        <span class="done-pill">✓ Scored</span>
      </div>
    </div>
    <div class="texts">
      <div class="col orig">
        <h4><span class="dot"></span> Original page</h4>
        <div class="text">${esc(it.original_text)}</div>
        <div class="fade"></div>
      </div>
      <div class="col rewrite">
        <h4><span class="dot"></span> AI rewrite — score this</h4>
        <div class="text">${esc(it.rewrite_text)}</div>
        <div class="fade"></div>
      </div>
    </div>
    <div class="score-zone">
      <p class="score-title">Your scores for this rewrite</p>
      <div class="score-row">${scorers}</div>
      <div class="notes-wrap">
        <label>Notes <span class="hint">required when a score is flagged below</span></label>
        <textarea data-notes="${esc(it.blind_id)}" placeholder="What specifically was wrong? (one line)"></textarea>
        <div class="flag-note">⚠ A flagged score (Accuracy/Completeness ≤ 3, or Added errors ≥ 3) — please add a one-line note.</div>
      </div>
    </div>`;
  itemsEl.appendChild(card);
});

// ---- State helpers ----
function getVal(bid, dim){
  const el = document.querySelector(`input[name="${dim}_${bid}"]:checked`);
  return el ? parseInt(el.value, 10) : null;
}
function itemComplete(bid){
  return DIMS.every(d => getVal(bid, d) !== null);
}
function itemFlagged(bid){
  const a = getVal(bid, "accuracy_1_5");
  const c = getVal(bid, "completeness_1_5");
  const e = getVal(bid, "added_errors_1_5");
  return (a!==null && a<=3) || (c!==null && c<=3) || (e!==null && e>=3);
}

// ---- Progress + per-card state ----
function refresh(){
  let done = 0;
  ITEMS.forEach(it => {
    const card = document.getElementById("item-" + it.blind_id);
    const complete = itemComplete(it.blind_id);
    card.classList.toggle("complete", complete);
    if (complete) done++;
    const nw = card.querySelector(".notes-wrap");
    nw.classList.toggle("flag", itemFlagged(it.blind_id));
  });
  const total = ITEMS.length;
  document.getElementById("done-n").textContent = done;
  document.getElementById("bar-fill").style.width = (100*done/total) + "%";
}

// ---- Persistence (localStorage) ----
function collect(){
  return {
    reviewer: {
      name: document.getElementById("rev-name").value,
      role: document.getElementById("rev-role").value,
      date: document.getElementById("rev-date").value,
    },
    scores: ITEMS.map(it => ({
      blind_id: it.blind_id,
      accuracy_1_5: getVal(it.blind_id, "accuracy_1_5"),
      completeness_1_5: getVal(it.blind_id, "completeness_1_5"),
      added_errors_1_5: getVal(it.blind_id, "added_errors_1_5"),
      notes: (document.querySelector(`textarea[data-notes="${it.blind_id}"]`).value || "").trim(),
    })),
  };
}
function save(silent){
  try {
    localStorage.setItem(STORE_KEY, JSON.stringify(collect()));
    const t = document.getElementById("saved-tag");
    const now = new Date();
    t.textContent = "Saved " + now.toLocaleTimeString();
  } catch(e){ /* storage may be disabled; export still works */ }
}
function restore(){
  let data;
  try { data = JSON.parse(localStorage.getItem(STORE_KEY)); } catch(e){ return; }
  if (!data) return;
  if (data.reviewer){
    document.getElementById("rev-name").value = data.reviewer.name || "";
    document.getElementById("rev-role").value = data.reviewer.role || "";
    document.getElementById("rev-date").value = data.reviewer.date || "";
  }
  (data.scores || []).forEach(s => {
    DIMS.forEach(d => {
      if (s[d]){
        const el = document.querySelector(`input[name="${d}_${s.blind_id}"][value="${s[d]}"]`);
        if (el) el.checked = true;
      }
    });
    const ta = document.querySelector(`textarea[data-notes="${s.blind_id}"]`);
    if (ta && s.notes) ta.value = s.notes;
  });
}

// ---- CSV export ----
function csvCell(v){
  v = (v === null || v === undefined) ? "" : String(v);
  if (/[",\n]/.test(v)) v = '"' + v.replace(/"/g, '""') + '"';
  return v;
}
function exportCSV(){
  const data = collect();
  const name = data.reviewer.name.trim();
  if (!name){
    alert("Please enter your name at the top before downloading.");
    document.getElementById("rev-name").focus();
    return;
  }
  const incomplete = data.scores.filter(s => !(s.accuracy_1_5 && s.completeness_1_5 && s.added_errors_1_5));
  if (incomplete.length){
    const ok = confirm(incomplete.length + " of " + data.scores.length +
      " items are not fully scored. Download anyway?\n\n(You can come back, your draft is saved on this device.)");
    if (!ok) return;
  }
  // Flagged-without-note warning
  const missingNotes = data.scores.filter(s => {
    const flagged = (s.accuracy_1_5 && s.accuracy_1_5<=3) || (s.completeness_1_5 && s.completeness_1_5<=3) || (s.added_errors_1_5 && s.added_errors_1_5>=3);
    return flagged && !s.notes;
  });
  if (missingNotes.length){
    const ok = confirm(missingNotes.length + " flagged item(s) have no note. A one-line note helps the manuscript. Download anyway?");
    if (!ok) return;
  }

  const header = ["reviewer_name","reviewer_role","review_date","blind_id","accuracy_1_5","completeness_1_5","added_errors_1_5","notes"];
  const rows = [header.join(",")];
  data.scores.forEach(s => {
    rows.push([
      csvCell(name), csvCell(data.reviewer.role), csvCell(data.reviewer.date),
      csvCell(s.blind_id), csvCell(s.accuracy_1_5), csvCell(s.completeness_1_5),
      csvCell(s.added_errors_1_5), csvCell(s.notes),
    ].join(","));
  });
  const blob = new Blob([rows.join("\n")], {type: "text/csv;charset=utf-8"});
  const slug = name.toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_|_$/g, "") || "reviewer";
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "aim3_scores" + FILE_SUFFIX + "_" + slug + ".csv";
  document.body.appendChild(a); a.click(); a.remove();
  save(true);
}

// ---- Wire up ----
document.addEventListener("change", e => {
  if (e.target.matches('input[type="radio"], #rev-name, #rev-role, #rev-date')){ refresh(); save(true); }
});
document.addEventListener("input", e => {
  if (e.target.matches("textarea[data-notes]")){ save(true); }
});
document.getElementById("btn-save").addEventListener("click", () => save(false));
document.getElementById("btn-export").addEventListener("click", exportCSV);
window.addEventListener("beforeunload", () => save(true));

// ---- Expand / collapse the passages for an item ----
document.addEventListener("click", e => {
  const btn = e.target.closest(".expand-btn");
  if (!btn) return;
  const card = btn.closest(".item");
  const expanded = card.classList.toggle("expanded");
  btn.textContent = expanded ? "⤡ Collapse passages" : "⤢ Expand passages";
});

// ---- Flag passages that overflow so the "more below" fade only shows when needed ----
function markOverflow(){
  document.querySelectorAll(".item:not(.expanded) .col").forEach(col => {
    const t = col.querySelector(".text");
    col.classList.toggle("has-overflow", t.scrollHeight - t.clientHeight > 4);
  });
}
window.addEventListener("resize", markOverflow);

// default date = today, then restore any saved draft (restore wins if present)
(function(){
  const d = new Date();
  const iso = d.getFullYear() + "-" + String(d.getMonth()+1).padStart(2,"0") + "-" + String(d.getDate()).padStart(2,"0");
  document.getElementById("rev-date").value = iso;
})();
restore();
refresh();
markOverflow();
</script>
</body>
</html>
"""


if __name__ == "__main__":
    sys.exit(main())
