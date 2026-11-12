"""P01 VOI harness completeness and fail-closed behavior smoke check."""
from __future__ import annotations

import json
from pathlib import Path

from betterinstincts.traversal_voi import evaluate_traversal_voi

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts/voi-traversal-harness.v1.json"


def check() -> None:
    cfg = json.loads(CONTRACT.read_text(encoding="utf-8"))
    assert cfg["schema"] == "betterinstincts.voi-traversal-harness/v1"
    assert cfg["execute_allowed_default"] is False
    assert cfg["control_permit"] is None
    assert cfg["limits"]["max_host_walks_before_goal_action"] == 1
    assert cfg["walk_contract"]["terminal"].startswith("NEEDS")
    for path in (
        *cfg["owners"].values(),
        cfg["consultation"],
        cfg["harness"]["map"],
        cfg["harness"]["tests"],
        "contracts/native-gameplay-decisions/BI-VOI-PURPOSEFUL-TRAVERSAL-20261112.v1.json",
    ):
        assert (ROOT / path).is_file(), path
    result = evaluate_traversal_voi({}, goal={})
    assert result["execute_allowed"] is False
    assert result["control_permit"] is None
    assert result["sim"]["walk_candidate"] is False


if __name__ == "__main__":
    check()
    print("VOI_PURPOSEFUL_TRAVERSAL_OFFLINE_HARNESS_PASS_NOT_GAME_CERT")
