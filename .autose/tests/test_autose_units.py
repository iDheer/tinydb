"""Unit tests for the deterministic parts of autose (no model calls).

Run with: python -m pytest -q -p no:cacheprovider --no-cov -c /dev/null .autose/tests
"""
from __future__ import annotations

import asyncio
import http.client
import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

import checks  # noqa: E402
import gate  # noqa: E402
from keyproxy import KeyProxy  # noqa: E402
from policy import Policy  # noqa: E402
from review import apply_rules, route_for  # noqa: E402


# -- policy ---------------------------------------------------------------------------
def test_policy_reads_limited_to_worktree(tmp_path):
    p = Policy("planner", tmp_path)
    assert p.decide("Read", {"file_path": str(tmp_path / "tinydb" / "table.py")})[0]
    assert not p.decide("Read", {"file_path": str(tmp_path / ".git" / "config")})[0]
    assert not p.decide("Read", {"file_path": str(tmp_path.parent / "secret.txt")})[0]
    assert not p.decide("Read", {"file_path": "/proc/self/environ"})[0]
    assert not p.decide("Write", {"file_path": str(tmp_path / "x.py")})[0]  # planner has no Write
    assert not p.decide("Bash", {"command": "ls"})[0]


def test_policy_writes_only_declared_files(tmp_path):
    p = Policy("implementer", tmp_path, writable={"tinydb/queries.py"})
    assert p.decide("Edit", {"file_path": str(tmp_path / "tinydb" / "queries.py")})[0]
    assert not p.decide("Edit", {"file_path": str(tmp_path / "tinydb" / "table.py")})[0]
    assert not p.decide("Write", {"file_path": str(tmp_path / ".github" / "workflows" / "x.yml")})[0]
    assert not p.decide("Write", {"file_path": str(tmp_path / "tinydb" / ".." / ".autose" / "policy.py")})[0]


def test_policy_bash_allowlist_and_metacharacters(tmp_path):
    p = Policy("tester", tmp_path)
    assert p.decide("Bash", {"command": "python -m pytest -q tests/test_x.py"})[0]
    assert p.decide("Bash", {"command": "git diff"})[0]
    for bad in ("curl https://evil", "python -m pytest; curl x", "git push origin HEAD",
                "python -m pytest | tee out", "cat ~/.bashrc", "env", "python -m pytest $(id)",
                "git diff > a.txt", "pip install requests"):
        assert not p.decide("Bash", {"command": bad})[0], bad


def test_policy_reviewer_scratch(tmp_path):
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    work = tmp_path / "work"
    work.mkdir()
    p = Policy("reviewer", work, scratch=scratch)
    assert p.decide("Write", {"file_path": str(scratch / "probe.py")})[0]
    assert not p.decide("Write", {"file_path": str(work / "tinydb" / "table.py")})[0]
    assert p.decide("Bash", {"command": f"python {(scratch / 'probe.py').as_posix()}"})[0]
    assert not p.decide("Bash", {"command": f"python {(work / 'evil.py').as_posix()}"})[0]


def test_policy_allows_structured_output_for_every_role(tmp_path):
    # Found by the first real-SDK smoke test: output_format answers via this internal tool.
    for role in ("planner", "judge", "implementer", "tester", "reviewer"):
        assert Policy(role, tmp_path).decide("StructuredOutput", {"version": "x"})[0]


def test_policy_hook_output_shape(tmp_path):
    p = Policy("planner", tmp_path)
    out = asyncio.run(p.hook()({"tool_name": "Bash", "tool_input": {"command": "ls"}}, None, None))
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert p.denials and p.calls


# -- gate -----------------------------------------------------------------------------
def test_gate_label_and_comment_rules():
    lab = {"label": {"name": "autose"}, "issue": {"number": 3}, "sender": {"type": "User"}}
    assert gate.decide("issues", lab)["run"] == "true"
    assert gate.decide("issues", lab | {"label": {"name": "bug"}})["run"] == "false"
    com = {"comment": {"body": "/autose", "author_association": "OWNER", "user": {"type": "User"}},
           "issue": {"number": 4}}
    assert gate.decide("issue_comment", com)["mode"] == "start"
    outsider = json.loads(json.dumps(com))
    outsider["comment"]["author_association"] = "NONE"
    assert gate.decide("issue_comment", outsider)["run"] == "false"
    chatter = json.loads(json.dumps(com))
    chatter["comment"]["body"] = "I think /autose would help"
    assert gate.decide("issue_comment", chatter)["run"] == "false"
    assert gate.decide("workflow_dispatch", {"inputs": {"issue": "x"}})["run"] == "false"


