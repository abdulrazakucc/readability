#!/usr/bin/env python3
"""Attach Word comments to the manuscript for decisions the authors must make.

A tracked change says "this text was altered". A comment says "here is why, and
here is the choice you still have". Where an edit was a judgement call -- most
often because completing it properly needs a source I cannot verify -- the reason
belongs in a comment anchored to the exact sentence, not buried in a commit message
or a separate CSV.

python-docx has no comment API, so the OPC parts are written directly:

  * `word/comments.xml`                 the comment bodies
  * `[Content_Types].xml`               an Override so Word knows the part's type
  * `word/_rels/document.xml.rels`      a relationship from the document to it
  * `w:commentRangeStart` / `End` / `w:commentReference` in `word/document.xml`
    to anchor each comment to a span of text

Comments are additive and idempotent: an anchor is only inserted if the target
sentence is not already commented, so re-running does not duplicate them.
"""

from __future__ import annotations

import re
import shutil
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import docx
from docx.oxml.ns import qn

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

MANUSCRIPT = REPO_ROOT / "publication" / "Naeem_final_clean_cardiac_CT_readability.docx"
BACKUP_DIR = REPO_ROOT / "private" / "manuscript_backups"
# Comments carry the author's name so the co-author knows who raised the question.
AUTHOR = "Abdul Razak"
INITIALS = "AR"

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = f'xmlns:w="{W}"'


# Each entry anchors on a distinctive phrase in the sentence it concerns.
COMMENTS: list[dict] = [
    {
        "anchor": "Health-literacy guidance commonly recommends",
        "text": (
            "SUGGESTION - please confirm. This sentence originally attributed the 6th-grade "
            "recommendation to the National Library of Medicine, the American Medical Association "
            "and the CDC, citing reference 3 (Kutner et al., National Assessment of Adult "
            "Literacy). That reference is a literacy survey: it supports the statistic that about "
            "one third of US adults read at or below that level, but it contains no recommendation "
            "from any of those three bodies, so the attribution was not supported by the source "
            "cited. It has been softened to \"health-literacy guidance commonly recommends\", "
            "which reference 3 does support. If you prefer to keep the named attribution - it is a "
            "stronger opening - please supply the specific NLM, AMA and CDC guidance documents and "
            "they will be cited here. These were deliberately not generated, because an unverified "
            "citation is a worse problem than a softer sentence."
        ),
    },
    {
        "anchor": "Recent reports have evaluated the readability of LLM-generated answers",
        "text": (
            "SUGGESTION - please confirm. References 7 and 8 were previously cited together for "
            "\"readability of LLM-generated answers to cardiology patient questions\". Reference 7 "
            "(Behers et al.) is exactly that. Reference 8 (Ayers et al.) compared physician and "
            "chatbot responses to general patient questions on a public social-media forum, so it "
            "is neither cardiology-specific nor a readability study. The sentence now makes two "
            "claims, each carrying only the citation that supports it. Reference 8 was kept rather "
            "than deleted so it does not become an uncited entry in the reference list. If you "
            "would rather drop Ayers from the Introduction entirely, it should also be removed "
            "from the reference list and the remaining references renumbered."
        ),
    },
]


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _para_text(para) -> str:
    """Paragraph text with tracked changes accepted, so revised sentences are found."""
    return "".join(n.text for n in para._element.iter()
                   if n.tag == f"{{{W}}}t" and n.text)


def anchor_comments(document, comments: list[dict]) -> list[dict]:
    """Insert range markers around each target paragraph. Returns those applied."""
    applied = []
    for idx, spec in enumerate(comments):
        target = next((p for p in document.paragraphs
                       if spec["anchor"] in _para_text(p)), None)
        if target is None:
            applied.append({**spec, "status": "ANCHOR NOT FOUND"})
            continue
        if target._element.find(qn("w:commentRangeStart")) is not None:
            applied.append({**spec, "status": "ALREADY COMMENTED"})
            continue

        cid = str(idx)
        start = docx.oxml.OxmlElement("w:commentRangeStart")
        start.set(qn("w:id"), cid)
        target._element.insert(0, start)

        end = docx.oxml.OxmlElement("w:commentRangeEnd")
        end.set(qn("w:id"), cid)
        target._element.append(end)

        run = docx.oxml.OxmlElement("w:r")
        ref = docx.oxml.OxmlElement("w:commentReference")
        ref.set(qn("w:id"), cid)
        run.append(ref)
        target._element.append(run)

        applied.append({**spec, "status": "APPLIED", "id": cid})
    return applied


def _comments_xml(applied: list[dict]) -> str:
    body = []
    for spec in applied:
        if spec.get("status") != "APPLIED":
            continue
        text = (spec["text"].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))
        body.append(
            f'<w:comment w:id="{spec["id"]}" w:author="{AUTHOR}" '
            f'w:initials="{INITIALS}" w:date="{_stamp()}">'
            f'<w:p><w:r><w:t xml:space="preserve">{text}</w:t></w:r></w:p>'
            f"</w:comment>"
        )
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f"<w:comments {NS}>" + "".join(body) + "</w:comments>"
    )


def write_comments_part(path: Path, applied: list[dict]) -> None:
    """Add comments.xml plus its content-type override and relationship."""
    CT = "application/vnd.openxmlformats-officedocument.wordprocessingml.comments+xml"
    REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/comments"

    with zipfile.ZipFile(path) as zin:
        items = {n: zin.read(n) for n in zin.namelist()}

    ct = items["[Content_Types].xml"].decode("utf-8")
    if "comments+xml" not in ct:
        ct = ct.replace("</Types>",
                        f'<Override PartName="/word/comments.xml" ContentType="{CT}"/></Types>')
    items["[Content_Types].xml"] = ct.encode("utf-8")

    rels_name = "word/_rels/document.xml.rels"
    rels = items[rels_name].decode("utf-8")
    if "comments.xml" not in rels:
        existing = [int(m) for m in re.findall(r'Id="rId(\d+)"', rels)]
        rid = f"rId{max(existing) + 1 if existing else 1}"
        rels = rels.replace(
            "</Relationships>",
            f'<Relationship Id="{rid}" Type="{REL}" Target="comments.xml"/></Relationships>')
    items[rels_name] = rels.encode("utf-8")

    items["word/comments.xml"] = _comments_xml(applied).encode("utf-8")

    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zout:
        for name, data in items.items():
            zout.writestr(name, data)


def main() -> int:
    if not MANUSCRIPT.exists():
        print(f"manuscript not found: {MANUSCRIPT}")
        return 2

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    backup = BACKUP_DIR / f"{MANUSCRIPT.stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx"
    shutil.copy2(MANUSCRIPT, backup)

    document = docx.Document(str(MANUSCRIPT))
    applied = anchor_comments(document, COMMENTS)
    document.save(str(MANUSCRIPT))

    if any(a.get("status") == "APPLIED" for a in applied):
        write_comments_part(MANUSCRIPT, applied)

    print("=" * 78)
    print("REVIEW COMMENTS ADDED")
    print("=" * 78)
    print(f"  file   : {MANUSCRIPT.name}")
    print(f"  backup : {backup.relative_to(REPO_ROOT)}\n")
    for a in applied:
        print(f"  [{a['status']}] {a['anchor'][:58]}")
    print("\n  In Word: Review > Show Comments.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
