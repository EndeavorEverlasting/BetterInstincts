#!/usr/bin/env python3
"""Fail-closed checks for canonical project doctrine and pointer continuity."""
from pathlib import Path
import ast
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
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
    "docs/HORIZON.md", "docs/HORIZON_DECISIONS.md", "plans/horizon.v1.json",
    "plans/active/BI-003.execution.v1.json", "contracts/needs.v1.json",
    "betterinstincts/horizon.py", "scripts/eval_horizon.py",
    "scripts/check_horizon.py", "scripts/horizon_status.py",
    "plans/active/BI-HORIZON.dispatch.v1.json",
    "tests/test_horizon.py", "tests/test_horizon_contract.py", "tests/test_horizon_status.py",
    "docs/SCENE_INTELLIGENCE.md", "contracts/game-scenes.v1.json", "contracts/save-policy.v1.json",
    "betterinstincts/scenes.py", "betterinstincts/save_policy.py",
    "scripts/scene_map.py", "scripts/save_guard.py", "scripts/check_scene_contract.py",
    "tests/test_scene_map.py", "tests/test_save_policy.py", "tests/test_game_host_save_guard.py",
    "contracts/decision-prompts.v1.json", "betterinstincts/decision_eval.py",
    "betterinstincts/host_stack.py", "scripts/decision_eval.py", "tests/test_decision_eval.py",
    "contracts/viewport-black.v1.json", "betterinstincts/viewport.py",
    "scripts/viewport_recover.py", "tests/test_viewport.py",
    "contracts/host-menu.v1.json", "betterinstincts/host_menu.py",
    "betterinstincts/menu_blockers.py", "scripts/host_menu.py",
    "scripts/menu_blockers.py", "tests/test_host_menu.py",
    "contracts/glossary.v1.json", "docs/GLOSSARY.md",
    "contracts/ontology.v1.json", "docs/ONTOLOGY.md",
    "scripts/check_ontology.py", "scripts/semantic_preflight.py",
    "betterinstincts/semantic_advisory.py", "tests/test_semantic_advisory.py",
    "contracts/behavior-matrix.v1.json", "contracts/host-listener.v1.json",
    "contracts/player-presence.v1.json", "contracts/needs-force.v1.json",
    "docs/HOST_AUTONOMY.md",
    "betterinstincts/glossary.py", "betterinstincts/behavior_eval.py",
    "betterinstincts/player_presence.py", "betterinstincts/needs_force.py",
    "betterinstincts/host_listener.py", "betterinstincts/host_automate.py",
    "scripts/host_listener.py", "scripts/needs_force.py", "scripts/host_automate.py",
    "tests/test_host_autonomy.py",
    "contracts/host-funds.v1.json", "betterinstincts/funds_inject.py",
    "scripts/funds_inject.py", "tests/test_funds_inject.py",
    "contracts/progression-eval.v1.json", "docs/PROGRESSION_EVAL.md",
    "betterinstincts/progression_eval.py", "scripts/progression_eval.py",
    "tests/test_progression_eval.py", "tests/fixtures/progression-eval.v1.json",
    "contracts/horizon-continuity.v1.json", "docs/HORIZON_CONTINUITY.md",
    "betterinstincts/horizon_continuity.py", "scripts/check_horizon_continuity.py",
    "tests/test_horizon_continuity.py",
    "contracts/event-balance.v1.json", "docs/EVENT_BALANCE.md",
    "betterinstincts/event_balance.py", "scripts/event_balance.py",
    "tests/test_event_balance.py",
    "contracts/event-goals.v1.json", "docs/EVENT_GOALS.md",
    "betterinstincts/event_goals.py", "scripts/event_goals.py",
    "tests/test_event_goals.py",
    "contracts/moodlets.v1.json", "docs/MOODLETS.md",
    "betterinstincts/moodlets.py", "scripts/moodlets.py",
    "tests/test_moodlets.py",
    "contracts/build-optimize.v1.json", "docs/BUILD_OPTIMIZE.md",
    "betterinstincts/build_optimize.py", "scripts/build_optimize.py",
    "tests/test_build_optimize.py",
    "contracts/school-day.v1.json", "docs/SCHOOL_DAY.md",
    "betterinstincts/school_day.py", "scripts/school_day.py",
    "tests/test_school_day.py",
    "contracts/sim-profile.v1.json", "docs/SIM_PROFILE.md",
    "betterinstincts/sim_profile.py", "scripts/sim_profile.py",
    "tests/test_sim_profile.py",
    "contracts/scenario-goals.v1.json", "docs/SCENARIO_GOALS.md",
    "betterinstincts/scenario_goals.py", "scripts/scenario_goals.py",
    "tests/test_scenario_goals.py",
    "contracts/navigating-needs.v1.json", "docs/NAVIGATING_NEEDS.md",
    "betterinstincts/navigating_needs.py", "scripts/navigating_needs.py",
    "tests/test_navigating_needs.py",
    "contracts/teen-homework.v1.json", "docs/TEEN_HOMEWORK.md",
    "docs/CAREER_PERFORMANCE.md", "docs/TEEN_DAY_JOURNEY.md",
    "betterinstincts/teen_homework.py", "scripts/teen_homework.py",
    "tests/test_teen_homework.py",
    "contracts/social-opportunity.v1.json", "docs/SOCIAL_OPPORTUNITY.md",
    "betterinstincts/social_opportunity.py", "scripts/social_opportunity.py",
    "tests/test_social_opportunity.py",
    "contracts/fun-service.v1.json", "docs/FUN_SERVICE.md",
    "betterinstincts/fun_service.py", "scripts/fun_service.py",
    "tests/test_fun_service.py",
    "contracts/need-services.v1.json", "contracts/need-lanes.v1.json",
    "docs/NEED_SERVICES.md",
    "betterinstincts/need_service_base.py", "betterinstincts/need_services.py",
    "scripts/need_services.py", "tests/test_need_services.py",
    "contracts/need-load-balance.v1.json", "docs/NEED_LOAD_BALANCE.md",
    "betterinstincts/need_load_balance.py", "tests/test_need_load_balance.py",
    "contracts/domain-cascade.v1.json", "docs/DOMAIN_CASCADE.md",
    "betterinstincts/domain_cascade.py", "scripts/domain_cascade.py",
    "tests/test_domain_cascade.py",
    "contracts/curious-catalog.v1.json", "docs/CURIOUS_CATALOG.md",
    "betterinstincts/curious_catalog.py", "scripts/curious_catalog.py",
    "tests/test_curious_catalog.py",
)
MARKERS = (
    "docs/DOCTRINE.md", "docs/LEDGER.md", "plans/active/BI-001.md", "plans/active/BI-002.md",
    "Player first", "Save-safe", "Storage", "Performance",
    "Evidence", "Continuity", "CHANGED | PROVED | NEXT",
    "docs/COMPATIBILITY.md", "docs/LIVE_CERT.md", "BLOCKED_LOCAL_GAME_ACCESS",
    "docs/HORIZON.md", "plans/horizon.v1.json", "six needs",
    "docs/SCENE_INTELLIGENCE.md", "Unknown/user saves",
    "docs/ONTOLOGY.md", "scripts/semantic_preflight.py",
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
    from scripts.check_horizon import validate as check_horizon
    from betterinstincts.horizon import validate_rules
    check_horizon(json.loads((root / "plans/horizon.v1.json").read_text(encoding="utf-8")))
    validate_rules(json.loads((root / "contracts/needs.v1.json").read_text(encoding="utf-8")))
    from scripts.check_scene_contract import check as check_scene_contract
    check_scene_contract(root)
    return {"state": "PASS", "root": "AGENTS.md", "required_files": len(REQUIRED),
            "proof_ceiling": "tracked governance content only; no live Sims validation"}

if __name__ == "__main__":
    try:
        print(json.dumps(validate(), sort_keys=True))
    except (DoctrineViolation, OSError) as exc:
        print("DOCTRINE_BLOCKED: " + str(exc), file=sys.stderr)
        sys.exit(2)
