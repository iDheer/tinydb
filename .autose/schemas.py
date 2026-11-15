"""JSON schemas for structured agent output (ADR-003). Small on purpose."""

S = {"type": "string"}
SA = {"type": "array", "items": S}


def obj(props: dict, required: list[str] | None = None) -> dict:
    return {"type": "object", "properties": props,
            "required": required if required is not None else list(props),
            "additionalProperties": False}


def enum(*vals: str) -> dict:
    return {"type": "string", "enum": list(vals)}


AC = obj({"id": S, "given": S, "when": S, "then": S})

SPEC = obj({
    "title": S,
    "summary": S,
    "verdict": enum("READY", "READY-WITH-OPEN-ITEMS", "DRAFT"),
    "requirements": {"type": "array", "items": obj({
        "id": S,
        "kind": enum("FR", "NFR", "CON"),
        "statement": S,
        "source": enum("STATED", "CONFIRMED", "DERIVED", "EVIDENCED", "ASSUMED"),
        "source_quote": S,
        "priority": enum("MUST", "SHOULD", "COULD", "UNSET"),
        "status": enum("READY", "BLOCKED", "NEEDS-CLARIFICATION", "ASSUMPTION-ONLY"),
        "acceptance_criteria": {"type": "array", "items": AC},
        "links": SA,
    })},
    "terms": {"type": "array", "items": obj({"id": S, "term": S, "interpretations": SA})},
    "open_questions": {"type": "array", "items": obj({
        "id": S, "priority": enum("P1", "P2", "P3"), "question": S, "why_it_matters": S,
        "options": SA, "proposed_default": S, "blocks": SA})},
    "assumptions": {"type": "array", "items": obj({"id": S, "text": S, "risk_if_wrong": S})},
    "out_of_scope": SA,
})

JUDGE = obj({"criteria": {"type": "array", "items": obj({
    "id": S, "testable": {"type": "boolean"}, "reason": S})}})

DESIGN = obj({
    "summary": S,
    "approach": S,
    "alternatives": {"type": "array", "items": obj({"option": S, "why_not": S})},
    "files": {"type": "array", "items": obj({
        "path": S,
        "change": enum("modify", "create"),
        "purpose": S,
        "symbols": {"type": "array", "items": obj({
            "name": S,
            "kind": enum("function", "class", "method", "constant"),
            "change": enum("modify", "create"),
            "description": S})},
    })},
    "ac_mapping": {"type": "array", "items": obj({"ac_id": S, "symbols": SA, "test_idea": S})},
    "constraints": {"type": "array", "items": obj({"id": S, "how_respected": S})},
    "risks": SA,
})

IMPLEMENT = obj({
    "status": enum("done", "design_gap", "test_dispute", "blocked"),
    "summary": S,
    "changed_files": SA,
    "design_gap": S,
    "disputed_tests": {"type": "array", "items": obj({"test": S, "reason": S})},
})

TEST = obj({
    "status": enum("done", "blocked"),
    "tests": {"type": "array", "items": obj({"name": S, "ac_id": S})},
    "notes": S,
    "suspected_bugs": SA,
})

REVIEW = obj({
    "issue_requirements": SA,
    "requirement_checks": {"type": "array", "items": obj({
        "requirement": S, "met": enum("yes", "no", "partly"), "evidence": S})},
    "findings": {"type": "array", "items": obj({
        "severity": enum("blocker", "major", "minor", "nit"),
        "category": enum("approach", "code", "tests", "scope"),
        "file": S, "line": {"type": "integer"}, "description": S, "evidence": S,
        "suggested_fix": S})},
    "checks_run": {"type": "array", "items": obj({"command": S, "result": S})},
    "risks_considered": SA,
    "verdict": enum("approve", "request_changes"),
    "route": enum("none", "design", "implement"),
    "summary": S,
})
