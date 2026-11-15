"""Shared helpers: configuration, environment hygiene, subprocesses, GitHub CLI."""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import time
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
PROMPTS = HERE / "prompts"
SKILL_PATH = HERE / "skills" / "requirements-specifier" / "SKILL.md"

ALLOWED_ASSOCIATIONS = {"OWNER", "MEMBER", "COLLABORATOR"}

# Names of environment variables that must never reach an agent or a test run.
_SECRET_NAME = re.compile(r"(TOKEN|KEY|SECRET|PASSWORD|CREDENTIAL)", re.I)
# Variables that are safe and useful to keep even though they match the pattern above.
_KEEP = {"AUTOSE_KEYPROXY_URL"}


def load_config() -> dict[str, Any]:
    with open(HERE / "config.toml", "rb") as fh:
        return tomllib.load(fh)


def log(msg: str) -> None:
    print(f"[autose {time.strftime('%H:%M:%S')}] {msg}", flush=True)


@dataclass
class Secrets:
    """Secrets are read once at start-up and removed from os.environ, so that no child
    process (agent CLI, Bash tool, pytest, code written by an agent) inherits them."""

    anthropic_key: str | None = None
    oauth_token: str | None = None
    gh_token: str | None = None
    values: list[str] = field(default_factory=list)

    @classmethod
    def take_from_env(cls) -> "Secrets":
        s = cls(
            anthropic_key=os.environ.pop("AUTOSE_ANTHROPIC_KEY", None) or None,
            oauth_token=os.environ.pop("AUTOSE_OAUTH_TOKEN", None) or None,
            gh_token=os.environ.pop("AUTOSE_GH_TOKEN", None) or None,
        )
        for name in list(os.environ):
            if _SECRET_NAME.search(name) and name not in _KEEP:
                val = os.environ.pop(name)
                if len(val) >= 12:
                    s.values.append(val)
        s.values += [v for v in (s.anthropic_key, s.oauth_token, s.gh_token) if v]
        return s


def scrubbed_env(extra: dict[str, str] | None = None) -> dict[str, str]:
    """Minimal environment for check runs (pytest, mypy) of agent-written code."""
    keep = ("PATH", "HOME", "LANG", "LC_ALL", "TMPDIR", "TEMP", "TMP", "SYSTEMROOT",
            "PYTHONPATH", "VIRTUAL_ENV", "pythonLocation", "USERPROFILE", "COMSPEC",
            "PATHEXT", "WINDIR")
    env = {k: v for k, v in os.environ.items() if k in keep}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONHASHSEED"] = "0"
    if extra:
        env.update(extra)
    return env


def run(cmd: list[str], cwd: str | Path | None = None, env: dict[str, str] | None = None,
        timeout: int = 600, check: bool = False, input: str | None = None) -> subprocess.CompletedProcess:
    p = subprocess.run(cmd, cwd=cwd, env=env, timeout=timeout, capture_output=True, text=True,
                       input=input, encoding="utf-8", errors="replace")
    if check and p.returncode != 0:
        raise RuntimeError(f"command failed ({p.returncode}): {' '.join(cmd)}\n{p.stdout}\n{p.stderr}")
    return p


_UNSHARE_OK: bool | None = None


def netless_prefix() -> list[str]:
    """`unshare -rn` puts a check run into a new network namespace with no interfaces
    (Linux only). Probed once; if unavailable we say so in the logs."""
    global _UNSHARE_OK
    if _UNSHARE_OK is None:
        _UNSHARE_OK = bool(sys.platform.startswith("linux") and shutil.which("unshare")
                           and run(["unshare", "-rn", "true"]).returncode == 0)
        log(f"network-less check runs: {'on' if _UNSHARE_OK else 'UNAVAILABLE (plain env scrub only)'}")
    return ["unshare", "-rn"] if _UNSHARE_OK else []


_BWRAP_OK: bool | None = None


def jail_prefix(workdir: Path, scratch: Path | None = None) -> list[str]:
    """argv prefix that runs one agent Bash command in a bubblewrap jail (ADR-009):
    no network, own PID/IPC namespaces and a fresh /proc (other processes and their
    environments are invisible), the whole filesystem read-only except the work tree,
    the reviewer's scratch dir and an empty /tmp; $RUNNER_TEMP is hidden.
    Falls back to `unshare -rn` (network only) when bubblewrap cannot run."""
    global _BWRAP_OK
    w = str(Path(workdir).resolve())
    args = ["bwrap", "--ro-bind", "/", "/", "--dev", "/dev", "--proc", "/proc", "--tmpfs", "/tmp"]
    rt = os.environ.get("RUNNER_TEMP")
    if rt and not w.startswith(rt.rstrip("/") + "/"):
        args += ["--tmpfs", rt]
    args += ["--bind", w, w]
    if scratch:
        s = str(Path(scratch).resolve())
        args += ["--bind", s, s]
    args += ["--unshare-net", "--unshare-pid", "--unshare-ipc", "--die-with-parent", "--new-session",
             "--chdir", w, "--"]
    if _BWRAP_OK is None:
        _BWRAP_OK = bool(sys.platform.startswith("linux") and shutil.which("bwrap")
                         and run(args + ["true"]).returncode == 0)
        log(f"agent Bash jail: {'bubblewrap' if _BWRAP_OK else 'UNAVAILABLE, falling back to unshare -rn'}")
    return args if _BWRAP_OK else netless_prefix()


