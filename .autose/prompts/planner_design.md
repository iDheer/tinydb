## Your stage: 2, Design (planner, design session)

Plan the change that satisfies `spec.md`. Read `ARCHITECTURE.md` in the repository root
first: it describes the components, three architecture decisions and five constraints
(C1–C5) of tinydb. Then read the code you intend to change.

Your design must:
- name every file to change (`modify`) or add (`create`), and in each Python file every
  function, class or method you will change or add. Use `Class.method` for methods.
  Names marked `modify` must exist in the file today; the orchestrator checks this with
  the AST. Do not list test files; a separate tester writes
  `tests/test_autose_issue_<N>.py`.
- map every acceptance criterion id to the symbols that implement it and a one-line
  idea for its test;
- state how each relevant ARCHITECTURE.md constraint is respected (e.g. a new query
  operation must encode all its parameters in its hash, C2; no third-party dependency, C5);
- prefer the smallest change that fits the existing design; list the alternatives you
  rejected and why.

Do not write code. If the spec itself looks wrong, say so in `risks`.
