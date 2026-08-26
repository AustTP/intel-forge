# Triage Rubric (EXAMPLE)

> Copy this to `config/triage_rubric.md` and rewrite it for your domain.
> This is the single most important file to customize: it defines what your
> intelligence system considers good enough to keep. The judge reads this
> verbatim. Be concrete: vague rubrics produce vague verdicts.

## What is being judged

Describe the candidate the gate receives. One per evaluation. For example: a
proposed skill file, a synthesized finding, a draft brief, a corpus item you're
deciding whether to promote. Replace this paragraph with your own.

## Must-pass criteria

The candidate is REJECTED if it fails any of these. Rewrite for your domain.

1. **Grounded.** Every claim traces to something concrete: a source in the
   corpus, a citation, or a reproducible observation; not assertion or vibes.
2. **Specific.** It says something precise and actionable, not a generic
   summary that could apply to anything in the domain.
3. **Correct.** Nothing in it is factually wrong or internally contradictory.
4. **Self-contained.** A competent practitioner could act on it without needing
   context that isn't present.
5. **Non-duplicative.** It isn't already covered by existing material (note the
   overlap if it is).

## Quality signals (for grading, not gating)

Use these to choose between ACCEPT and REVISE, and to write useful fix notes:

- Is it current, or does it rest on facts that may have gone stale?
- Is the scope right: neither a trivial fragment nor an unfocused dump?
- Would following it actually produce the intended result?

## How to rule

- **ACCEPT**: passes every must-pass criterion and the quality signals are
  solid.
- **REVISE**: the core is sound but at least one fixable problem exists; list
  the specific fixes and don't be vague.
- **REJECT**: fails any must-pass criterion or is unsalvageable.
- **ESCALATE**: the candidate sits in a genuine grey area or you can't assess
  it confidently from what's provided; say what additional context a human
  would need.

## Notes to the judge

- Be strict. A gate that accepts everything is worthless. When torn between
  ACCEPT and REVISE, choose REVISE; between REVISE and REJECT, choose REJECT.
- Judge only what's in front of you. Don't assume unstated context makes it
  better than it reads.
- Give per-criterion reasoning so the verdict is auditable.
