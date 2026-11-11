"""Verify P01 navigation contract, semantic owners and fail-closed canary."""
from __future__ import annotations

import json
from pathlib import Path

from betterinstincts.household_navigation import plan_household_navigation

ROOT = Path(__file__).resolve().parents[1]


def check() -> None:
    cfg = json.loads((ROOT / "contracts/household-navigation.v1.json").read_text(encoding="utf-8"))
    ontology = json.loads((ROOT / "contracts/ontology.v1.json").read_text(encoding="utf-8"))
    assert cfg["schema"] == "betterinstincts.household-navigation/v1"
    assert cfg["ontology_revision"] <= ontology["revision"]
    for key in cfg["concepts"]:
        assert key in ontology["concepts"], key
        assert ontology["concepts"][key]["canonical_owner"] == "contracts/household-navigation.v1.json"
    invariants = {x["id"] for x in ontology["invariants"]}
    assert {f"BI-ONT-{n:03d}" for n in range(36, 42)}.issubset(invariants)
    for path in ("betterinstincts/household_navigation.py",
                 "betterinstincts/room_map_traverse.py",
                 "tests/test_household_navigation.py",
                 "docs/HOUSEHOLD_NAVIGATION.md"):
        assert (ROOT / path).is_file(), path
    assert cfg["safety"]["visual_graph_is_not_route_graph"] is True
    assert cfg["safety"]["actual_game_certification"] == "UNPROVEN"
    assert "plan_semantic_region_route" in (ROOT / "betterinstincts/room_map_traverse.py").read_text()
    result = plan_household_navigation({})
    assert result["control_permit"] is None
    assert result["effects_issued"] == 0
    assert result["execute_allowed"] is False


if __name__ == "__main__":
    check()
    print("HOUSEHOLD_NAVIGATION_OFFLINE_CONTRACT_PASS_NOT_GAME_CERTIFICATION")
