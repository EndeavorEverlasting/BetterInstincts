"""P00/P01 hard gate: scene graph, save classification and host boundaries."""
from __future__ import annotations

import json
from pathlib import Path
import sys

from betterinstincts.scenes import load_catalog, SceneError
from betterinstincts.save_policy import load_policy, SavePolicyError

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = (
    "AGENTS.md", "docs/SCENE_INTELLIGENCE.md",
    "contracts/game-scenes.v1.json", "contracts/save-policy.v1.json",
    "scripts/game_host.py", "scripts/scene_map.py", "scripts/save_guard.py",
    "tests/test_scene_map.py", "tests/test_save_policy.py", "tests/test_game_host_save_guard.py",
)


class SceneContractError(ValueError):
    pass


def check(root: Path = ROOT) -> dict:
    root = Path(root)
    missing = [name for name in REQUIRED if not (root / name).is_file()]
    if missing:
        raise SceneContractError("MISSING_SCENE_CONTRACT:" + ",".join(missing))
    catalog = load_catalog(root / "contracts/game-scenes.v1.json")
    policy = load_policy(root / "contracts/save-policy.v1.json")
    host = (root / "scripts/game_host.py").read_text(encoding="utf-8")
    agent = (root / "AGENTS.md").read_text(encoding="utf-8")
    if "selected_save_guard(cfg, run_id)" not in host or "SAVE_SELECTION_PROTECTED" not in host:
        raise SceneContractError("GAME_HOST_SAVE_SELECTION_NOT_GUARDED")
    if "Unknown/user saves" not in agent or "docs/SCENE_INTELLIGENCE.md" not in agent:
        raise SceneContractError("AGENT_SCENE_SAVE_GOVERNANCE_MISSING")
    if len(catalog["scenes"]) < 30 or policy["default_classification"] != "UNKNOWN_PROTECTED":
        raise SceneContractError("SCENE_COVERAGE_OR_SAVE_DEFAULT_WEAKENED")
    return {"state": "PASS", "scenes": len(catalog["scenes"]), "default_save": "UNKNOWN_PROTECTED",
            "proof_ceiling": "OFFLINE_CONTRACT_NOT_LIVE_SCREEN_RECOGNITION"}


def main() -> int:
    try:
        print(json.dumps(check(), sort_keys=True))
    except (SceneError, SavePolicyError, SceneContractError, OSError, ValueError, TypeError) as exc:
        print(json.dumps({"state": "BLOCKED", "reason": str(exc)}, sort_keys=True))
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
