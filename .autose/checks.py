"""Deterministic stage checks (ADR-007). The orchestrator alone calls these and decides."""
from __future__ import annotations

import ast
import re
import shutil
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from common import run, run_isolated

# Subset of the A1 skill's Appendix A list that never belongs in an observable criterion.
VAGUE = ["fast", "quick", "quickly", "real-time", "instant", "instantly", "scalable", "user-friendly",
         "intuitive", "seamless", "seamlessly", "efficient", "efficiently", "optimal", "robust",
         "lightweight", "as needed", "etc", "and so on", "soon", "properly", "correctly", "appropriate",
         "appropriately", "reasonable", "better", "nicer", "easier"]
_VAGUE_RE = re.compile(r"(?<![\w-])(" + "|".join(re.escape(v) for v in VAGUE) + r")(?![\w-])", re.I)


def result(passed: bool, reasons: list[str], **details: Any) -> dict[str, Any]:
    return {"passed": passed, "reasons": reasons, "details": details}


def ac_slug(ac_id: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", ac_id.lower()).strip("_")


def core_acs(spec: dict[str, Any]) -> list[dict[str, Any]]:
    return [ac for r in spec.get("requirements", []) if r.get("priority") in ("MUST", "SHOULD")
            and r.get("status") == "READY" for ac in r.get("acceptance_criteria", [])]


# -- stage 1 ---------------------------------------------------------------------------
def check_spec(spec: dict[str, Any], judge: dict[str, Any] | None) -> dict[str, Any]:
    reasons: list[str] = []
    reqs = spec.get("requirements", [])
    core = [r for r in reqs if r.get("priority") in ("MUST", "SHOULD")]
    p1 = [q for q in spec.get("open_questions", []) if q.get("priority") == "P1"]
    needs_info = False
    if spec.get("verdict") == "DRAFT":
        reasons.append("spec verdict is DRAFT (the issue does not yet define what to build)")
        needs_info = True
    if p1:
        reasons.append("open P1 questions: " + ", ".join(q["id"] for q in p1))
        needs_info = True
    if not any(r.get("status") == "READY" for r in core):
        reasons.append("no READY MUST/SHOULD requirement")
        needs_info = True
    for r in core:
        if r.get("status") != "READY":
            reasons.append(f"{r['id']} is {r.get('status')} (core requirements must be READY)")
            needs_info = True
        if not r.get("acceptance_criteria"):
            reasons.append(f"{r['id']} has no acceptance criterion")
        for ac in r.get("acceptance_criteria", []):
            for part in ("given", "when", "then"):
                if not (ac.get(part) or "").strip():
                    reasons.append(f"{ac['id']}: empty '{part}'")
            text = " ".join(ac.get(p, "") for p in ("given", "when", "then"))
            if "<TBD" in text:
                reasons.append(f"{ac['id']}: contains a <TBD> placeholder")
            m = _VAGUE_RE.search(text)
            if m:
                reasons.append(f"{ac['id']}: vague term '{m.group(1)}'")
    ids = [ac["id"] for ac in core_acs(spec)]
    if len(ids) != len(set(ids)):
        reasons.append("duplicate acceptance-criterion ids")
    if judge is not None:
        verdicts = {c["id"]: c for c in judge.get("criteria", [])}
        for i in ids:
            c = verdicts.get(i)
            if c is None:
                reasons.append(f"{i}: testability judge gave no verdict")
            elif not c["testable"]:
                reasons.append(f"{i}: judge says not testable: {c['reason']}")
    return result(not reasons, reasons, needs_info=needs_info, ac_ids=ids)


# -- stage 2 ---------------------------------------------------------------------------
def _symbols(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
        if isinstance(node, ast.ClassDef):
            for sub in node.body:
                if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    names.add(f"{node.name}.{sub.name}")
                elif isinstance(sub, ast.Assign):
                    names |= {f"{node.name}.{t.id}" for t in sub.targets if isinstance(t, ast.Name)}
        if isinstance(node, ast.Assign):
            names |= {t.id for t in node.targets if isinstance(t, ast.Name)}
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names.add(node.target.id)
    return names


def check_design(design: dict[str, Any], spec: dict[str, Any], workdir: Path, test_file: str) -> dict[str, Any]:
    reasons: list[str] = []
    files = design.get("files", [])
    src = [f for f in files if not f["path"].startswith("tests/")]
    if not src:
        reasons.append("design names no source file to change")
    if not any(f.get("symbols") for f in src):
        reasons.append("design names no function, class or method")
    for f in files:
        p = workdir / f["path"]
        if f["path"].startswith((".github/", ".autose/", ".git/")) or ".." in f["path"]:
            reasons.append(f"{f['path']}: protected or invalid path")
            continue
        if f["change"] == "modify" and not p.is_file():
            reasons.append(f"{f['path']}: marked modify but does not exist")
            continue
        if f["change"] == "create" and p.exists() and f["path"] != test_file:
            reasons.append(f"{f['path']}: marked create but already exists")
        if f["change"] == "modify" and p.suffix == ".py":
            try:
                have = _symbols(p)
            except SyntaxError as exc:
                reasons.append(f"{f['path']}: cannot parse ({exc})")
                continue
            for s in f.get("symbols", []):
                if s["change"] == "modify" and s["name"] not in have:
                    reasons.append(f"{f['path']}: symbol {s['name']} (modify) not found")
                if s["change"] == "create" and s["name"] in have:
                    reasons.append(f"{f['path']}: symbol {s['name']} (create) already exists")
    mapped = {m["ac_id"] for m in design.get("ac_mapping", []) if m.get("symbols") and m.get("test_idea")}
    for ac in core_acs(spec):
        if ac["id"] not in mapped:
            reasons.append(f"{ac['id']} not mapped to code and a test idea")
    return result(not reasons, reasons)


def design_writable(design: dict[str, Any]) -> set[str]:
    return {f["path"] for f in design.get("files", []) if not f["path"].startswith("tests/")}


# -- stage 3 ---------------------------------------------------------------------------
def changed_files(workdir: Path, base: str) -> list[str]:
    tracked = run(["git", "diff", "--name-only", base], cwd=workdir).stdout.split()
    untracked = run(["git", "ls-files", "--others", "--exclude-standard"], cwd=workdir).stdout.split()
    return sorted(set(tracked) | set(untracked))


def check_impl(workdir: Path, base: str, allowed: set[str], test_file: str) -> dict[str, Any]:
    reasons: list[str] = []
    files = changed_files(workdir, base)
    src_changes = [f for f in files if f != test_file]
    if not src_changes:
        reasons.append("no source change (empty diff)")
    extra = [f for f in src_changes if f not in allowed]
    if extra:
        reasons.append("changed files not declared in design.md: " + ", ".join(extra))
    py = sys.executable
    p = run_isolated([py, "-m", "compileall", "-q", "tinydb"], cwd=workdir, timeout=120)
    if p.returncode != 0:
        reasons.append("compileall failed:\n" + (p.stdout + p.stderr)[-1500:])
    p = run_isolated([py, "-c", "import tinydb, tinydb.operations, tinydb.middlewares"], cwd=workdir, timeout=60)
    if p.returncode != 0:
        reasons.append("import tinydb failed:\n" + (p.stdout + p.stderr)[-1500:])
    mypy_out = ""
    if shutil.which("mypy") or run([py, "-c", "import mypy"]).returncode == 0:
        p = run_isolated([py, "-m", "mypy", "tinydb"], cwd=workdir, timeout=300)
        mypy_out = (p.stdout + p.stderr)[-1500:]
        if p.returncode != 0:
            reasons.append("mypy tinydb failed:\n" + mypy_out)
    return result(not reasons, reasons, changed=files, mypy=mypy_out)


# -- stage 4 ---------------------------------------------------------------------------
def _junit(path: Path) -> dict[str, Any]:
    out = {"passed": 0, "failed": 0, "errors": 0, "skipped": 0, "cases": [], "failures": []}
    if not path.exists():
        out["errors"] = 1
        out["failures"].append("(no junit report: collection or startup failure)")
        return out
    root = ET.parse(path).getroot()
    for tc in root.iter("testcase"):
        name = tc.get("name", "")
        full = f"{tc.get('classname', '')}::{name}"
        if tc.find("failure") is not None:
            out["failed"] += 1
            out["failures"].append(full)
            state = "failed"
        elif tc.find("error") is not None:
            out["errors"] += 1
            out["failures"].append(full)
            state = "error"
        elif tc.find("skipped") is not None:
            out["skipped"] += 1
            state = "skipped"
        else:
            out["passed"] += 1
            state = "passed"
        out["cases"].append({"name": name, "classname": tc.get("classname", ""), "state": state})
    for ts in root.iter("testsuite"):  # collection errors show up only as suite errors
        if int(ts.get("errors", 0)) > out["errors"]:
            out["errors"] = int(ts.get("errors", 0))
    return out


def run_pytest(workdir: Path, args: list[str], tag: str) -> tuple[dict[str, Any], str]:
    xml = Path(tempfile.gettempdir()) / f"autose-{tag}-{abs(hash(str(workdir)))}.xml"
    xml.unlink(missing_ok=True)
    p = run_isolated([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "--no-cov",
                      f"--junitxml={xml}", *args], cwd=workdir, timeout=900)
    return _junit(xml), (p.stdout + p.stderr)[-6000:]


def check_tests(workdir: Path, base: str, spec: dict[str, Any], test_file: str) -> dict[str, Any]:
    reasons: list[str] = []
    if not (workdir / test_file).is_file():
        return result(False, [f"{test_file} was not written"], test_file=test_file, kind="coverage")
    suite, out = run_pytest(workdir, [], "suite")
    new = [c for c in suite["cases"] if c["classname"].endswith(Path(test_file).stem)]
    coverage = {}
    for ac in core_acs(spec):
        slug = ac_slug(ac["id"])
        coverage[ac["id"]] = [c["name"] for c in new if c["name"].startswith(f"test_{slug}")]
    kind = "pass"
    failing_new = [f for f in suite["failures"] if Path(test_file).stem in f]
    failing_old = [f for f in suite["failures"] if Path(test_file).stem not in f]
    if suite["failed"] or suite["errors"]:
        reasons.append(f"suite: {suite['failed']} failed, {suite['errors']} errors "
                       f"({len(failing_new)} new, {len(failing_old)} existing)")
        kind = "failures"
    missing = [ac for ac, ts in coverage.items() if not ts]
    if missing:
        reasons.append("acceptance criteria without a test named test_<ac>: " + ", ".join(missing))
        kind = "coverage" if kind == "pass" else kind
    fail_before = _fail_before(workdir, base, test_file)
    if fail_before["total"] and fail_before["failed"] == 0:
        reasons.append("every new test also passes on the base commit, so the tests do not exercise the change")
        kind = "coverage" if kind == "pass" else kind
    return result(not reasons, reasons, suite={k: suite[k] for k in ("passed", "failed", "errors", "skipped")},
                  failures=suite["failures"], failing_new=failing_new, failing_old=failing_old,
                  new_tests=[c["name"] for c in new], coverage=coverage, fail_before=fail_before,
                  output_tail=out[-4000:], test_file=test_file, kind=kind)


def _fail_before(workdir: Path, base: str, test_file: str) -> dict[str, Any]:
    tmp = Path(tempfile.mkdtemp(prefix="autose-base-"))
    try:
        run(["git", "worktree", "add", "--detach", str(tmp / "wt"), base], cwd=workdir, check=True)
        dst = tmp / "wt" / test_file
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(workdir / test_file, dst)
        res, _ = run_pytest(tmp / "wt", [test_file], "base")
        total = max(len(res["cases"]), res["errors"])
        return {"total": total, "failed": res["failed"] + res["errors"]}
    finally:
        run(["git", "worktree", "remove", "--force", str(tmp / "wt")], cwd=workdir)
        shutil.rmtree(tmp, ignore_errors=True)


# -- stage 5 ---------------------------------------------------------------------------
SECRET_PATTERNS = re.compile(r"(sk-ant-[A-Za-z0-9_-]{8,}|ghp_[A-Za-z0-9]{20,}|ghs_[A-Za-z0-9]{20,}|"
                             r"github_pat_[A-Za-z0-9_]{20,}|gho_[A-Za-z0-9]{20,})")


def secret_scan(diff_text: str, known: list[str]) -> list[str]:
    hits = [m.group(0)[:12] + "…" for m in SECRET_PATTERNS.finditer(diff_text)
            if "autose-dummy" not in m.group(0)]
    hits += ["<known secret value>" for v in known if v and v in diff_text]
    return hits
