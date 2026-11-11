"""P00/P01 static world traversal ontology/harness completeness gate.

This is a read-only repository validator. No game process, screenshots,
local profile, user save, mouse input or desktop service is inspected.
"""
from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path, PurePosixPath
from typing import Any

from scripts.check_horizon import validate as validate_horizon
from scripts.check_horizon import validate_dispatch

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = "contracts/world-traversal-harness.v1.json"
ONTOLOGY = "contracts/ontology.v1.json"
DOMAIN = "contracts/world-traversal-learning.v1.json"
HORIZON = "plans/horizon.v1.json"
DISPATCH = "plans/active/BI-HORIZON.dispatch.v1.json"
PATHS = "contracts/workstation-paths.v1.json"
SEMANTICS = ("HIGHLIGHT_OBSERVATION", "WORLD_TARGET_TRACK", "WORLD_INTERACTION_ATTEMPT")
INVARIANTS = ("BI-ONT-028", "BI-ONT-029", "BI-ONT-030")
ORDER = ("OFFLINE_PREFLIGHT", "WORLD_SENSOR", "WORLD_OUTCOME", "WORLD_INTEGRATE")
SOURCE_OWNERS = {
    "root": "AGENTS.md",
    "detail": "docs/AGENT_OPERATING_RULES.md",
    "doctrine": "docs/DOCTRINE.md",
    "ontology": ONTOLOGY,
    "domain_contract": DOMAIN,
    "domain_library": "betterinstincts/world_traversal_learning.py",
    "host_adapter": "betterinstincts/host_stack.py",
    "game_control_owner": "betterinstincts/screen_admit.py",
    "lot_guard": "betterinstincts/lot_boundary.py",
    "existing_workflow": DISPATCH,
    "horizon": HORIZON,
}
ROUTES = {
    "AGENTS.md": ("docs/AGENT_OPERATING_RULES.md", "docs/WORLD_TRAVERSAL_HARNESS.md"),
    "docs/AGENT_OPERATING_RULES.md": ("contracts/world-traversal-harness.v1.json",
                                      "BI-ONT-028..030", "python -m scripts.check_world_traversal_harness"),
    "docs/DOCTRINE.md": ("HIGHLIGHT_OBSERVATION", "WORLD_TARGET_TRACK",
                          "WORLD_INTERACTION_ATTEMPT", "WORLD_SENSOR", "BI-002"),
    "docs/ONTOLOGY.md": ("revision 5", "BI-ONT-028", "BI-ONT-029", "BI-ONT-030"),
    "docs/WORLD_TRAVERSAL_HARNESS.md": ("WORLD_SENSOR", "WORLD_OUTCOME",
                                         "WORLD_INTEGRATE", "docs/LEDGER.md",
                                         "contracts/workstation-paths.v1.json",
                                         "BLOCKED_LOCAL_GAME_ACCESS"),
    ".cursor/skills/world-traversal-p08/SKILL.md": (
        "name: world-traversal-p08", "python -m scripts.horizon_status",
        "python -m scripts.check_world_traversal_harness",
        "WORLD_SENSOR", "WORLD_OUTCOME", "WORLD_INTEGRATE",
        "player_interrupted: false", "BI-002",
    ),
    ".github/workflows/ci.yml": ("python -m scripts.check_world_traversal_harness",
                                  "python -m unittest tests.test_world_traversal_harness -v"),
}
ARTIFACT_VISIBILITY = {
    "OFFLINE_MODEL": "IGNORED_LOCAL_ONLY",
    "P08_SENSOR": "PRIVATE_LOCAL_ONLY_NOT_TRACKED",
    "P08_OUTCOME": "PRIVATE_LOCAL_ONLY_NOT_TRACKED",
    "SOURCE_PROOF": "PUBLIC_TRACKED_SANITIZED",
}


class WorldTraversalHarnessError(ValueError):
    """World traversal canonical ownership, safety or completeness regressed."""


def _must(condition: bool, reason: str) -> None:
    if not condition:
        raise WorldTraversalHarnessError(reason)


