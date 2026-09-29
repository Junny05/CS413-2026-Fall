# AI Use Record – Assignment #3

## Tool
Claude Code (model: Claude Opus 5.5)

## Important prompts

1. Pasted the full text of Assignment #3 (tasks 1–5, submission and evaluation rules)
   into Claude Code in the course repository.
2. And asked to do it carefully under the guidelines that I am checking it for every time it does anything.
3. Claude read `assigns/03/LAMBDA-UI-informal-requirements.md` (the stakeholder brief)
   and `assigns/02/MySolution/lambda0.py` (to see how the current interpreter
   represents programs as Python-built ASTs) before drafting.

## Significant suggestions:

- The overall structure of `REQUIREMENTS.md`: stakeholders, system-boundary diagram
  separating the environment from the external compiler, eight clarification questions,
  assumptions A1–A10, 20 functional and 6 quality requirements with MoSCoW priorities,
  a proposed logical compiler interface, 11 acceptance checks (4 failure/exception
  cases), a traceability table, review notes, and an unresolved-issues list.
- Treating all numeric targets (10 s time limit, 0.2 s response, 15-minute setup,
  2-minute first run) as *proposals*, because the brief gives no numbers.
- Stating explicitly that **no stakeholder answers were received**, so that no
  assumption is presented as an instructor decision.
- Adding the verdicts "Could not complete" / "Not run" and the "Out of date" result
  marker to make "one troublesome test" and "which version produced the result"
  testable.

## Corrections made during the session

- The AI's first version of review note 6 described an "early draft" that listed class
  sharing as a Must; that draft never existed, so the note was replaced with a real
  ambiguity it had resolved (the meaning of "change its input", now A3/Q3).

## How I reviewed the output
- Read every requirement against the brief; confirm each traceability entry.
- Checked the proposed numbers (A6, A10, QR-01, QR-03, QR-04)
- Confirmed the question list
- Verified internal consistency: requirement IDs referenced in the traceability
  table, acceptance checks, and review notes all point to requirements that
  actually exist in the document.
- Checked the system-boundary diagram against the brief to confirm nothing was
  drawn as in-scope that the brief assigns to the external compiler, or vice versa.
- Re-read each MoSCoW priority and checked it against what the brief implies
  (nothing marked Must that the brief only mentions in passing).
- Sanity-checked the acceptance checks by mentally running them against the
  current `assigns/02/MySolution/lambda0.py` interpreter, to catch any that
  assume a capability that doesn't exist yet.
- Looked for unsupported claims — statements presented as fact that aren't
  actually backed by the brief or the code (this is what caught the fabricated
  "early draft" in review note 6).
- Confirmed quoted text attributed to the brief actually appears in
  `LAMBDA-UI-informal-requirements.md`.
- Checked that assumptions don't quietly contradict each other (e.g. A3 vs A10
  on the meaning of "input").
- Confirmed the "Out of date" / "Not run" / "Could not complete" verdicts are
  distinct and non-overlapping, so a grader can't hit an ambiguous case.