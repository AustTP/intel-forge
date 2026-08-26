# Configuring the triage gate

The triage gate is a rubric-driven LLM-as-judge. It takes a candidate, evaluates
it against your rubric, and returns a structured verdict with per-criterion
reasoning. Three things are yours to configure: the **rubric** (what "good"
means), the **verdicts** (the possible outcomes), and the **judge** (which model
does the evaluating).

## 1. The rubric — the important one

`config/triage_rubric.md` is read verbatim by the judge. This is where your
domain lives. A vague rubric produces vague verdicts, so be concrete:

- State exactly what the candidate is.
- List **must-pass criteria** — failing any means REJECT.
- List **quality signals** — used to grade ACCEPT vs REVISE and to write fix
  notes.
- Tell the judge how to rule, and to be strict.

Start from `config/triage_rubric.example.md` and rewrite every section for your
subject. This file, more than any code, determines how good your gate is.

## 2. The verdicts

`config/triage.yaml` lists the verdicts the judge may return. The defaults —
ACCEPT / REVISE / REJECT / ESCALATE — suit most uses, but rename or extend them
(e.g. add `PROMOTE` vs `KEEP`, or a severity ladder). Each verdict has a name, a
meaning shown to the judge, and an action documenting what your pipeline does
with it.

The CLI exits `0` only on `ACCEPT` (else `2`), so the gate composes in shell
pipelines and CI. If you rename ACCEPT, adjust that check in `pipeline/triage.py`.

## 3. The judge — any model

The reference judge uses the Anthropic API and needs `ANTHROPIC_API_KEY` plus
`pip install anthropic`. But the gate only needs a function that takes a prompt
string and returns a string, so any provider works. To swap it:

```python
from pipeline.triage import triage, load_config, TriageConfig
from pathlib import Path

def my_judge(prompt: str, cfg: TriageConfig) -> str:
    # call OpenAI, a local model, Bedrock, whatever — return the raw text
    return my_model.complete(prompt)

cfg = load_config(Path("config/triage.yaml"), Path("config/triage_rubric.md"))
verdict = triage(candidate_text, cfg, judge=my_judge)
```

## Trying it without a model

To see exactly what the judge will be asked — and wire up your own model —
print the assembled prompt instead of calling anything:

```bash
python3 -m pipeline.triage --input candidate.md --print-prompt
```

## Where the gate fits

Run it wherever you promote candidates:

- **Before adding a skill** to the library (see `docs/WRITING_A_SKILL.md`).
- **On synthesized findings/outputs** before you act on or ship them.
- **In CI**, gating merges to `skills/` on the exit code.
- **In the refresh**, if you want re-verification of flagged-stale skills to be
  automatic rather than manual.

Keep it strict. The relevance filter at ingest is the loose gate; triage is the
one that protects the quality of what you keep.
