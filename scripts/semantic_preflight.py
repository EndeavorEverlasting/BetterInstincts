"""Mandatory local-agent ontology preflight for changes, samples and experiments.

PASS is semantic consultation ONLY. Game input still requires independent
scene, save, player, build, adapter and maintainer approval.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts.check_ontology import (
    CONSULTATIONS, ONTOLOGY, ROOT,
    read_json, validate_consultation, validate_ontology,
)


class SemanticPreflightError(ValueError):
    pass


def preflight(
    consultation: str,
    *,
    operation: str,
    files: tuple[str, ...] = (),
    exact_game_build: str | None = None,
    root: Path = ROOT,
) -> dict:
    if operation not in {"repo_mutation", "offline_experiment", "game_sampling", "game_experiment"}:
        raise SemanticPreflightError("UNKNOWN_OPERATION")
    rel = Path(consultation)
    if rel.is_absolute() or ".." in rel.parts or rel.suffix != ".json" or not rel.is_relative_to(CONSULTATIONS):
        raise SemanticPreflightError("CONSULTATION_PATH_NOT_CANONICAL")
    path = (root / rel).resolve()
    if not path.is_relative_to((root / CONSULTATIONS).resolve()) or not path.is_file():
        raise SemanticPreflightError("CONSULTATION_NOT_FOUND")
    targets = []
    for item in files:
        p = Path(item)
        if p.is_absolute() or ".." in p.parts or not str(p).strip() or str(p) == ".":
            raise SemanticPreflightError("MUTATION_PATH_INVALID")
        targets.append(p.as_posix())
    if operation == "repo_mutation" and not targets:
        raise SemanticPreflightError("MUTATION_PATHS_REQUIRED")
    ontology = read_json(root / ONTOLOGY)
    validate_ontology(ontology, root)
    record = read_json(path)
    validate_consultation(record, ontology, targets, root)
    # The consultation validator only rejects non-admitted decisions when a
    # mutation file is supplied. Read-only sampling and game experiments have
    # no file path, but a BLOCK_UNSAFE/DEFER decision must still fail closed.
    if record.get("decision") != "ADMIT_FOR_OFFLINE_PROTOTYPE":
        raise SemanticPreflightError("CONSULTATION_NOT_ADMITTED")
    if operation in {"game_sampling", "game_experiment"}:
        if not exact_game_build or record.get("game_build_scope") != "EXACT_GAME_BUILD:" + exact_game_build:
            raise SemanticPreflightError("GAME_SCOPE_NOT_CONSULTED")
    return {
        "status": "ONTOLOGY_PREFLIGHT_PASS_NOT_GAME_AUTHORITY",
        "operation": operation,
        "consultation": rel.as_posix(),
        "files": sorted(set(targets)),
        "game_build_scope": record["game_build_scope"],
        "control_permit": None,
        "next_gate": "INDEPENDENT_HOST_GAME_SAVE_SCENE_PLAYER_ADMISSION" if operation.startswith("game_")
        else "BOUNDED_IMPLEMENTATION_AND_TESTS",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--consultation", required=True)
    parser.add_argument("--operation", required=True, choices=["repo_mutation", "offline_experiment", "game_sampling", "game_experiment"])
    parser.add_argument("--file", action="append", default=[])
    parser.add_argument("--exact-game-build", default=None)
    args = parser.parse_args()
    try:
        result = preflight(args.consultation, operation=args.operation,
                           files=tuple(args.file), exact_game_build=args.exact_game_build)
        print(json.dumps(result, sort_keys=True))
    except (SemanticPreflightError, ValueError, OSError, KeyError, TypeError) as exc:
        print("ONTOLOGY_PREFLIGHT_FAIL " + str(exc))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
