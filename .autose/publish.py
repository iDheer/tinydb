"""publish job: post the review, keep state, route the next round or hand over (ADR-002, ADR-008).

Never merges. Posts a COMMENT-type review so a bot verdict can never satisfy branch protection."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import GitHub, Secrets, load_config, log, run_url  # noqa: E402
from store import Store  # noqa: E402


def merge_readiness(state: dict, verdict: dict, send_backs: int, max_send_backs: int) -> str:
    runs = [r for r in state.get("runs", []) if r.get("variant", "baseline") == "baseline"]
    last = runs[-1] if runs else {}
    passed = last.get("passed_stages", [])
    ci = state.get("ci") or {}
    ok = verdict["verdict"] == "approve"
    rows = [
        ("Stage checks in the last build run", ", ".join(f"✅ {s}" for s in passed) or "❌ none"
         if last.get("status") == "pr-open" else f"❌ last build run status: {last.get('status')}"),
        ("CI on head commit", f"{'✅' if ci.get('conclusion') == 'success' else '❌'} {ci.get('conclusion')} "
                              f"on `{(verdict.get('head_sha') or '')[:10]}` {ci.get('url') or ''}"),
        ("Independent review (separate job, Opus 5.5, read-only)",
         "✅ approve" if ok else f"❌ request changes ({len(verdict.get('findings', []))} finding(s))"),
        ("Review send-backs used", f"{send_backs} of {max_send_backs}"),
        ("Total model cost for this issue", f"${sum(r.get('cost_usd', 0) for r in state.get('runs', [])):.2f} "
                                            f"(+ review ${verdict['meta'].get('cost_usd', 0):.2f})"),
        ("Human decision", "⏳ required: autose never merges"),
    ]
    overall = ("READY FOR HUMAN REVIEW: all automated checks passed and the independent reviewer approved."
               if ok and last.get("status") == "pr-open" else
               "NOT READY: the reviewer still requests changes after the allowed rounds. Read the findings "
               "before deciding; merging is possible but not recommended.")
    lines = ["<!-- autose -->", "## MERGE_READINESS_CHECK", "", "| Check | Result |", "|---|---|"]
    lines += [f"| {a} | {b} |" for a, b in rows]
    lines += ["", f"**{overall}**", "", f"Review run: {run_url()}"]
    return "\n".join(lines) + "\n"


def main() -> int:
    cfg = load_config()
    sec = Secrets.take_from_env()
    repo = os.environ["GITHUB_REPOSITORY"]
    gh = GitHub(sec.gh_token, repo, cfg)
    rdir = Path(os.environ["AUTOSE_REVIEW_OUT"])
    verdict = json.loads((rdir / "verdict.json").read_text(encoding="utf-8"))
    review_md = (rdir / "review.md").read_text(encoding="utf-8")
    pr, issue, rnd = verdict["pr"], int(os.environ["AUTOSE_ISSUE"]), verdict["round"]
    experiment = os.environ.get("AUTOSE_EXPERIMENT", "")
    variant = verdict.get("variant", "baseline")
    store = Store(repo, sec.gh_token, cfg["repo"]["artifacts_branch"]).open()

    if experiment:
        # Seeded-PR / decision experiments: post and store, never route.
        rel = f"experiments/{experiment}/pr-{pr}-{variant}-{os.environ.get('GITHUB_RUN_ID', 'local')}"
        gh.gh("pr", "review", str(pr), "--repo", repo, "--comment", "--body-file", "-",
              input=review_md + f"\n<sub>experiment `{experiment}`, variant `{variant}`</sub>\n")
        store.save(f"experiment {experiment}: PR #{pr} {variant}", {rel: rdir})
        log(f"experiment review stored at {rel}")
        return 0

    state = store.read_json(f"issue-{issue}/state.json", {}) or {}
    history = state.setdefault("reviews", [])
    history.append({"round": rnd, "verdict": verdict["verdict"], "route": verdict["route"],
                    "findings": len(verdict["findings"]), "cost_usd": verdict["meta"].get("cost_usd"),
                    "run_url": run_url(), "head_sha": verdict.get("head_sha")})
    state["last_review"] = {"round": rnd, "findings": verdict["findings"], "verdict": verdict["verdict"]}
    send_backs = state.get("send_backs", 0)
    run_dir = (state.get("runs") or [{}])[-1].get("dir", f"issue-{issue}/review")

    gh.gh("pr", "review", str(pr), "--repo", repo, "--comment", "--body-file", "-", input=review_md)
    files: dict = {f"{run_dir}/review-round-{rnd}.md": rdir / "review.md",
                   f"{run_dir}/review-round-{rnd}.json": rdir / "verdict.json",
                   f"{run_dir}/review-logs-round-{rnd}": rdir / "logs"}

    max_sb = cfg["budgets"]["max_send_backs"]
    if verdict["verdict"] != "approve" and send_backs < max_sb:
        state["send_backs"] = send_backs + 1
        nxt = rnd + 1
        files[f"issue-{issue}/state.json"] = json.dumps(state, indent=2) + "\n"
        store.save(f"issue #{issue}: review round {rnd} requested changes", files)
        gh.gh("workflow", "run", "autose.yml", "--repo", repo, "--ref", cfg["repo"]["default_branch"],
              "-f", f"issue={issue}", "-f", "mode=rework", "-f", f"from_stage={verdict['route']}",
              "-f", f"round={nxt}")
        gh.comment_pr(pr, f"<!-- autose -->\nReview round {rnd} requested changes → back to stage "
                          f"**{'2 (design)' if verdict['route'] == 'design' else '3 (implementation)'}** "
                          f"for round {nxt} (send-back {send_backs + 1} of {max_sb}).")
        log(f"routed to {verdict['route']} for round {nxt}")
        return 0

    files[f"issue-{issue}/state.json"] = json.dumps(state | {"status": "handover"}, indent=2) + "\n"
    store.save(f"issue #{issue}: handover after review round {rnd}", files)
    gh.comment_pr(pr, merge_readiness(state, verdict, send_backs, max_sb))
    gh.add_labels(pr, "autose:ready-for-human")
    gh.remove_labels(issue, "autose:running")
    log("handed over to a human")
    return 0


if __name__ == "__main__":
    sys.exit(main())
