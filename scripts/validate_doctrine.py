#!/usr/bin/env python3
"""Fail-closed checks for canonical project doctrine and pointer continuity."""
from pathlib import Path
import ast
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = (
    "AGENTS.md", "docs/DOCTRINE.md", "docs/LEDGER.md",
    "docs/ROADMAP.md", "docs/PRIOR_ART.md", "docs/VALIDATION.md",
    "docs/STRATEGY.md", "plans/active/BI-001.md", "plans/active/BI-002.md",
    "docs/COMPATIBILITY.md", "docs/LIVE_CERT.md", "plans/active/BI-002.execution.v1.json",
    "compatibility/catalog.v1.json", "betterinstincts/compatibility.py", "betterinstincts/live_eval.py",
    "scripts/live_cert.py", "scripts/check_backward_compat.py",
    "scripts/tuning_audit.py", "scripts/compatibility_status.py",
    ".cursor/rules/betterinstincts-compatibility.mdc",
    ".github/CODEOWNERS", "docs/MAINTAINER_REVIEW.md",
    "betterinstincts/priority.py", "tests/test_priority.py",
    "docs/PROMPT_INVOCATIONS.md", "scripts/check_tracked_assets.py",
    ".github/workflows/ci.yml",
)
MARKERS = (
    "docs/DOCTRINE.md", "docs/LEDGER.md", "plans/active/BI-001.md", "plans/active/BI-002.md",
    "Player first", "Save-safe", "Storage", "Performance",
    "Evidence", "Continuity", "CHANGED | PROVED | NEXT",
    "docs/COMPATIBILITY.md", "docs/LIVE_CERT.md", "BLOCKED_LOCAL_GAME_ACCESS",
)
class DoctrineViolation(Exception):
    pass

def validate(root=ROOT):
    missing = [name for name in REQUIRED if not (root / name).is_file()]
    if missing:
        raise DoctrineViolation("MISSING_CANONICAL_PATH:" + ",".join(missing))
    content = (root / "AGENTS.md").read_text(encoding="utf-8")
    for marker in MARKERS:
        if marker not in content:
            raise DoctrineViolation("GOVERNANCE_GAP:" + marker)
    if len(content) > 3600:
        raise DoctrineViolation("ALWAYS_ON_GOVERNANCE_BUDGET")
    ledger = (root / "docs/LEDGER.md").read_text(encoding="utf-8")
    if "income" not in ledger or "career" not in ledger or "UNPROVEN" not in ledger:
        raise DoctrineViolation("PARENT_OR_PROOF_LOST")
    doctrine = (root / "docs/DOCTRINE.md").read_text(encoding="utf-8")
    for word in ("explicit, user-selected Mods root", "disposable", "distribution"):
        if word not in doctrine:
            raise DoctrineViolation("SAFETY_DOCTRINE_LOST:" + word)
    # Fail closed if the deliberately pure, offline policy starts depending on game,
    # network, filesystem, or process APIs without an explicit integration gate.
    source = (root / "betterinstincts/priority.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    disallowed = {"sims", "sims4", "os", "pathlib", "subprocess", "socket", "requests", "urllib"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            mods = [alias.name.split(".")[0] for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            mods = [(node.module or "").split(".")[0]]
        else:
            mods = []
        if any(name in disallowed for name in mods):
            raise DoctrineViolation("OFFLINE_POLICY_IO_IMPORT")
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in {"open", "exec", "eval", "__import__"}:
            raise DoctrineViolation("OFFLINE_POLICY_IO_CALL")
    lab = (root / "plans/active/BI-002.md").read_text(encoding="utf-8")
    if "BI-002 cannot be CLOSED" not in lab or "scripts.live_cert status" not in lab:
        raise DoctrineViolation("LOCAL_GAME_GATE_LOST")
    if "CLOSED" in lab.splitlines()[0].upper():
        from betterinstincts.compatibility import load_catalog
        catalog = load_catalog(root)
        if not any(r.get("module") == "hunger" and r.get("status") == "certified" for r in catalog["profiles"]):
            raise DoctrineViolation("HUNGER_SPRINT_CLOSURE_WITHOUT_GAME_CERT")
    manifest = json.loads((root / "plans/active/BI-002.execution.v1.json").read_text(encoding="utf-8"))
    required = ["actual_reversible_package", "five_vanilla_trials", "five_modified_trials",
                "rollback_smoke", "measured_behavior_improvement", "player_queue_safety", "maintainer_review"]
    if manifest.get("parent_gate") != "HUNGER_LIVE_CERTIFIED" or manifest.get("closure_requires") != required:
        raise DoctrineViolation("PARENT_GAME_GATE_REDEFINED")
    if manifest.get("parent_on_block") != "ACTIVE" or manifest.get("blocked_state") != "BLOCKED_LOCAL_GAME_ACCESS":
        raise DoctrineViolation("BLOCKED_WORK_FALSE_COMPLETION")
    return {"state": "PASS", "root": "AGENTS.md", "required_files": len(REQUIRED),
            "proof_ceiling": "tracked governance content only; no live Sims validation"}

if __name__ == "__main__":
    try:
        print(json.dumps(validate(), sort_keys=True))
    except (DoctrineViolation, OSError) as exc:
        print("DOCTRINE_BLOCKED: " + str(exc), file=sys.stderr)
        sys.exit(2)
