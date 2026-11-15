"""gate job: decide whether this event may start a run (ADR-010).

Reads the event from $GITHUB_EVENT_PATH; never from interpolated `${{ }}` text."""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import ALLOWED_ASSOCIATIONS, GitHub, Secrets, load_config, log, run_url, set_output  # noqa: E402

LABEL = "autose"


def decide(event_name: str, ev: dict, gh: GitHub | None = None) -> dict:
    no = {"run": "false"}
    if event_name == "workflow_dispatch":
        i = ev.get("inputs") or {}
        mode = i.get("mode") or "start"
        if mode not in ("start", "rework", "review") or not str(i.get("issue", "")).isdigit():
            return no | {"why": "invalid dispatch inputs"}
        return {"run": "true", "issue": i["issue"], "mode": mode, "from_stage": i.get("from_stage") or "",
                "round": i.get("round") or "1", "pr": i.get("pr") or "", "variant": i.get("variant") or "baseline",
                "stop_after": i.get("stop_after") or "", "experiment": i.get("experiment") or ""}
    if event_name == "issues":
        issue = ev.get("issue") or {}
        if (ev.get("label") or {}).get("name") != LABEL or issue.get("pull_request"):
            return no | {"why": "not the autose label on an issue"}
        if (ev.get("sender") or {}).get("type") == "Bot":
            return no | {"why": "label added by a bot"}
        return {"run": "true", "issue": str(issue["number"]), "mode": "start", "from_stage": "", "round": "1",
                "pr": "", "variant": "baseline", "stop_after": "", "experiment": ""}
    if event_name == "issue_comment":
        c = ev.get("comment") or {}
        body = (c.get("body") or "").strip()
        if not re.match(r"^/autose(\s|$)", body):
            return no | {"why": "not an /autose command"}
        if (c.get("user") or {}).get("type") == "Bot":
            return no | {"why": "comment by a bot"}
        if c.get("author_association") not in ALLOWED_ASSOCIATIONS:
            return no | {"why": f"author_association {c.get('author_association')} may not trigger autose"}
        issue = ev.get("issue") or {}
        if not issue.get("pull_request"):
            return {"run": "true", "issue": str(issue["number"]), "mode": "start", "from_stage": "", "round": "1",
                    "pr": "", "variant": "baseline", "stop_after": "", "experiment": ""}
        # A comment on a PR: `/autose review` re-runs the independent review of an autose PR.
        if not re.match(r"^/autose\s+review\b", body):
            return no | {"why": "on a PR only `/autose review` is supported"}
        head = ""
        if gh and gh.enabled:
            head = (gh.gh_json("pr", "view", str(issue["number"]), "--repo", gh.repo, "--json", "headRefName")
                    or {}).get("headRefName", "")
        m = re.match(r"^autose/issue-(\d+)$", head)
        if not m:
            return no | {"why": f"PR head {head!r} is not an autose branch"}
        return {"run": "true", "issue": m.group(1), "mode": "review", "from_stage": "", "round": "",
                "pr": str(issue["number"]), "variant": "baseline", "stop_after": "", "experiment": ""}
    return no | {"why": f"event {event_name} not handled"}


def main() -> int:
    cfg = load_config()
    sec = Secrets.take_from_env()
    gh = GitHub(sec.gh_token, os.environ.get("GITHUB_REPOSITORY", "local/tinydb"), cfg)
    ev = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text(encoding="utf-8"))
    d = decide(os.environ.get("GITHUB_EVENT_NAME", ""), ev, gh)
    log(f"gate decision: {d}")
    set_output(**{k: v for k, v in d.items() if k != "why"})
    if d["run"] == "true" and d["mode"] == "start" and gh.enabled:
        gh.add_labels(int(d["issue"]), "autose:running")
        gh.remove_labels(int(d["issue"]), "autose:needs-info", "autose:stopped")
        gh.comment_issue(int(d["issue"]), f"<!-- autose -->\nautose run started: {run_url()}\n\n"
                                          "Stages: requirements → design → implementation → testing → release → "
                                          "independent review. A person decides whether to merge.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
