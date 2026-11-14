"""Canonical source-backed mechanics coverage and evidence-driven replan proposals.

Index only; does not replace any Sims domain owner, execute actions, harvest
game state, update private profiles or silently mark gameplay as certified.
"""
from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts/mechanics-registry.v1.json"
SCHEMA = "betterinstincts.mechanics-registry/v1"
LIFE = {"SOURCE_PRESENT", "GAP"}
ID = re.compile(r"^[a-z][a-z0-9]+(?:-[a-z0-9]+)*$")
REF = re.compile(r"^[A-Za-z0-9:_./-]{3,160}$")


class MechanicsRegistryError(ValueError):
    pass


def _file(path: Path, *, size: int = 65536) -> dict:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > size:
        raise MechanicsRegistryError("MECHANICS_REGISTRY_UNSAFE_FILE")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise MechanicsRegistryError("MECHANICS_REGISTRY_INVALID_JSON") from exc
    if not isinstance(data, dict):
        raise MechanicsRegistryError("MECHANICS_REGISTRY_ROOT_INVALID")
    return data


def validate_registry(data: Mapping, *, root: Path = ROOT) -> dict:
    if not isinstance(data, Mapping) or data.get("schema") != SCHEMA:
        raise MechanicsRegistryError("MECHANICS_SCHEMA_INVALID")
    if type(data.get("revision")) is not int or data["revision"] < 1:
        raise MechanicsRegistryError("MECHANICS_REVISION_INVALID")
    rows = data.get("mechanics")
    if not isinstance(rows, list) or not 10 <= len(rows) <= 256:
        raise MechanicsRegistryError("MECHANICS_COVERAGE_INVALID")
    ids: set[str] = set()
    domains: set[str] = set()
    scopes = {"SIM", "HOUSEHOLD", "WORLD"}
    dependency_graph: dict[str, list[str]] = {}
    counts = {"SOURCE_PRESENT": 0, "GAP": 0}
    for row in rows:
        if not isinstance(row, Mapping) or set(row) != {
            "id", "domain", "scope", "owner", "evidence_state", "tests",
            "dependencies", "next_gate", "game_effect_certified", "private_instance_data",
        }:
            raise MechanicsRegistryError("MECHANICS_ROW_SCHEMA_INVALID")
        ident, domain = row["id"], row["domain"]
        if (not isinstance(ident, str) or not ID.fullmatch(ident) or ident in ids
                or not isinstance(domain, str) or not ID.fullmatch(domain)):
            raise MechanicsRegistryError("MECHANICS_DUPLICATE_OR_INVALID_ID")
        ids.add(ident)
        domains.add(domain)
        if row["scope"] not in scopes or row["evidence_state"] not in LIFE:
            raise MechanicsRegistryError("MECHANICS_SCOPE_OR_STATE_INVALID")
        if row["game_effect_certified"] is not False or row["private_instance_data"] is not False:
            raise MechanicsRegistryError("UNPROVEN_LIVE_CLAIM_OR_PRIVATE_DATA")
        if row["next_gate"] not in {"LOCAL_EXACT_BUILD_AND_OUTCOME_PROOF", "P95_OWNER_DISCOVERY"}:
            raise MechanicsRegistryError("MECHANIC_PROOF_GATE_INVALID")
        owner, tests = row["owner"], row["tests"]
        if (not isinstance(tests, list) or len(tests) > 4
                or len(tests) != len(set(map(str, tests)))):
            raise MechanicsRegistryError("MECHANIC_TEST_LIST_INVALID")
        if row["evidence_state"] == "SOURCE_PRESENT":
            if (not isinstance(owner, str) or not owner.startswith("betterinstincts/")
                    or not owner.endswith(".py") or
                    not (root / owner).is_file() or not tests or
                    row["next_gate"] != "LOCAL_EXACT_BUILD_AND_OUTCOME_PROOF"):
                raise MechanicsRegistryError("MECHANIC_SOURCE_OWNER_OR_TEST_MISSING")
            for test in tests:
                if not isinstance(test, str) or not test.startswith("tests/test_") or (
                        not test.endswith(".py") or not (root / test).is_file()):
                    raise MechanicsRegistryError("MECHANIC_TEST_OWNER_INVALID")
        elif owner is not None or tests or row["next_gate"] != "P95_OWNER_DISCOVERY":
            raise MechanicsRegistryError("MECHANIC_GAP_MUST_NOT_INVENT_OWNER")
        deps = row["dependencies"]
        if (not isinstance(deps, list) or len(deps) > 16
                or len(set(map(str, deps))) != len(deps)
                or any(not isinstance(d, str) for d in deps)):
            raise MechanicsRegistryError("MECHANIC_DEPENDENCIES_INVALID")
        dependency_graph[ident] = deps
        counts[row["evidence_state"]] += 1
    for ident, deps in dependency_graph.items():
        if any(d not in ids or d == ident for d in deps):
            raise MechanicsRegistryError("MECHANIC_UNKNOWN_OR_SELF_DEPENDENCY")
    colors: dict[str, int] = {}

    def visit(node: str) -> None:
        if colors.get(node) == 1:
            raise MechanicsRegistryError("MECHANIC_DEPENDENCY_CYCLE")
        if colors.get(node) == 2:
            return
        colors[node] = 1
        for dep in dependency_graph[node]:
            visit(dep)
        colors[node] = 2

    for node in sorted(ids):
        visit(node)
    return {
        "schema": "betterinstincts.mechanics-coverage/v1",
        "mechanics_total": len(ids),
        "domains_total": len(domains),
        "source_present": counts["SOURCE_PRESENT"],
        "visible_gaps": counts["GAP"],
        "live_game_certified": 0,
        "gaps": [r["id"] for r in rows if r["evidence_state"] == "GAP"],
        "proof_ceiling": data["proof_ceiling"],
    }


