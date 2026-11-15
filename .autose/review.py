"""review job: the independent reviewer (ADR-008).

Inputs (prepared by an earlier, non-agent step of the same job that holds a read-only token):
  $AUTOSE_REVIEW_IN/issue.json     issue title, body and comments
  $AUTOSE_REVIEW_IN/informed.json  only for the `informed` experiment variant: PR body, spec, design
The work tree is the PR head, checked out fresh by this job. The agent gets no GitHub token.
"""
from __future__ import annotations

import json
import os
import secrets as pysecrets
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import render  # noqa: E402
import schemas  # noqa: E402
from agents import AgentRunner  # noqa: E402
from common import PROMPTS, Secrets, dump_json, load_config, log, run, set_output, trusted_comments, write  # noqa: E402
from keyproxy import KeyProxy  # noqa: E402
from orchestrator import fence  # noqa: E402
from policy import Policy  # noqa: E402


def apply_rules(review: dict, executed: list[str]) -> tuple[str, list[str]]:
    """Anti-rubber-stamp rules. Returns (final_verdict, overrides)."""
    overrides = []
    verdict = review.get("verdict", "request_changes")
    if verdict == "approve":
        serious = [f for f in review.get("findings", []) if f["severity"] in ("blocker", "major")]
        if serious:
            overrides.append(f"approve → request changes: {len(serious)} blocker/major finding(s)")
        full_suite = any("pytest" in c and not any(a.endswith(".py") or "::" in a for a in c.split()[1:])
                         and "tests/test_" not in c for c in executed)
        if not full_suite:
            overrides.append("approve → request changes: the reviewer did not run the full test suite")
        checks_ = review.get("requirement_checks", [])
        if not checks_ or any(not (c.get("evidence") or "").strip() or c.get("met") != "yes" for c in checks_):
            overrides.append("approve → request changes: a requirement is not met or has no evidence")
        if overrides:
            verdict = "request_changes"
    return verdict, overrides


def route_for(review: dict, verdict: str) -> str:
    if verdict == "approve":
        return "none"
    if review.get("route") in ("design", "implement"):
        return review["route"]
    serious = [f for f in review.get("findings", []) if f["severity"] in ("blocker", "major")]
    return "design" if any(f["category"] == "approach" for f in serious) else "implement"


def main() -> int:
    cfg = load_config()
    sec = Secrets.take_from_env()
    work = Path(os.environ["AUTOSE_WORK"]).resolve()
    inp = Path(os.environ["AUTOSE_REVIEW_IN"])
    out = Path(os.environ.get("RUNNER_TEMP", "/tmp")) / "autose" / "review-out"
    scratch = Path(os.environ.get("RUNNER_TEMP", "/tmp")) / "autose" / "review-scratch"
    scratch.mkdir(parents=True, exist_ok=True)
    pr, rnd = os.environ["AUTOSE_PR"], int(os.environ.get("AUTOSE_ROUND") or 1)
    variant = os.environ.get("AUTOSE_VARIANT", "baseline") or "baseline"
    issue = json.loads((inp / "issue.json").read_text(encoding="utf-8"))
    base = run(["git", "merge-base", "origin/main", "HEAD"], cwd=work, check=True).stdout.strip()
    diff = run(["git", "diff", base, "HEAD"], cwd=work, check=True).stdout
    nonce = pysecrets.token_hex(6)

    body = f"# {issue.get('title', '')}\n\n{issue.get('body') or ''}"
    parts = [f"Pull request #{pr} claims to address this issue:",
             fence("issue", nonce, body, author=(issue.get("author") or {}).get("login", "?"))]
    for c in trusted_comments(issue):
        parts.append(fence("comment", nonce, c["body"], author=c["author"], association="maintainer"))
    parts += [f"The diff (base {base[:10]} → PR head):\n```diff\n{diff[:60000]}\n```",
              f"The repository at the PR head is your working directory. Scratch directory for probes: {scratch}"]
    if variant == "informed" and (inp / "informed.json").exists():
        extra = json.loads((inp / "informed.json").read_text(encoding="utf-8"))
        parts.append("Context from the implementation side (PR description, spec and design):\n\n"
                     + "\n\n".join(f"### {k}\n{v}" for k, v in extra.items() if v))
    parts.append("Review it and return the JSON verdict.")

    proxy = None if os.environ.get("AUTOSE_FAKE") else KeyProxy(api_key=sec.anthropic_key,
                                                                oauth_token=sec.oauth_token).start()
    runner = AgentRunner(cfg, out / "logs", proxy.agent_env() if proxy else {})
    system = (PROMPTS / "common.md").read_text(encoding="utf-8") + "\n\n" + \
        (PROMPTS / "reviewer.md").read_text(encoding="utf-8")
    policy = Policy("reviewer", work, scratch=scratch)
    res = runner.run("reviewer", f"reviewer.r{rnd}", system, "\n\n".join(parts), schemas.REVIEW, policy)
    if proxy:
        proxy.stop()
    if not res.ok:
        review = {"verdict": "request_changes", "route": "implement", "findings": [], "requirement_checks": [],
                  "issue_requirements": [], "checks_run": [], "risks_considered": [],
                  "summary": f"The reviewer agent failed: {res.error}"}
        final, overrides = "request_changes", ["reviewer error: treated as request changes"]
    else:
        review = res.output
        final, overrides = apply_rules(review, res.executed_bash)
    route = route_for(review, final)
    meta = {"model": res.model, "cost_usd": res.cost_usd, "num_turns": res.num_turns, "usage": res.usage,
            "variant": variant, "ok": res.ok, "error": res.error}
    write(out / "review.md", render.review_md(int(pr), rnd, review, final, overrides, res.executed_bash, meta))
    dump_json(out / "verdict.json", {"pr": int(pr), "issue": int(issue.get("number", 0) or os.environ.get("AUTOSE_ISSUE", 0)),
                                     "round": rnd, "raw_verdict": review.get("verdict"), "verdict": final,
                                     "route": route, "overrides": overrides, "findings": review.get("findings", []),
                                     "executed": res.executed_bash, "meta": meta, "variant": variant,
                                     "head_sha": run(["git", "rev-parse", "HEAD"], cwd=work).stdout.strip()})
    dump_json(out / "review.json", review)
    log(f"review verdict: raw={review.get('verdict')} final={final} route={route} overrides={overrides}")
    set_output(verdict=final, route=route)
    return 0


if __name__ == "__main__":
    sys.exit(main())
