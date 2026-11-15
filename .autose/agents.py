"""Run one agent session with the Claude Agent SDK (ADR-001, ADR-005, ADR-006).

Every call gets: a fixed tool list, a PreToolUse policy hook that decides every call,
no settings from disk, sandboxed Bash without network, the proxy's dummy credential,
turn/USD/wall-clock limits, and a JSON schema for its final answer. The transcript and
metrics are written next to the artifacts.

AUTOSE_FAKE=<dir> replaces the model with canned answers from <dir>/<label>.json (and
applies <dir>/<label>.patch to the work tree if present). Used to test the orchestrator
and the workflow wiring without spending tokens.
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from common import dump_json, log, run, write
from policy import ROLE_TOOLS, Policy


@dataclass
class AgentResult:
    ok: bool
    output: dict[str, Any] | None
    cost_usd: float = 0.0
    usage: dict[str, Any] = field(default_factory=dict)
    num_turns: int = 0
    duration_s: float = 0.0
    error: str = ""
    denials: int = 0
    executed_bash: list[str] = field(default_factory=list)
    model: str = ""

    def metrics(self) -> dict[str, Any]:
        return {"ok": self.ok, "cost_usd": round(self.cost_usd, 5), "usage": self.usage,
                "num_turns": self.num_turns, "duration_s": round(self.duration_s, 1),
                "error": self.error, "denials": self.denials, "model": self.model}


class AgentRunner:
    def __init__(self, cfg: dict[str, Any], log_dir: Path, agent_env: dict[str, str],
                 sandbox: bool = True):
        self.cfg = cfg
        self.log_dir = log_dir
        self.agent_env = agent_env
        self.sandbox = sandbox and sys.platform.startswith("linux") and os.environ.get("AUTOSE_SANDBOX", "1") != "0"
        self.fake_dir = os.environ.get("AUTOSE_FAKE")
        self.total_cost = 0.0
        self.calls: list[dict[str, Any]] = []

    def run(self, role: str, label: str, system: str, prompt: str, schema: dict[str, Any],
            policy: Policy) -> AgentResult:
        model = self.cfg["models"][role]
        t0 = time.time()
        if self.fake_dir:
            res = self._fake(label, policy)
        else:
            lim = self.cfg["limits"][role]
            try:
                res = asyncio.run(asyncio.wait_for(
                    self._query(role, label, system, prompt, schema, policy, model, lim),
                    timeout=lim["timeout_s"]))
            except asyncio.TimeoutError:
                res = AgentResult(False, None, error=f"wall-clock timeout after {lim['timeout_s']}s")
            except Exception as exc:  # SDK/CLI errors become a failed stage, not a crash
                res = AgentResult(False, None, error=f"{type(exc).__name__}: {exc}")
        res.duration_s = time.time() - t0
        res.denials = len(policy.denials)
        res.executed_bash = policy.executed_bash()
        res.model = model
        self.total_cost += res.cost_usd
        rec = {"label": label, "role": role, **res.metrics()}
        self.calls.append(rec)
        dump_json(self.log_dir / f"{label}.metrics.json", {**rec, "tool_calls": policy.calls})
        write(self.log_dir / f"{label}.prompt.md", f"# system\n\n{system}\n\n# user\n\n{prompt}\n")
        log(f"agent {label} ({model}): ok={res.ok} cost=${res.cost_usd:.3f} turns={res.num_turns} "
            f"denials={res.denials} {res.error}")
        return res

    async def _query(self, role, label, system, prompt, schema, policy, model, lim) -> AgentResult:
        from claude_agent_sdk import (AssistantMessage, ClaudeAgentOptions, HookMatcher, ResultMessage,
                                      TextBlock, ToolResultBlock, ToolUseBlock, UserMessage, query)
        sandbox = None
        if self.sandbox and "Bash" in ROLE_TOOLS[role]:
            sandbox = {"enabled": True, "autoAllowBashIfSandboxed": False,
                       "allowUnsandboxedCommands": False, "network": {"allowedDomains": []}}
        stderr_lines: list[str] = []
        options = ClaudeAgentOptions(
            tools=ROLE_TOOLS[role],
            allowed_tools=[],
            system_prompt={"type": "preset", "preset": "claude_code", "append": system,
                           "exclude_dynamic_sections": True},
            model=model,
            effort=self.cfg["effort"][role],
            max_turns=lim["max_turns"],
            max_budget_usd=lim["max_usd"],
            cwd=str(policy.workdir),
            setting_sources=[],
            permission_mode="dontAsk",
            hooks={"PreToolUse": [HookMatcher(matcher=None, hooks=[policy.hook()], on_failure="block")]},
            output_format={"type": "json_schema", "schema": schema},
            env={**self.agent_env, "DISABLE_TELEMETRY": "1", "DISABLE_ERROR_REPORTING": "1",
                 "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1", "DISABLE_AUTOUPDATER": "1"},
            sandbox=sandbox,
            stderr=lambda line: stderr_lines.append(line),
        )
        transcript: list[dict[str, Any]] = []
        md: list[str] = [f"# transcript: {label} ({model})\n"]
        result: ResultMessage | None = None
        async for msg in query(prompt=prompt, options=options):
            if isinstance(msg, AssistantMessage):
                for b in msg.content:
                    if isinstance(b, TextBlock):
                        transcript.append({"type": "text", "text": b.text})
                        md.append(b.text + "\n")
                    elif isinstance(b, ToolUseBlock):
                        transcript.append({"type": "tool_use", "name": b.name, "input": b.input})
                        md.append(f"**→ {b.name}** `{json.dumps(b.input)[:400]}`\n")
            elif isinstance(msg, UserMessage) and isinstance(msg.content, list):
                for b in msg.content:
                    if isinstance(b, ToolResultBlock):
                        txt = b.content if isinstance(b.content, str) else json.dumps(b.content)
                        transcript.append({"type": "tool_result", "is_error": b.is_error, "content": (txt or "")[:4000]})
                        md.append(f"<details><summary>result{' (error)' if b.is_error else ''}</summary>\n\n"
                                  f"```\n{(txt or '')[:1500]}\n```\n</details>\n")
            elif isinstance(msg, ResultMessage):
                result = msg
        write(self.log_dir / f"{label}.transcript.md", "\n".join(md))
        dump_json(self.log_dir / f"{label}.transcript.json", transcript)
        if stderr_lines:
            write(self.log_dir / f"{label}.stderr.txt", "\n".join(stderr_lines[-200:]))
        if result is None:
            return AgentResult(False, None, error="no result message")
        out = result.structured_output
        if isinstance(out, str):
            try:
                out = json.loads(out)
            except json.JSONDecodeError:
                out = None
        ok = (not result.is_error) and isinstance(out, dict)
        return AgentResult(ok, out if isinstance(out, dict) else None,
                           cost_usd=result.total_cost_usd or 0.0, usage=result.usage or {},
                           num_turns=result.num_turns,
                           error="" if ok else f"{result.subtype}: {result.errors or result.result or ''}"[:500])

    def _fake(self, label: str, policy: Policy) -> AgentResult:
        d = Path(self.fake_dir)
        # A fake answer may be specific to an attempt (label) or shared by role prefix.
        base = label.split(".")[0]
        for name in (label, base):
            patch = d / f"{name}.patch"
            if patch.exists():
                run(["git", "apply", "--whitespace=nowarn", str(patch)], cwd=policy.workdir, check=True)
                break
        for name in (label, base):
            f = d / f"{name}.json"
            if f.exists():
                return AgentResult(True, json.loads(f.read_text(encoding="utf-8")), cost_usd=0.0, num_turns=1)
        return AgentResult(False, None, error=f"no fake answer for {label}")