# -- key proxy ------------------------------------------------------------------------
def test_keyproxy_injects_key_and_streams():
    seen = {}

    class Up(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *a):
            pass

        def do_POST(self):
            seen["key"] = self.headers.get("x-api-key")
            seen["body"] = self.rfile.read(int(self.headers["Content-Length"]))
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Transfer-Encoding", "chunked")
            self.end_headers()
            for part in (b"event: a\n\n", b"event: b\n\n"):
                self.wfile.write(b"%x\r\n%s\r\n" % (len(part), part))
            self.wfile.write(b"0\r\n\r\n")

    up = ThreadingHTTPServer(("127.0.0.1", 0), Up)
    threading.Thread(target=up.serve_forever, daemon=True).start()
    proxy = KeyProxy(api_key="sk-ant-REAL", upstream_host="127.0.0.1",
                     upstream_port=up.server_address[1], upstream_tls=False).start()
    try:
        env = proxy.agent_env()
        assert "REAL" not in json.dumps(env)
        host, port = env["ANTHROPIC_BASE_URL"].split("//")[1].split(":")
        c = http.client.HTTPConnection(host, int(port))
        c.request("POST", "/v1/messages", body=b'{"x":1}', headers={"x-api-key": env["ANTHROPIC_API_KEY"],
                                                                     "Content-Type": "application/json"})
        r = c.getresponse()
        assert r.status == 200 and r.read() == b"event: a\n\nevent: b\n\n"
        assert seen["key"] == "sk-ant-REAL" and seen["body"] == b'{"x":1}'
        c2 = http.client.HTTPConnection(host, int(port))
        c2.request("POST", "/v1/messages", body=b"{}", headers={"x-api-key": "wrong"})
        assert c2.getresponse().status == 403
    finally:
        proxy.stop()
        up.shutdown()


# -- checks ---------------------------------------------------------------------------
def _spec(**over):
    s = {"verdict": "READY-WITH-OPEN-ITEMS", "open_questions": [], "requirements": [{
        "id": "FR-Q-001", "priority": "MUST", "status": "READY", "acceptance_criteria": [
            {"id": "FR-Q-001.AC-1", "given": "a table with two documents", "when": "search(q) runs",
             "then": "it returns only document 2"}]}]}
    s.update(over)
    return s


def test_check_spec_pass_and_vague_and_draft():
    judge = {"criteria": [{"id": "FR-Q-001.AC-1", "testable": True, "reason": "ok"}]}
    assert checks.check_spec(_spec(), judge)["passed"]
    vague = _spec()
    vague["requirements"][0]["acceptance_criteria"][0]["then"] = "it is handled correctly"
    assert not checks.check_spec(vague, judge)["passed"]
    draft = checks.check_spec(_spec(verdict="DRAFT", open_questions=[{"id": "Q-001", "priority": "P1"}]), judge)
    assert not draft["passed"] and draft["details"]["needs_info"]
    assert not checks.check_spec(_spec(), {"criteria": [{"id": "FR-Q-001.AC-1", "testable": False,
                                                        "reason": "x"}]})["passed"]


def test_check_design_symbols(tmp_path):
    (tmp_path / "tinydb").mkdir()
    (tmp_path / "tinydb" / "queries.py").write_text("class Query:\n    def fragment(self):\n        pass\n")
    d = {"files": [{"path": "tinydb/queries.py", "change": "modify", "purpose": "",
                    "symbols": [{"name": "Query.fragment", "kind": "method", "change": "modify",
                                 "description": ""}]}],
         "ac_mapping": [{"ac_id": "FR-Q-001.AC-1", "symbols": ["Query.fragment"], "test_idea": "x"}]}
    assert checks.check_design(d, _spec(), tmp_path, "tests/t.py")["passed"]
    d["files"][0]["symbols"][0]["name"] = "Query.nope"
    assert not checks.check_design(d, _spec(), tmp_path, "tests/t.py")["passed"]


def test_ac_slug_and_secret_scan():
    assert checks.ac_slug("FR-QUERY-001.AC-2") == "fr_query_001_ac_2"
    assert checks.secret_scan("+ key = 'sk-ant-abcdefghijklmno'", [])
    assert not checks.secret_scan("+ ANTHROPIC_API_KEY=sk-ant-autose-dummy-1234567890", [])
    assert checks.secret_scan("+ x = 'hunter2hunter2'", ["hunter2hunter2"])


# -- reviewer rules -------------------------------------------------------------------
def test_review_rules_turn_weak_approvals_into_changes():
    good = {"verdict": "approve", "findings": [], "requirement_checks": [
        {"requirement": "r", "met": "yes", "evidence": "probe passed"}]}
    assert apply_rules(good, ["python -m pytest -q"]) == ("approve", [])
    v, o = apply_rules(good, ["python -m pytest -q tests/test_queries.py"])
    assert v == "request_changes" and o
    bad = dict(good, findings=[{"severity": "major", "category": "approach"}])
    v, _ = apply_rules(bad, ["python -m pytest -q"])
    assert v == "request_changes" and route_for(bad | {"route": "none"}, v) == "design"
