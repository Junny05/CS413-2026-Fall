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
- Read every requirement against the brief; confirm each traceability entry. -->
- Check the proposed numbers (A6, A10, QR-01, QR-03, QR-04) are ones you can defend. -->
- Confirm the question list is what *you* would ask; record any real answers
       from the instructor in §4 of REQUIREMENTS.md and update the assumptions. -->
- Note anything you changed, added, or removed after reading the AI draft. -->