def run_isolated(cmd: list[str], cwd: str | Path, timeout: int = 600) -> subprocess.CompletedProcess:
    return run(netless_prefix() + cmd, cwd=cwd, env=scrubbed_env(), timeout=timeout)


class GitHub:
    """Thin wrapper over the `gh` CLI. Only non-agent code holds one of these."""

    def __init__(self, token: str | None, repo: str, cfg: dict[str, Any]):
        self.token = token
        self.repo = repo
        owner = repo.split("/")[0].lower()
        if owner in {o.lower() for o in cfg["repo"]["forbidden_upstream_owners"]}:
            raise SystemExit(f"refusing to operate on upstream repository {repo}")
        current = os.environ.get("GITHUB_REPOSITORY")
        if current and current.lower() != repo.lower():
            raise SystemExit(f"refusing to operate on {repo}: workflow runs in {current}")

    @property
    def enabled(self) -> bool:
        return bool(self.token)

    def gh(self, *args: str, input: str | None = None, check: bool = True, timeout: int = 120) -> str:
        if not self.token:
            log(f"(dry-run gh) {' '.join(args)[:200]}")
            return ""
        env = scrubbed_env({"GH_TOKEN": self.token, "GH_PROMPT_DISABLED": "1", "NO_COLOR": "1"})
        p = run(["gh", *args], env=env, input=input, timeout=timeout)
        if check and p.returncode != 0:
            raise RuntimeError(f"gh {' '.join(args)[:300]} failed: {p.stderr.strip()[:800]}")
        return p.stdout

    def gh_json(self, *args: str) -> Any:
        out = self.gh(*args)
        return json.loads(out) if out.strip() else None

    def comment_issue(self, number: int, body: str) -> None:
        self.gh("issue", "comment", str(number), "--repo", self.repo, "--body-file", "-", input=body, check=False)

    def comment_pr(self, number: int, body: str) -> None:
        self.gh("pr", "comment", str(number), "--repo", self.repo, "--body-file", "-", input=body, check=False)

    def add_labels(self, number: int, *labels: str) -> None:
        for lab in labels:
            self.gh("label", "create", lab, "--repo", self.repo, "--force", "--color", "5319e7", check=False)
        self.gh("issue", "edit", str(number), "--repo", self.repo, "--add-label", ",".join(labels), check=False)

    def remove_labels(self, number: int, *labels: str) -> None:
        self.gh("issue", "edit", str(number), "--repo", self.repo, "--remove-label", ",".join(labels), check=False)

    def issue(self, number: int) -> dict[str, Any]:
        return self.gh_json("issue", "view", str(number), "--repo", self.repo,
                            "--json", "number,title,body,url,author,comments,labels") or {}


def run_url() -> str:
    server = os.environ.get("GITHUB_SERVER_URL", "https://github.com")
    repo = os.environ.get("GITHUB_REPOSITORY", "local/local")
    rid = os.environ.get("GITHUB_RUN_ID", "0")
    return f"{server}/{repo}/actions/runs/{rid}"


def set_output(**kv: Any) -> None:
    path = os.environ.get("GITHUB_OUTPUT")
    lines = [f"{k}={v}" for k, v in kv.items()]
    if path:
        with open(path, "a", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")
    log("outputs: " + ", ".join(lines))


def trusted_comments(issue: dict[str, Any]) -> list[dict[str, str]]:
    """Comments by maintainers only (OWNER/MEMBER/COLLABORATOR), excluding bots and
    autose's own comments and the bare `/autose` trigger lines."""
    out = []
    for c in issue.get("comments") or []:
        login = ((c.get("author") or {}).get("login") or "")
        if c.get("authorAssociation") not in ALLOWED_ASSOCIATIONS or login.endswith("[bot]") \
                or login == "github-actions":
            continue
        body = (c.get("body") or "").strip()
        if body.startswith("<!-- autose -->"):
            continue
        body = "\n".join(l for l in body.splitlines() if not l.strip().startswith("/autose")).strip()
        if body:
            out.append({"author": login, "body": body})
    return out


def write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")
    return path


def dump_json(path: Path, obj: Any) -> Path:
    return write(path, json.dumps(obj, indent=2, ensure_ascii=False, default=str) + "\n")
