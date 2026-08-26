#!/usr/bin/env python3
"""
skill_freshness.py — flag skill files that haven't been touched or re-validated
in a while, so their claims get periodically re-checked against current reality
instead of quietly rotting.

Knowledge has a shelf life. A skill written against last year's facts, tools, or
best practices can silently go stale. This tool doesn't decide correctness — it
just surfaces the oldest skills so a human (or the triage gate) re-examines them.

Freshness signal is the more recent of:
  1. filesystem mtime of the skill file
  2. the most recent YYYY-MM-DD date found in the file's own text (a dated
     "last reviewed" note is more meaningful than mtime, which resets on copy)

  python3 -m pipeline.skill_freshness                 # default 180-day threshold
  python3 -m pipeline.skill_freshness --threshold 90
  python3 -m pipeline.skill_freshness --skill my-skill.md
"""

from __future__ import annotations

import argparse
import re
from datetime import date, datetime
from pathlib import Path

SKILLS_DIR = Path(__file__).resolve().parent.parent / "skills"
DATE_RE = re.compile(r"20\d{2}-\d{2}-\d{2}")


def _most_recent_internal_date(text: str):
    best = None
    for m in DATE_RE.finditer(text):
        try:
            d = datetime.strptime(m.group(), "%Y-%m-%d").date()
        except ValueError:
            continue
        if d <= date.today() and (best is None or d > best):
            best = d
    return best


def check(threshold_days: int, only_skill: str | None) -> list[dict]:
    results = []
    for sf in sorted(SKILLS_DIR.glob("*.md")):
        if sf.name.startswith("_") or sf.name == "SKILLS_INDEX.md":
            continue  # templates / index aren't skills
        if only_skill and sf.name != only_skill:
            continue
        text = sf.read_text(encoding="utf-8", errors="ignore")
        mtime_date = datetime.fromtimestamp(sf.stat().st_mtime).date()
        internal = _most_recent_internal_date(text)
        most_recent = max(d for d in (mtime_date, internal) if d is not None)
        age = (date.today() - most_recent).days
        results.append({
            "file": sf.name,
            "most_recent_signal": most_recent.isoformat(),
            "age_days": age,
            "stale": age > threshold_days,
        })
    return results


def main() -> None:
    ap = argparse.ArgumentParser(description="Flag stale skills for re-verification.")
    ap.add_argument("--threshold", type=int, default=180, help="age in days (default 180)")
    ap.add_argument("--skill", help="check a single skill file by name")
    args = ap.parse_args()

    rows = check(args.threshold, args.skill)
    if not rows:
        print("No skills found. Add skills to skills/ (see skills/_TEMPLATE.md).")
        return

    rows.sort(key=lambda r: r["age_days"], reverse=True)
    stale = [r for r in rows if r["stale"]]

    print(f"{'AGE':>5}  {'LAST SIGNAL':<12}  FILE")
    for r in rows:
        flag = "  <-- STALE" if r["stale"] else ""
        print(f"{r['age_days']:>5}  {r['most_recent_signal']:<12}  {r['file']}{flag}")

    print(f"\n{len(stale)}/{len(rows)} skills over {args.threshold} days.")


if __name__ == "__main__":
    main()
