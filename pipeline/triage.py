#!/usr/bin/env python3
"""
triage.py — the triage gate. A rubric-driven, LLM-as-judge quality filter.

This is the strict gate. Where the ingest relevance filter only keeps obvious
noise out of the corpus, the triage gate evaluates a *candidate* — a proposed
skill, a synthesized finding, a draft output, a corpus item you're deciding
whether to promote — against an explicit rubric, and returns a structured
verdict WITH reasoning. Every decision is auditable: you can see why the judge
ruled the way it did, per criterion.

Nothing here is domain-specific. What "good" means lives entirely in your
rubric (config/triage_rubric.md) and the verdicts you allow
(config/triage.yaml). Swap the rubric and the same machine grades an entirely
different subject without a line of code changing — it never knows or cares
what the domain is.

  # Evaluate a candidate file against the configured rubric:
  python3 -m pipeline.triage --input candidate.md

  # Evaluate stdin:
  cat candidate.md | python3 -m pipeline.triage

  # Just print the assembled judge prompt and exit (wire up your own model):
  python3 -m pipeline.triage --input candidate.md --print-prompt

By default it looks for a judge via ANTHROPIC_API_KEY (reference adapter). Any
provider works — see `Judge` below and docs/CONFIGURING_TRIAGE.md.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

import yaml

CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

@dataclass
class TriageConfig:
    rubric_md: str
    verdicts: list[dict]          # [{name, meaning, action}]
    model: str
    max_tokens: int

    @property
    def verdict_names(self) -> list[str]:
        return [v["name"] for v in self.verdicts]


def load_config(cfg_path: Path, rubric_path: Path) -> TriageConfig:
    cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) if cfg_path.exists() else {}
    if not rubric_path.exists():
        sys.exit(
            f"No rubric at {rubric_path}.\n"
            f"Copy config/triage_rubric.example.md to config/triage_rubric.md and edit it."
        )
    return TriageConfig(
        rubric_md=rubric_path.read_text(encoding="utf-8"),
        verdicts=cfg.get("verdicts", _DEFAULT_VERDICTS),
        model=cfg.get("model", "claude-sonnet-4-6"),
        max_tokens=int(cfg.get("max_tokens", 1024)),
    )


# Sensible generic defaults if config/triage.yaml is absent. Override freely.
_DEFAULT_VERDICTS = [
    {"name": "ACCEPT",   "meaning": "Meets the bar as-is.",                 "action": "keep"},
    {"name": "REVISE",   "meaning": "Salvageable but needs specific fixes.", "action": "return with notes"},
    {"name": "REJECT",   "meaning": "Does not meet the bar; discard.",       "action": "drop"},
    {"name": "ESCALATE", "meaning": "Judge is not confident; a human should decide.", "action": "route to human"},
]


# ---------------------------------------------------------------------------
# The judge interface (vendor-neutral)
# ---------------------------------------------------------------------------

# A Judge is any callable: prompt string in, model response string out.
Judge = Callable[[str, TriageConfig], str]


def anthropic_judge(prompt: str, cfg: TriageConfig) -> str:
    """Reference adapter using the Anthropic API. Optional dependency.

    Replace this with OpenAI, a local model, Bedrock, etc. — the gate only
    needs a string back. See docs/CONFIGURING_TRIAGE.md for a swap example.
    """
    try:
        import anthropic
    except ImportError:
        sys.exit("anthropic not installed. `pip install anthropic`, or plug in your own judge.")
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        sys.exit("ANTHROPIC_API_KEY not set. Set it, or plug in your own judge function.")
    client = anthropic.Anthropic(api_key=key)
    resp = client.messages.create(
        model=cfg.model,
        max_tokens=cfg.max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(block.text for block in resp.content if getattr(block, "type", "") == "text")


# ---------------------------------------------------------------------------
# Prompt assembly + verdict parsing
# ---------------------------------------------------------------------------

def build_prompt(candidate: str, cfg: TriageConfig) -> str:
    verdict_lines = "\n".join(
        f'  - {v["name"]}: {v["meaning"]}' for v in cfg.verdicts
    )
    schema = {
        "verdict": "<one of: " + ", ".join(cfg.verdict_names) + ">",
        "rationale": "<2-3 sentence overall justification>",
        "criteria": [
            {"criterion": "<name>", "pass": True, "note": "<why>"}
        ],
        "suggested_fixes": ["<only if REVISE; else empty>"],
    }
    return f"""You are a strict triage judge. Evaluate the CANDIDATE below against the
RUBRIC. Be specific and evidence-based. Do not be generous — the point of the
gate is to keep the bar high.

Return ONLY a JSON object, no prose before or after, matching this schema:
{json.dumps(schema, indent=2)}

Allowed verdicts:
{verdict_lines}

=== RUBRIC ===
{cfg.rubric_md}

=== CANDIDATE ===
{candidate}
"""


def parse_verdict(raw: str, cfg: TriageConfig) -> dict:
    """Extract the JSON verdict, tolerating stray text or code fences."""
    text = raw.strip()
    if "```" in text:
        # pull the fenced block if the model wrapped it
        parts = text.split("```")
        for p in parts:
            p = p.strip()
            if p.startswith("json"):
                p = p[4:].strip()
            if p.startswith("{"):
                text = p
                break
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end != -1:
        text = text[start:end + 1]
    try:
        verdict = json.loads(text)
    except json.JSONDecodeError:
        return {"verdict": "ESCALATE", "rationale": "Judge output was not valid JSON.",
                "criteria": [], "suggested_fixes": [], "_raw": raw}
    if verdict.get("verdict") not in cfg.verdict_names:
        verdict.setdefault("_warnings", []).append(
            f"verdict {verdict.get('verdict')!r} not in allowed set {cfg.verdict_names}"
        )
    return verdict


def triage(candidate: str, cfg: TriageConfig, judge: Optional[Judge] = None) -> dict:
    judge = judge or anthropic_judge
    prompt = build_prompt(candidate, cfg)
    raw = judge(prompt, cfg)
    return parse_verdict(raw, cfg)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(description="Rubric-driven triage gate.")
    ap.add_argument("--input", help="candidate file (default: stdin)")
    ap.add_argument("--config", default=str(CONFIG_DIR / "triage.yaml"))
    ap.add_argument("--rubric", default=str(CONFIG_DIR / "triage_rubric.md"))
    ap.add_argument("--print-prompt", action="store_true",
                    help="print the assembled judge prompt and exit (no model call)")
    args = ap.parse_args()

    candidate = Path(args.input).read_text(encoding="utf-8") if args.input else sys.stdin.read()
    if not candidate.strip():
        sys.exit("Empty candidate.")

    cfg = load_config(Path(args.config), Path(args.rubric))

    if args.print_prompt:
        print(build_prompt(candidate, cfg))
        return

    verdict = triage(candidate, cfg)
    print(json.dumps(verdict, indent=2))
    # Exit non-zero on anything that isn't a clean accept, so the gate composes
    # in shell pipelines and CI.
    sys.exit(0 if verdict.get("verdict") == "ACCEPT" else 2)


if __name__ == "__main__":
    main()
