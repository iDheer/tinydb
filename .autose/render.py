"""Render structured agent output into the Markdown artifacts (ADR-003)."""
from __future__ import annotations

from typing import Any


def _check_block(check: dict[str, Any] | None) -> str:
    if not check:
        return ""
    mark = "PASSED" if check.get("passed") else "FAILED"
    lines = [f"\n## Stage check: {mark}\n"]
    for r in check.get("reasons", []):
        lines.append(f"- {r}")
    return "\n".join(lines) + "\n"


def spec_md(issue: dict[str, Any], spec: dict[str, Any], check: dict[str, Any] | None = None,
            judge: dict[str, Any] | None = None) -> str:
    out = [f"# spec.md: {spec.get('title') or issue.get('title')}\n",
           f"- Issue: #{issue.get('number')} {issue.get('url', '')}",
           f"- Verdict (A1 skill): **{spec.get('verdict')}**, stakeholder mode: unavailable",
           f"\n{spec.get('summary', '')}\n", "## Requirements\n"]
    for r in spec.get("requirements", []):
        out += [f"### {r['id']}: {r['statement']}",
                f"- Kind: {r['kind']} · Priority: {r['priority']} · Status: **{r['status']}**",
                f"- Source: {r['source']} (\"{r['source_quote']}\")"]
        if r.get("links"):
            out.append(f"- Links: {', '.join(r['links'])}")
        out.append("- Acceptance criteria:")
        for ac in r.get("acceptance_criteria", []):
            out.append(f"  - **{ac['id']}**: Given {ac['given']}, when {ac['when']}, then {ac['then']}.")
        out.append("")
    if spec.get("open_questions"):
        out += ["## Open questions\n", "| Q | Priority | Question | Options / default | Blocks |",
                "|---|---|---|---|---|"]
        for q in spec["open_questions"]:
            opts = "; ".join(q.get("options", [])) + (f" (default: {q['proposed_default']})"
                                                     if q.get("proposed_default") else "")
            out.append(f"| {q['id']} | {q['priority']} | {q['question']} | {opts} | "
                       f"{', '.join(q.get('blocks', [])) or 'none yet'} |")
        out.append("")
    if spec.get("terms"):
        out += ["## Terms\n"] + [f"- {t['id']} **{t['term']}**: " + " / ".join(t["interpretations"])
                                 for t in spec["terms"]] + [""]
    if spec.get("assumptions"):
        out += ["## Assumptions\n"] + [f"- {a['id']}: {a['text']} (risk if wrong: {a['risk_if_wrong']})"
                                       for a in spec["assumptions"]] + [""]
    if spec.get("out_of_scope"):
        out += ["## Out of scope\n"] + [f"- {x}" for x in spec["out_of_scope"]] + [""]
    if judge:
        out += ["## Testability judge (Haiku 5.5)\n", "| AC | Testable | Reason |", "|---|---|---|"]
        out += [f"| {c['id']} | {'yes' if c['testable'] else 'no'} | {c['reason']} |"
                for c in judge.get("criteria", [])]
        out.append("")
    return "\n".join(out) + _check_block(check)


def design_md(design: dict[str, Any], check: dict[str, Any] | None = None) -> str:
    out = ["# design.md\n", design.get("summary", ""), "", "## Approach\n", design.get("approach", ""), "",
           "## Files and symbols to change\n", "| File | Change | Symbol | Kind | Symbol change | What |",
           "|---|---|---|---|---|---|"]
    for f in design.get("files", []):
        syms = f.get("symbols") or [{"name": "-", "kind": "-", "change": "-", "description": f["purpose"]}]
        for s in syms:
            out.append(f"| `{f['path']}` | {f['change']} | `{s['name']}` | {s['kind']} | {s['change']} | "
                       f"{s['description']} |")
    out += ["", "## Acceptance criteria → code → test\n", "| AC | Symbols | Test idea |", "|---|---|---|"]
    out += [f"| {m['ac_id']} | {', '.join(m['symbols'])} | {m['test_idea']} |" for m in design.get("ac_mapping", [])]
    if design.get("constraints"):
        out += ["", "## Architecture constraints (ARCHITECTURE.md)\n"]
        out += [f"- {c['id']}: {c['how_respected']}" for c in design["constraints"]]
    if design.get("alternatives"):
        out += ["", "## Alternatives considered\n"]
        out += [f"- {a['option']}: {a['why_not']}" for a in design["alternatives"]]
    if design.get("risks"):
        out += ["", "## Risks\n"] + [f"- {r}" for r in design["risks"]]
    return "\n".join(out) + "\n" + _check_block(check)


