#!/usr/bin/env python3
"""
ingest.py — run configured sources and write new items into the corpus.

  python3 -m pipeline.ingest                      # all sources, full backfill
  python3 -m pipeline.ingest --since 2026-01-01   # only items on/after a date
  python3 -m pipeline.ingest --sources acme-blog  # named sources only
  python3 -m pipeline.ingest --dry-run            # show what would be written

Flow:  sources.yaml -> adapter.fetch() -> relevance filter -> dedup -> corpus/*.md

The relevance filter here is a CHEAP, ingest-time keyword gate (config/relevance.yaml)
whose only job is to keep obvious noise out of the corpus. It is NOT the quality
judge — that's the triage gate (pipeline/triage.py), which runs later against a
rubric. Keep this filter loose; let triage be the strict one.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

from pipeline.core import (
    RateLimiter, RobotsCache, Item, already_have, write_item, is_relevant,
)
from pipeline import sources as source_registry

CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"


def load_yaml(path: Path) -> dict:
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def main() -> None:
    ap = argparse.ArgumentParser(description="Ingest sources into the corpus.")
    ap.add_argument("--since", help="ISO date lower bound, e.g. 2026-01-01")
    ap.add_argument("--sources", help="comma-separated source names to run (default: all)")
    ap.add_argument("--dry-run", action="store_true", help="don't write files")
    ap.add_argument("--config", default=str(CONFIG_DIR / "sources.yaml"),
                    help="path to sources config (default: config/sources.yaml)")
    ap.add_argument("--relevance", default=str(CONFIG_DIR / "relevance.yaml"),
                    help="path to relevance config (default: config/relevance.yaml)")
    args = ap.parse_args()

    sources_cfg = load_yaml(Path(args.config))
    if not sources_cfg.get("sources"):
        sys.exit(
            f"No sources found in {args.config}.\n"
            f"Copy config/sources.example.yaml to config/sources.yaml and edit it."
        )

    rel_cfg = load_yaml(Path(args.relevance))
    include = rel_cfg.get("include", [])
    exclude = rel_cfg.get("exclude", [])

    wanted = None
    if args.sources:
        wanted = {s.strip() for s in args.sources.split(",")}

    global_rate = float(sources_cfg.get("rate_limit", 1.0))
    rl = RateLimiter(default_delay=global_rate)
    robots = RobotsCache()

    total_new = 0
    total_seen = 0
    total_filtered = 0

    for entry in sources_cfg["sources"]:
        name = entry.get("name", "?")
        if wanted and name not in wanted:
            continue
        stype = entry.get("type")
        try:
            adapter = source_registry.build(stype, rl, robots, entry)
        except KeyError as e:
            print(f"[skip] {name}: {e}")
            continue

        print(f"[*] {name} ({stype})")
        try:
            for item in adapter.fetch(since=args.since):
                total_seen += 1
                blob = f"{item.title}\n{item.content_md}"
                if not is_relevant(blob, include, exclude):
                    total_filtered += 1
                    continue
                if already_have(item):
                    continue
                path = write_item(item, dry_run=args.dry_run)
                total_new += 1
                if path:
                    print(f"    + {path.name}")
        except Exception as e:  # noqa: BLE001
            print(f"    [WARN] {name} failed: {e}")

    print(
        f"\nDone. seen={total_seen} filtered_out={total_filtered} "
        f"new={total_new}{' (dry-run)' if args.dry_run else ''}"
    )


if __name__ == "__main__":
    main()