def load_registry(path: Path = CONTRACT) -> dict:
    data = _file(Path(path))
    validate_registry(data, root=ROOT)
    return data


def review_outcomes(registry: Mapping, outcomes: Sequence[Mapping],
                    *, capture_ref: str) -> dict:
    """Do not lose mechanics when actions fail; propose the NEXT evidence gate.

    A replayed, missing, player-interrupted or unreviewed outcome never
    advances a mechanic's status. No source-state mutation is performed.
    """
    validate_registry(registry)
    if (not isinstance(capture_ref, str) or not REF.fullmatch(capture_ref)
            or not isinstance(outcomes, (list, tuple)) or len(outcomes) > 64):
        raise MechanicsRegistryError("OUTCOMES_OR_CAPTURE_INVALID")
    catalog = {row["id"]: row for row in registry["mechanics"]}
    seen: set[str] = set()
    proposals: list[dict] = []
    for event in outcomes:
        if not isinstance(event, Mapping) or set(event) != {
            "mechanic_id", "outcome", "proof_ref", "capture_ref", "player_interrupted",
        }:
            raise MechanicsRegistryError("MECHANIC_OUTCOME_SCHEMA_INVALID")
        mech = event["mechanic_id"]
        if mech not in catalog:
            raise MechanicsRegistryError("UNKNOWN_MECHANIC_ID_REQUIRES_CATALOG_REVIEW")
        proof = event["proof_ref"]
        if (not isinstance(proof, str) or not REF.fullmatch(proof)
                or proof in seen):
            raise MechanicsRegistryError("REPLAYED_OR_INVALID_OUTCOME_PROOF")
        seen.add(proof)
        if (event["capture_ref"] != capture_ref or type(event["player_interrupted"]) is not bool
                or event["outcome"] not in {"SUCCEEDED", "FAILED", "UNAVAILABLE", "UNKNOWN"}):
            raise MechanicsRegistryError("STALE_OR_AMBIGUOUS_OUTCOME")
        if event["player_interrupted"]:
            continue
        item = catalog[mech]
        if event["outcome"] in {"FAILED", "UNAVAILABLE"}:
            proposals.append({
                "mechanic_id": mech,
                "finding": "MISSING_MECHANIC_OWNER" if item["evidence_state"] == "GAP"
                           else "REPLAN_FROM_FAILURE_NOT_BLIND_RETRY",
                "next_gate": item["next_gate"],
                "owner": item["owner"],
                "evidence_ref": proof,
                "execute_allowed": False,
            })
    return {
        "schema": "betterinstincts.mechanics-replan/v1",
        "capture_ref": capture_ref,
        "replan_proposals": proposals,
        "mutation_allowed": False,
        "game_action_allowed": False,
        "proof_ceiling": "OBSERVED_SOURCE_RECONCILIATION_NOT_GAME_CERTIFICATION",
    }
