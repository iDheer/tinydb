"""Durable state and artifacts on the orphan branch `autose-artifacts` (ADR-004).

Layout:
  issue-N/state.json
  issue-N/run-<run_id>-<attempt>/{spec.md, design.md, diff.patch, test_report.md, pr.md,
                                  review-round-K.md, logs/...}
Without a token (local runs) the store is a plain directory.
"""
from __future__ import annotations

import base64
import json
import os
import shutil
import tempfile
import time
from pathlib import Path
from typing import Any

from common import log, run


class Store:
    def __init__(self, repo: str, token: str | None, branch: str = "autose-artifacts",
                 local_root: Path | None = None):
        self.repo, self.token, self.branch = repo, token, branch
        self.dir = local_root or Path(tempfile.mkdtemp(prefix="autose-store-"))
        self.remote = f"https://github.com/{repo}.git"
        self._ready = False

    # -- git plumbing ------------------------------------------------------------------
    def _git(self, *args: str, check: bool = True):
        cmd = ["git"]
        if self.token:
            basic = base64.b64encode(f"x-access-token:{self.token}".encode()).decode()
            cmd += ["-c", f"http.extraheader=AUTHORIZATION: basic {basic}"]
        env = {k: v for k, v in os.environ.items() if k in ("PATH", "HOME", "USERPROFILE", "SYSTEMROOT", "TMP", "TEMP")}
        env |= {"GIT_TERMINAL_PROMPT": "0", "GIT_AUTHOR_NAME": "autose-bot", "GIT_COMMITTER_NAME": "autose-bot",
                "GIT_AUTHOR_EMAIL": "autose-bot@users.noreply.github.com",
                "GIT_COMMITTER_EMAIL": "autose-bot@users.noreply.github.com"}
        return run(cmd + list(args), cwd=self.dir, env=env, check=check, timeout=180)

    def open(self) -> "Store":
        if self._ready:
            return self
        if not self.token:
            self.dir.mkdir(parents=True, exist_ok=True)
            self._ready = True
            return self
        if not (self.dir / ".git").exists():
            self.dir.mkdir(parents=True, exist_ok=True)
            self._git("init", "-q")
            self._git("remote", "add", "origin", self.remote)
        self._sync()
        self._ready = True
        return self

    def _sync(self) -> None:
        if self._git("fetch", "-q", "--depth", "1", "origin", self.branch, check=False).returncode == 0:
            self._git("checkout", "-q", "-B", self.branch, "FETCH_HEAD")
            self._git("reset", "-q", "--hard", "FETCH_HEAD")
        else:
            self._git("checkout", "-q", "--orphan", self.branch, check=False)
            (self.dir / "README.md").write_text(
                "# autose artifacts\n\nState and artifacts of every autose run, one folder per issue.\n",
                encoding="utf-8")

    # -- content -----------------------------------------------------------------------
    def read_json(self, rel: str, default: Any = None) -> Any:
        p = self.dir / rel
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else default

    def read_text(self, rel: str) -> str | None:
        p = self.dir / rel
        return p.read_text(encoding="utf-8") if p.exists() else None

    def list_dirs(self, rel: str) -> list[str]:
        p = self.dir / rel
        return sorted(x.name for x in p.iterdir() if x.is_dir()) if p.exists() else []

    def save(self, message: str, files: dict[str, Path | str]) -> None:
        """Copy files (rel path -> source path or text) and push, retrying on races."""
        for attempt in range(6):
            for rel, src in files.items():
                dst = self.dir / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                if isinstance(src, Path):
                    if src.is_dir():
                        shutil.copytree(src, dst, dirs_exist_ok=True)
                    elif src.exists():
                        shutil.copy2(src, dst)
                else:
                    dst.write_text(src, encoding="utf-8", newline="\n")
            if not self.token:
                return
            self._git("add", "-A")
            if self._git("diff", "--cached", "--quiet", check=False).returncode == 0:
                return
            self._git("commit", "-q", "-m", message)
            push = self._git("push", "-q", "origin", f"HEAD:refs/heads/{self.branch}", check=False)
            if push.returncode == 0:
                return
            log(f"store push rejected (attempt {attempt + 1}), re-syncing: {push.stderr.strip()[:200]}")
            time.sleep(2 + attempt * 2)
            self._sync()  # discard our commit, re-apply files on top of the new remote state
        raise RuntimeError("could not push artifacts after 6 attempts")

    def url(self, rel: str) -> str:
        return f"https://github.com/{self.repo}/tree/{self.branch}/{rel}"

    def blob_url(self, rel: str) -> str:
        return f"https://github.com/{self.repo}/blob/{self.branch}/{rel}"
