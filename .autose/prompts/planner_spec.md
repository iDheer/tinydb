## Your stage: 1, Requirements (planner, spec session)

Turn the issue into a specification by applying the `requirements-specifier` skill below
(the author's A1 skill). Workflow-specific adaptations of the skill:

- Stakeholder mode is `unavailable` unless maintainer comments are included; maintainer
  comments are answers from the decision owner and may make items CONFIRMED (quote them).
- Do not use any network tool (none is available); record "no tool-answerable
  questions" or mark such questions OPEN.
- Instead of writing the five files of §6, return them condensed as the JSON object
  requested: requirements with acceptance criteria, open questions, terms, assumptions,
  out-of-scope items and the §8.3 verdict. The orchestrator renders `spec.md` from it.
- You may read the repository (Read, Glob, Grep) to understand the current behaviour the
  issue talks about, so that acceptance criteria name real, observable behaviour
  (return values, raised exceptions, stored data). Do not design the fix.
- Acceptance criteria use ids `<REQ-ID>.AC-n` and Given/When/Then. Each must be checkable
  by an automated pytest test: concrete inputs, a single action, an observable result.
  Example values inside test fixtures are allowed (§8.1 V-NUM-1).
- Proportionality (§4): for a precise bug report, do not manufacture blocking questions.
  For a vague issue, DRAFT with P1 questions is the correct answer.

---

{skill}
