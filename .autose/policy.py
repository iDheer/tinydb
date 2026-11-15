"""Per-role tool policy, enforced in a PreToolUse hook for every tool call (ADR-005).

The policy is pure Python so it can be unit-tested without a model
(see .autose/tests/test_policy.py)."""
from __future__ import annotations

import shlex
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any

ROLE_TOOLS = {
    "planner": ["Read", "Glob", "Grep"],
    "judge": [],
    "implementer": ["Read", "Glob", "Grep", "Edit", "Write", "Bash"],
    "tester": ["Read", "Glob", "Grep", "Edit", "Write", "Bash"],
    "reviewer": ["Read", "Glob", "Grep", "Bash", "Write"],
}

PY = ("python", "python3")
_BUILD_CMDS = [
    [p, "-m", m] for p in PY for m in ("pytest", "compileall", "mypy")
] + [[p, "-c"] for p in PY] + [
    ["pytest"], ["git", "diff"], ["git", "status"], ["git", "log"], ["ls"],
]
ROLE_BASH = {
    "implementer": _BUILD_CMDS,
    "tester": _BUILD_CMDS,
    "reviewer": _BUILD_CMDS + [["git", "show"]],  # + `python <scratch>/x.py`, see below
}
# Shell metacharacters that would let one allowed prefix smuggle in a second command.
_META = (";", "&", "|", "`", "$(", ">", "<", "\n", "\r")
PROTECTED_DIRS = (".git", ".github", ".autose")


@dataclass
class Policy:
    role: str
    workdir: Path
    writable: set[str] = field(default_factory=set)  # repo-relative POSIX paths
    scratch: Path | None = None
    jail: list[str] = field(default_factory=list)  # argv prefix every allowed Bash command runs under
    denials: list[dict[str, Any]] = field(default_factory=list)
    calls: list[dict[str, Any]] = field(default_factory=list)

    # -- helpers ---------------------------------------------------------------------
    def _resolve(self, raw: str | None) -> Path:
        p = Path(raw) if raw else self.workdir
        if not p.is_absolute():
            p = self.workdir / p
        return p.resolve()

    def _rel(self, p: Path) -> str | None:
        try:
            return PurePosixPath(p.relative_to(self.workdir.resolve()).as_posix()).as_posix()
        except ValueError:
            return None

    def _in_scratch(self, p: Path) -> bool:
        if not self.scratch:
            return False
        try:
            p.relative_to(self.scratch.resolve())
            return True
        except ValueError:
            return False

    def _readable(self, p: Path) -> bool:
        if self._in_scratch(p):
            return True
        rel = self._rel(p)
        if rel is None:
            return False
        return rel == "." or rel.split("/")[0] != ".git"

    # -- decision --------------------------------------------------------------------
    def decide(self, tool: str, args: dict[str, Any]) -> tuple[bool, str]:
        if tool == "StructuredOutput":
            # The SDK's internal tool that returns the final JSON answer (output_format).
            return True, "final structured answer"
        if tool not in ROLE_TOOLS.get(self.role, []):
            return False, f"tool {tool} is not available to the {self.role}"
        if tool in ("Read", "Glob", "Grep"):
            target = args.get("file_path") if tool == "Read" else args.get("path")
            p = self._resolve(target)
            if not self._readable(p):
                return False, "reads are limited to the repository working tree (not .git)"
            return True, "read inside working tree"
        if tool in ("Edit", "Write"):
            p = self._resolve(args.get("file_path"))
            if self._in_scratch(p):
                return True, "scratch write"
            rel = self._rel(p)
            if rel is None:
                return False, "writes outside the repository are not allowed"
            if rel.split("/")[0] in PROTECTED_DIRS:
                return False, f"{rel.split('/')[0]}/ is protected"
            if rel not in self.writable:
                allowed = ", ".join(sorted(self.writable)) or "nothing"
                return False, (f"{rel} is not writable for the {self.role}. Writable: {allowed}. "
                               "If the design is missing a file, finish with status design_gap.")
            return True, "declared in design"
        if tool == "Bash":
            return self._bash(args.get("command") or "")
        return False, "not allowed"

    def _bash(self, command: str) -> tuple[bool, str]:
        cmd = command.strip()
        if any(m in cmd for m in _META):
            return False, "one plain command per call: no pipes, redirects, chaining or substitution"
        try:
            argv = shlex.split(cmd)
        except ValueError:
            return False, "could not parse command"
        if not argv:
            return False, "empty command"
        if any(a.startswith("..") or "/.." in a for a in argv):
            return False, "parent-directory paths are not allowed"
        for prefix in ROLE_BASH.get(self.role, []):
            if argv[: len(prefix)] == prefix:
                return True, "allowlisted command"
        if self.role == "reviewer" and len(argv) >= 2 and argv[0] in PY:
            p = self._resolve(argv[1])
            if self._in_scratch(p) and p.suffix == ".py":
                return True, "reviewer probe script in scratch"
        return False, (f"command not allowlisted for the {self.role}: allowed are "
                       "python -m pytest/compileall/mypy, python -c, git diff/status/log, ls")

    # -- SDK hook --------------------------------------------------------------------
    def hook(self):
        async def pre_tool_use(input_data: dict[str, Any], tool_use_id: str | None, context: Any):
            tool = input_data.get("tool_name", "")
            args = input_data.get("tool_input") or {}
            ok, why = self.decide(tool, args)
            rec = {"tool": tool, "args": _short(args), "allowed": ok, "reason": why}
            self.calls.append(rec)
            if not ok:
                self.denials.append(rec)
            out: dict[str, Any] = {"hookEventName": "PreToolUse",
                                   "permissionDecision": "allow" if ok else "deny",
                                   "permissionDecisionReason": why}
            if ok and tool == "Bash" and self.jail:
                out["updatedInput"] = self.jailed(args)
            return {"hookSpecificOutput": out}
        return pre_tool_use

    def jailed(self, args: dict[str, Any]) -> dict[str, Any]:
        """The allowed command, rewritten to run inside the jail. The policy already
        rejected shell metacharacters, so the argv round-trips through shlex exactly."""
        argv = shlex.split((args.get("command") or "").strip())
        return {**args, "command": shlex.join(self.jail + argv)}

    def executed_bash(self) -> list[str]:
        return [c["args"].get("command", "") for c in self.calls if c["tool"] == "Bash" and c["allowed"]]


def _short(args: dict[str, Any]) -> dict[str, Any]:
    out = {}
    for k, v in args.items():
        if isinstance(v, str) and len(v) > 300:
            v = v[:300] + "…"
        out[k] = v
    return out