def test_report_md(issue_no: int, attempts: list[dict[str, Any]], tester_out: dict[str, Any] | None) -> str:
    out = [f"# test_report.md: issue #{issue_no}\n"]
    for i, a in enumerate(attempts, 1):
        d = a.get("details", {})
        out += [f"## Attempt {i}: {'PASSED' if a.get('passed') else 'FAILED'}\n",
                f"- Full suite: {d.get('suite', {}).get('passed', '?')} passed, "
                f"{d.get('suite', {}).get('failed', '?')} failed, {d.get('suite', {}).get('errors', '?')} errors, "
                f"{d.get('suite', {}).get('skipped', '?')} skipped",
                f"- New tests ({d.get('test_file', '')}): {len(d.get('new_tests', []))}"]
        cov = d.get("coverage", {})
        if cov:
            out += ["", "| Acceptance criterion | Tests |", "|---|---|"]
            out += [f"| {ac} | {', '.join(ts) or '**none**'} |" for ac, ts in cov.items()]
        fb = d.get("fail_before")
        if fb is not None:
            out += ["", f"- On the base commit, {fb.get('failed', 0)} of {fb.get('total', 0)} new tests fail "
                    f"(at least one must fail, so the tests exercise the change)."]
        if d.get("failures"):
            out += ["", "Failing tests:"] + [f"- `{f}`" for f in d["failures"][:30]]
        out += [f"- {r}" for r in a.get("reasons", [])] + [""]
    if tester_out:
        out += ["## Tester notes\n", tester_out.get("notes", "")]
        if tester_out.get("suspected_bugs"):
            out += ["", "Suspected implementation bugs reported by the tester:"]
            out += [f"- {b}" for b in tester_out["suspected_bugs"]]
    return "\n".join(out) + "\n"


def pr_md(issue: dict[str, Any], spec: dict[str, Any], design: dict[str, Any], impl: dict[str, Any] | None,
          test_attempts: list[dict[str, Any]], links: dict[str, str]) -> str:
    acs = [ac for r in spec.get("requirements", []) for ac in r.get("acceptance_criteria", [])]
    last = test_attempts[-1]["details"] if test_attempts else {}
    out = [f"Closes #{issue['number']}\n",
           f"**autose** generated this pull request for issue #{issue['number']} ({issue.get('title', '')}).",
           "A separate reviewer agent will post a review; a person decides whether to merge.\n",
           "## What changed\n", design.get("summary", ""), "",
           (impl or {}).get("summary", ""), "",
           "## Acceptance criteria covered\n"]
    out += [f"- {ac['id']}: Given {ac['given']}, when {ac['when']}, then {ac['then']}." for ac in acs]
    s = last.get("suite", {})
    out += ["", "## Tests\n", f"- Full suite: {s.get('passed', '?')} passed, {s.get('failed', '?')} failed",
            f"- New tests: `{last.get('test_file', '')}` ({len(last.get('new_tests', []))} tests)", "",
            "## Run artifacts\n"]
    out += [f"- [{k}]({v})" for k, v in links.items()]
    return "\n".join(out) + "\n"


def review_md(pr: int, rnd: int, review: dict[str, Any], final_verdict: str, overrides: list[str],
              executed: list[str], meta: dict[str, Any]) -> str:
    v = "✅ APPROVE" if final_verdict == "approve" else "❌ REQUEST CHANGES"
    out = [f"<!-- autose -->\n# Independent review: PR #{pr}, round {rnd}\n",
           f"**Verdict: {v}**" + (f" → route: `{review.get('route')}`" if final_verdict != "approve" else ""),
           f"\nReviewer: {meta.get('model')} in a separate job, contents:read token, saw only the issue, "
           "the diff and the repository at the PR head.\n", review.get("summary", ""), ""]
    if overrides:
        out += ["**Verdict rules applied:**"] + [f"- {o}" for o in overrides] + [""]
    out += ["## Requirements from the issue (reviewer's reading)\n", "| Requirement | Met | Evidence |", "|---|---|---|"]
    out += [f"| {c['requirement']} | {c['met']} | {c['evidence']} |" for c in review.get("requirement_checks", [])]
    if review.get("findings"):
        out += ["", "## Findings\n", "| Severity | Category | Where | Finding | Evidence | Suggested fix |",
                "|---|---|---|---|---|---|"]
        out += [f"| {f['severity']} | {f['category']} | `{f['file']}:{f['line']}` | {f['description']} | "
                f"{f['evidence']} | {f['suggested_fix']} |" for f in review["findings"]]
    out += ["", "## Commands the reviewer actually ran\n"] + [f"- `{c}`" for c in executed or ["(none)"]]
    if review.get("risks_considered"):
        out += ["", "## Risks considered\n"] + [f"- {r}" for r in review["risks_considered"]]
    out += ["", f"<sub>cost ${meta.get('cost_usd', 0):.3f}, {meta.get('num_turns', 0)} turns</sub>"]
    return "\n".join(out).replace("\r", "") + "\n"
