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
    "betterinstincts/priority.py", "tests/test_priority.py",
    "docs/PROMPT_INVOCATIONS.md", "scripts/check_tracked_assets.py",
    ".github/workflows/ci.yml",
)
MARKERS = (
    "docs/DOCTRINE.md", "docs/LEDGER.md", "plans/active/BI-001.md", "plans/active/BI-002.md",
    "Player first", "Save-safe", "Storage", "Performance",
    "Evidence", "Continuity", "CHANGED | PROVED | NEXT",
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
    return {"state": "PASS", "root": "AGENTS.md", "required_files": len(REQUIRED),
            "proof_ceiling": "tracked governance content only; no live Sims validation"}

if __name__ == "__main__":
    try:
        print(json.dumps(validate(), sort_keys=True))
    except (DoctrineViolation, OSError) as exc:
        print("DOCTRINE_BLOCKED: " + str(exc), file=sys.stderr)
        sys.exit(2)