def _safe_rel(path: object) -> str:
    _must(isinstance(path, str) and bool(path), "HARNESS_PATH_INVALID")
    p = PurePosixPath(path)
    _must(not p.is_absolute() and ".." not in p.parts and
          p.as_posix() == path and "\\" not in path and ":" not in path,
          "HARNESS_PATH_INVALID")
    return path


def load_inputs(root: Path = ROOT) -> tuple[dict, dict, dict, dict, dict, dict, dict]:
    root = Path(root)
    def read(rel: str) -> dict:
        data = json.loads((root / rel).read_text(encoding="utf-8"))
        _must(isinstance(data, dict), "HARNESS_JSON_OBJECT_REQUIRED:" + rel)
        return data
    files = {p: (root / p).read_text(encoding="utf-8") for p in ROUTES}
    return (read(MANIFEST), read(ONTOLOGY), read(DOMAIN), read(HORIZON),
            read(DISPATCH), read(PATHS), files)


def validate_contract(
    manifest: Mapping[str, Any],
    ontology: Mapping[str, Any],
    domain: Mapping[str, Any],
    horizon: Mapping[str, Any],
    dispatch: Mapping[str, Any],
    paths: Mapping[str, Any],
    contents: Mapping[str, str],
    *,
    root: Path = ROOT,
) -> dict:
    """Validate semantic consistency and read-first/code/skill/workflow routes."""
    _must(manifest.get("schema") == "betterinstincts.world-traversal-harness/v1"
          and manifest.get("id") == "BI-P00-P01-WORLD-TRAVERSAL-HARNESS"
          and manifest.get("revision") == 1, "HARNESS_SCHEMA_DRIFT")
    authority = manifest.get("authority")
    _must(isinstance(authority, Mapping), "HARNESS_OWNERS_MISSING")
    for role, exact in SOURCE_OWNERS.items():
        _must(authority.get(role) == exact, "HARNESS_OWNER_DRIFT:" + role)
    _must(authority.get("ontology_min_revision") == 5 and
          tuple(authority.get("semantic_ids", ())) == SEMANTICS and
          tuple(authority.get("invariants", ())) == INVARIANTS,
          "HARNESS_ONTOLOGY_ROUTE_DRIFT")
    _must(ontology.get("revision", 0) >= 5, "ONTOLOGY_REVISION_LOST")
    concepts = ontology.get("concepts", {})
    invs = {x.get("id"): x for x in ontology.get("invariants", ())
            if isinstance(x, Mapping)}
    for name in SEMANTICS:
        item = concepts.get(name)
        _must(isinstance(item, Mapping) and item.get("definition") and
              item.get("canonical_owner") == DOMAIN,
              "WORLD_SEMANTIC_OWNER_LOST:" + name)
    for item in INVARIANTS:
        row = invs.get(item)
        _must(isinstance(row, Mapping) and DOMAIN in row.get("owned_by", [])
              if item != "BI-ONT-030" else isinstance(row, Mapping)
              and HORIZON in row.get("owned_by", []),
              "WORLD_SEMANTIC_INVARIANT_LOST:" + item)
    relations = {(x.get("from"), x.get("predicate"), x.get("to"))
                 for x in ontology.get("relations", ()) if isinstance(x, Mapping)}
    _must(("WORLD_TARGET_TRACK", "CANNOT_MINT_INPUT_AUTHORITY", "CONTROL_PERMIT") in relations and
          ("WORLD_INTERACTION_ATTEMPT", "MAY_UPDATE_BOUNDED_ADVISORY_ONLY",
           "LEARNING_MODEL") in relations, "WORLD_SEMANTIC_AUTHORITY_RELATION_LOST")

    frames = domain.get("frames", {})
    learning = domain.get("learning", {})
    boundaries = domain.get("boundaries", {})
    _must(domain.get("schema") == "betterinstincts.world-traversal-learning/v1"
          and frames.get("min_for_lock") == 2
          and frames.get("negative_confirmations") == 2
          and frames.get("each_frame_requires_two_distinct_cue_sources") is True
          and "NULL_ALLOWED" in frames.get("highlight_target_id_policy", "")
          and learning.get("max_seen_attempts") == 2048
          and learning.get("player_interrupted_attestation") == "EXPLICIT_FALSE_REQUIRED"
          and learning.get("heldout_training_overlap") == "ABSTAIN_NOT_COUNTED_AS_VALIDATION"
          and boundaries.get("execute_allowed_default") is False
          and boundaries.get("host_stack_opt_in_field") == "world_target.highlight_frames",
          "WORLD_TRACK_OR_REPLAY_SAFETY_DRIFT")

    _must(manifest.get("product_gate") == "BI-002"
          and manifest.get("supporting_priority") ==
              "BI-WORLD-TRAVERSAL-P08-SENSOR"
          and horizon.get("current_gate") == "BI-002"
          and horizon.get("next_supporting_priority", {}).get("id") ==
              manifest["supporting_priority"], "WORLD_HORIZON_PRIORITY_DRIFT")
    validate_horizon(dict(horizon))
    validate_dispatch(dict(horizon), dict(dispatch))
    _must(tuple(manifest.get("launch_order", ())) == ORDER,
          "WORLD_P01_LAUNCH_ORDER_DRIFT")
    workflow = manifest.get("workflow")
    _must(isinstance(workflow, list) and
          [x.get("id") for x in workflow if isinstance(x, Mapping)] == list(ORDER),
          "WORLD_P01_WORKFLOW_MISSING")
    by_id = {x["id"]: x for x in workflow}
    for name, expected_dep in (
        ("WORLD_SENSOR", "OFFLINE_PREFLIGHT"),
        ("WORLD_OUTCOME", "WORLD_SENSOR"),
        ("WORLD_INTEGRATE", "WORLD_OUTCOME"),
    ):
        _must(by_id[name].get("depends_on") == [expected_dep],
              "WORLD_P01_DEPENDENCY_DRIFT:" + name)
    for name in ("WORLD_SENSOR", "WORLD_OUTCOME"):
        _must(by_id[name].get("owner") == "LOCAL_AGENT_RUNTIME",
              "WORLD_P01_GAME_HOST_OWNER_DRIFT:" + name)
    _must(by_id["WORLD_INTEGRATE"].get("owner") == "CURRENT_CHAT_RUNTIME",
          "WORLD_P01_INTEGRATION_OWNER_DRIFT")
    runtime = manifest.get("runtime_partition", {})
    _must(runtime.get("shared_desktop") == "SINGLE_SCREEN_OWNER_SERIAL_WITH_GAME_HUNGER"
          and runtime.get("auto_dispatch") is False
          and runtime.get("observed_local_activation") is False,
          "WORLD_P01_PHANTOM_LOCAL_ACTIVATION")

    artifacts = manifest.get("artifacts")
    _must(isinstance(artifacts, list) and
          {x.get("id") for x in artifacts if isinstance(x, Mapping)}
          == set(ARTIFACT_VISIBILITY), "WORLD_P01_ARTIFACT_REGISTRY_MISSING")
    by_artifact = {x["id"]: x for x in artifacts}
    for name, visibility in ARTIFACT_VISIBILITY.items():
        _must(by_artifact[name].get("visibility") == visibility,
              "WORLD_P01_ARTIFACT_PRIVACY_DRIFT:" + name)
    _must(by_artifact["P08_SENSOR"].get("path", "").startswith("dist/game-host/") and
          by_artifact["P08_OUTCOME"].get("path", "").startswith("dist/game-host/") and
          by_artifact["OFFLINE_MODEL"].get("path", "").startswith("dist/world-traversal-eval/") and
          by_artifact["SOURCE_PROOF"].get("path") == "docs/LEDGER.md",
          "WORLD_P01_ARTIFACT_PATH_DRIFT")
    guard = manifest.get("safety", {})
    for key in ("execute_allowed", "auto_collect_frames", "auto_persist_models",
                "auto_use_saves", "may_change_windows_peripherals",
                "may_replace_screen_input_owner", "may_certify_BI002"):
        _must(guard.get(key) is False, "WORLD_P01_HARNESS_EFFECT_GRANTED:" + key)
    _must(manifest.get("harness", {}).get("skill") ==
          ".cursor/skills/world-traversal-p08/SKILL.md" and
          manifest.get("harness", {}).get("hook_existing") ==
          ".cursor/hooks/operator_boundary.py" and
          manifest.get("harness", {}).get("complete_check") ==
          "python -m scripts.check_world_traversal_harness",
          "WORLD_P01_SKILL_OR_HOOK_ROUTE_DRIFT")
    for required in ("python -m scripts.check_world_traversal_harness",
                     "python -m unittest tests.test_world_traversal_harness -v",
                     "python -m scripts.check_horizon"):
        _must(required in manifest.get("validators", ()),
              "WORLD_P01_VALIDATOR_MISSING:" + required)
    _must(manifest.get("workstation", {}).get("canonical_owner") == PATHS
          and manifest.get("workstation", {}).get("bootstrap_owner") ==
              "bootstrap.py" and
          paths.get("schema") == "betterinstincts.workstation-paths/v1",
          "WORLD_P01_WORKSTATION_OWNER_DRIFT")
    for platform in ("windows", "linux"):
        profile = paths.get("profiles", {}).get(platform, {})
        _must(all(isinstance(profile.get(role), str) and profile[role] for role in
                  ("development", "use", "worktrees", "entrypoint")) and
              profile.get("development") != profile.get("use"),
              "WORLD_P01_WORKSTATION_PROFILE_MISSING:" + platform)

    code_map = manifest.get("codebase_map")
    _must(isinstance(code_map, list) and
          len({x.get("surface") for x in code_map if isinstance(x, Mapping)}) ==
              len(code_map) >= 7, "WORLD_P01_CODEBASE_MAP_MISSING")
    referenced = set()
    for entry in code_map:
        _must(isinstance(entry, Mapping) and
              isinstance(entry.get("paths"), list) and entry["paths"],
              "WORLD_P01_CODEBASE_MAP_INVALID")
        for path in entry["paths"]:
            rel = _safe_rel(path)
            _must((root / rel).is_file(), "WORLD_P01_CODEBASE_OWNER_MISSING:" + rel)
            referenced.add(rel)
    for needed in ("AGENTS.md", "betterinstincts/world_traversal_learning.py",
                   "contracts/ontology.v1.json", "contracts/world-traversal-harness.v1.json",
                   "contracts/workstation-paths.v1.json",
                   ".cursor/skills/world-traversal-p08/SKILL.md"):
        _must(needed in referenced or needed == MANIFEST,
              "WORLD_P01_SOURCE_MAP_GAP:" + needed)
    # Root is a strictly size-budgeted router; detailed semantics live in the
    # mandatory owner, never in a duplicated always-on prompt wall.
    root_agent = contents.get("AGENTS.md", "")
    _must(isinstance(root_agent, str) and len(root_agent) <= 3600,
          "WORLD_P01_ROOT_GOVERNANCE_BUDGET")
    for path, fragments in ROUTES.items():
        content = contents.get(path)
        _must(isinstance(content, str), "WORLD_P01_ROUTE_FILE_MISSING:" + path)
        for fragment in fragments:
            _must(fragment in content, "WORLD_P01_ROUTE_TEXT_DRIFT:" + path + ":" + fragment)
    return {
        "status": "P00_P01_WORLD_TRAVERSAL_HARNESS_PASS",
        "ontology_revision": ontology["revision"], "invariants": list(INVARIANTS),
        "supporting_priority": manifest["supporting_priority"],
        "product_gate": "BI-002", "codebase_surfaces": len(code_map),
        "artifact_classes": len(artifacts),
        "local_game_activation_observed": False, "game_input_authorized": False,
        "proof_ceiling": manifest.get("proof_ceiling"),
    }


def check(root: Path = ROOT) -> dict:
    root = Path(root)
    inputs = load_inputs(root)
    return validate_contract(*inputs, root=root)


def main() -> int:
    try:
        print(json.dumps(check(), sort_keys=True))
        return 0
    except (WorldTraversalHarnessError, OSError, ValueError, KeyError,
            TypeError, AttributeError, json.JSONDecodeError) as exc:
        print("P00_P01_WORLD_TRAVERSAL_HARNESS_BLOCKED " + str(exc))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
