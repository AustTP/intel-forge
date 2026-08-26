#!/usr/bin/env python3
"""
build_index.py: regenerate corpus/INDEX.md, a browsable table of what's ingested.

  python3 -m pipeline.build_index

Reads the metadata block from each corpus/*.md file and writes a single index
grouped by source, newest first. Run it after ingest (the scheduler does this
for you). The index is what a human or an agent seeding skills scans to see
what raw material is available.
"""

from __future__ import annotations

import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from pipeline.core import CORPUS_DIR

_META_RE = re.compile(r"^\|\s*(.+?)\s*\|\s*(.+?)\s*\|$", re.MULTILINE)
_TITLE_RE = re.compile(r"^#\s*(.+)$", re.MULTILINE)


def _meta(text: str) -> dict:
    out = {}
    for k, v in _META_RE.findall(text):
        if k.lower() not in ("field",):  # skip header row
            out[k.strip()] = v.strip()
    return out


def main() -> None:
    files = sorted(CORPUS_DIR.glob("*.md"))
    files = [f for f in files if f.name != "INDEX.md"]

    by_source: dict[str, list[tuple]] = defaultdict(list)
    for f in files:
        text = f.read_text(encoding="utf-8", errors="ignore")
        meta = _meta(text)
        title_m = _TITLE_RE.search(text)
        title = title_m.group(1).strip() if title_m else f.stem
        source = meta.get("Source", "unknown")
        published = meta.get("Published", "")
        url = meta.get("Original URL", "")
        by_source[source].append((published, title, url, f.name))

    lines = [
        "# Corpus Index",
        "",
        f"_Generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')} - "
        f"{len(files)} items across {len(by_source)} sources._",
        "",
    ]
    for source in sorted(by_source):
        rows = sorted(by_source[source], key=lambda r: r[0] or "", reverse=True)
        lines.append(f"## {source} ({len(rows)})")
        lines.append("")
        lines.append("| Published | Title | File |")
        lines.append("|---|---|---|")
        for published, title, url, fname in rows:
            safe_title = title.replace("|", "\\|")
            link = f"[{safe_title}]({url})" if url else safe_title
            lines.append(f"| {published or ''} | {link} | `{fname}` |")
        lines.append("")

    (CORPUS_DIR / "INDEX.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {CORPUS_DIR / 'INDEX.md'} ({len(files)} items).")


if __name__ == "__main__":
    main()
