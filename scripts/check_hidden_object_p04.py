"""CI guard: P04 cannot silently lose the exact hidden-object operator guide.

This validates contract/routes/docs and never launches or certifies The Sims.
"""
from __future__ import annotations

import json
from pathlib import Path

from betterinstincts.hidden_object_discovery import ROOT, p04_guide, load_contract

ORDER = (
    "OPEN_CHEAT_CONSOLE", "ENABLE_CHEATS", "REVEAL_HIDDEN_OBJECTS",
    "ENTER_BUILD_BUY", "SELECT_DEBUG_RESULTS",
)
GUIDE_COMMAND = "python -m scripts.hidden_object_discovery guide"
AUDIT_COMMAND = (
    "python -m scripts.hidden_object_discovery audit "
    "--observation dist/game-host/hidden-object-p04-receipt.json"
)
HANDOFF = "plans/active/BI-HIDDEN-OBJECTS.P04.md"
DISPATCH = "plans/active/BI-HIDDEN-OBJECTS.dispatch.v1.json"


def verify(root: Path = ROOT) -> dict:
    cfg = load_contract(root / "contracts/hidden-object-discovery.v1.json")
    guide = p04_guide(cfg=cfg)
    book = cfg["operator_playbook"]
    if [x["step_id"] for x in guide["steps"]] != list(ORDER):
        raise ValueError("P04_STEP_ORDER_NOT_CANONICAL")
    if book.get("must_read_from_cli") != GUIDE_COMMAND:
        raise ValueError("P04_CLI_GUIDE_NOT_ROUTED")
    if book.get("completion_audit") != AUDIT_COMMAND:
        raise ValueError("P04_AUDIT_NOT_ROUTED")
    if guide["steps"][3].get("keyboard_shortcut_hint", "").split(" ")[0] != "F2":
        raise ValueError("P04_F2_HINT_MISSING")
    if not any("upper-left" in x for x in guide["steps"][0]["expected_ui_cues"]):
        raise ValueError("P04_CONSOLE_UI_CUE_MISSING")
    if not any("bottom-left" in x for x in [guide["steps"][4].get("search_location_hint", "")]):
        raise ValueError("P04_DEBUG_SEARCH_REGION_MISSING")
    if guide["steps"][4]["search_term"] != "debug":
        raise ValueError("P04_DEBUG_SEARCH_MISSING")
    if not guide["steps"][2]["optional_requires_explicit_opt_in"]:
        raise ValueError("P04_LIVE_EDIT_OPT_IN_LOST")
    if guide["host_action_authorized"]:
        raise ValueError("P04_UNSAFE_HOST_AUTHORITY")

    required_text = {
        # The root is intentionally compact; it MUST route to its mandatory
        # detailed owner, where the P04 workflow and commands are preserved.
        "AGENTS.md": ["docs/AGENT_OPERATING_RULES.md"],
        "docs/AGENT_OPERATING_RULES.md": [
            "## P04 hidden-object discovery", GUIDE_COMMAND, AUDIT_COMMAND, HANDOFF,
        ],
        HANDOFF: [GUIDE_COMMAND, AUDIT_COMMAND, *ORDER,
                  "Ctrl+Shift+C", "testingcheats true", "bb.showhiddenobjects",
                  "bb.showliveeditobjects", "F2", "DEBUG"],
        "docs/HIDDEN_OBJECT_DISCOVERY.md": [GUIDE_COMMAND, AUDIT_COMMAND, "P04_EVIDENCE_INCOMPLETE", "SELECT_DEBUG_RESULTS"],
        "scripts/hidden_object_discovery.py": ['commands.add_parser("guide"', 'commands.add_parser("audit"', "p04_guide()", "audit_p04_receipt("],
        "tests/test_hidden_object_discovery.py": ["P04OperatorGuideTests", "test_audit_rejects_skipped_reordered_or_forged_generic_steps", "test_p04_guide_always_exposes_five_user_steps_and_platforms"],
    }
    for filename, required in required_text.items():
        path = root / filename
        if not path.is_file():
            raise ValueError("P04_REQUIRED_FILE_MISSING:" + filename)
        contents = path.read_text(encoding="utf-8")
        for fragment in required:
            if fragment not in contents:
                raise ValueError("P04_ROUTE_OR_STEP_MISSING:" + filename + ":" + fragment)
    manifest = json.loads((root / DISPATCH).read_text(encoding="utf-8"))
    ingest = manifest.get("p04_required_ingest") or {}
    if ingest.get("required_step_ids") != list(ORDER):
        raise ValueError("P04_MACHINE_DISPATCH_SEQUENCE_MISSING")
    if ingest.get("guide_command") != GUIDE_COMMAND or ingest.get("audit_command") != AUDIT_COMMAND:
        raise ValueError("P04_MACHINE_DISPATCH_ENTRYPOINT_MISSING")
    if manifest.get("safety", {}).get("never_sendinput_from_planner") is not True:
        raise ValueError("P04_UNSAFE_DISPATCH")
    for lane_id in ("WINDOWS_SCENE", "WINDOWS_CATALOG", "CI_PROOF"):
        if not any(lane.get("lane_id") == lane_id for lane in manifest.get("lanes") or []):
            raise ValueError("P04_LANE_MISSING:" + lane_id)
    return {
        "status": "P04_PLAYBOOK_ROUTE_AND_SEQUENCE_PASS_NOT_GAME_PROOF",
        "step_ids": list(ORDER),
        "guide_command": GUIDE_COMMAND,
        "audit_command": AUDIT_COMMAND,
        "game_input_observed": False,
    }


def main() -> int:
    try:
        print(json.dumps(verify(), sort_keys=True))
        return 0
    except (ValueError, OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print("P04_PLAYBOOK_ROUTE_FAIL " + str(exc))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
