"""Fail-closed, repository-only ontology consultation checks.

This does not authorize game execution or certify gameplay. Git history confirms
a consultation record predates source mutation *within the candidate branch*;
it cannot attest that a human actually read the record.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ONTOLOGY = Path("contracts/ontology.v1.json")
CONSULTATIONS = Path("contracts/consultations")
REQUIRED = (
    "proposed_capability", "affected_concepts", "relevant_canonical_owners",
    "invariants_checked", "game_build_scope", "evidence_ceiling",
    "player_save_control_impact", "expected_outcome", "negative_tests",
    "rollback_path", "unresolved_unknowns", "files_expected", "decision",
)
DECISIONS = {
    "ADMIT_FOR_OFFLINE_PROTOTYPE", "REQUIRE_ONTOLOGY_AMENDMENT",
    "BLOCK_UNSAFE", "DEFER_FOR_GAME_EVIDENCE",
}


def read_json(path: Path) -> dict:
    item = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(item, dict):
        raise ValueError(f"{path}: root must be an object")
    return item


def validate_ontology(data: dict, root: Path = ROOT) -> None:
    if data.get("schema") != "betterinstincts.ontology/v1":
        raise ValueError("ONTOLOGY_SCHEMA_INVALID")
    concepts = data.get("concepts")
    if not isinstance(concepts, dict) or not concepts:
        raise ValueError("ONTOLOGY_CONCEPTS_MISSING")
    for name, concept in concepts.items():
        if not isinstance(concept, dict) or not name or not concept.get("definition"):
            raise ValueError(f"CONCEPT_INVALID:{name}")
        owner = concept.get("canonical_owner")
        if not isinstance(owner, str) or not (root / owner).is_file():
            raise ValueError(f"CONCEPT_OWNER_MISSING:{name}")
    relations = data.get("relations", [])
    if not isinstance(relations, list) or not relations:
        raise ValueError("ONTOLOGY_RELATIONS_MISSING")
    for edge in relations:
        if any(edge.get(k) not in concepts for k in ("from", "to")) or not edge.get("predicate"):
            raise ValueError("ONTOLOGY_RELATION_INVALID")
    invariants = data.get("invariants", [])
    ids = [x.get("id") for x in invariants]
    if not ids or any(not isinstance(x, str) for x in ids) or len(ids) != len(set(ids)):
        raise ValueError("ONTOLOGY_INVARIANTS_INVALID")
    for entry in invariants:
        if not entry.get("rule") or not entry.get("owned_by"):
            raise ValueError("ONTOLOGY_INVARIANT_EMPTY")
        for owner in entry["owned_by"]:
            if not (root / owner).is_file():
                raise ValueError(f"INVARIANT_OWNER_MISSING:{owner}")


def is_behavior_mutation(path: str) -> bool:
    if path == "AGENTS.md":
        return True
    if path.startswith((".github/workflows/", ".cursor/rules/", "betterinstincts/", "scripts/", "tests/", "compatibility/")):
        return True
    if path.startswith("contracts/") and path.endswith(".json"):
        return not (path == str(ONTOLOGY) or path.startswith(str(CONSULTATIONS) + "/"))
    return False


def validate_consultation(data: dict, ontology: dict, changed: list[str], root: Path = ROOT) -> None:
    if data.get("schema") != "betterinstincts.ontology-consultation/v1":
        raise ValueError("CONSULTATION_SCHEMA_INVALID")
    for field in REQUIRED:
        value = data.get(field)
        if value is None or value == "" or value == []:
            raise ValueError(f"CONSULTATION_FIELD_MISSING:{field}")
    if data.get("ontology") != str(ONTOLOGY):
        raise ValueError("CONSULTATION_WRONG_ONTOLOGY")
    raw = (root / ONTOLOGY).read_bytes()
    blob = hashlib.sha1(f"blob {len(raw)}\0".encode() + raw).hexdigest()
    if data.get("ontology_blob_sha") != blob:
        raise ValueError("CONSULTATION_ONTOLOGY_VERSION_MISMATCH")
    if data.get("game_build_scope") != "REPOSITORY_OFFLINE_ONLY" and not data.get("game_build_scope", "").startswith("EXACT_GAME_BUILD:"):
        raise ValueError("CONSULTATION_GAME_BUILD_AMBIGUOUS")
    if data.get("evidence_ceiling") == "GAME_CERTIFIED" and data.get("game_build_scope") == "REPOSITORY_OFFLINE_ONLY":
        raise ValueError("CONSULTATION_OFFLINE_PROOF_INFLATED")
    concepts = set(ontology["concepts"])
    invs = {x["id"] for x in ontology["invariants"]}
    if set(data["affected_concepts"]) - concepts:
        raise ValueError("CONSULTATION_UNKNOWN_CONCEPT")
    if set(data["invariants_checked"]) - invs:
        raise ValueError("CONSULTATION_UNKNOWN_INVARIANT")
    if not set(data["invariants_checked"]):
        raise ValueError("CONSULTATION_NO_INVARIANTS")
    universal = {"BI-ONT-001", "BI-ONT-002", "BI-ONT-003", "BI-ONT-005", "BI-ONT-006", "BI-ONT-008", "BI-ONT-010", "BI-ONT-012"}
    if not universal.issubset(set(data["invariants_checked"])):
        raise ValueError("CONSULTATION_UNIVERSAL_INVARIANTS_MISSING")
    if data["decision"] not in DECISIONS:
        raise ValueError("CONSULTATION_DECISION_INVALID")
    for owner in data["relevant_canonical_owners"]:
        if not isinstance(owner, str) or not (root / owner).is_file():
            raise ValueError(f"CONSULTATION_UNKNOWN_OWNER:{owner}")
    missing = set(changed) - set(data["files_expected"])
    if missing:
        raise ValueError("CONSULTATION_UNMAPPED_MUTATIONS:" + ",".join(sorted(missing)))
    if data["decision"] != "ADMIT_FOR_OFFLINE_PROTOTYPE" and changed:
        raise ValueError("CONSULTATION_NOT_ADMITTED")


def git(*args: str, root: Path = ROOT) -> str:
    run = subprocess.run(
        ["git", *args], cwd=root, capture_output=True, text=True, check=False,
    )
    if run.returncode:
        raise ValueError("GIT_CHECK_FAILED:" + " ".join(args) + ":" + run.stderr.strip())
    return run.stdout.strip()


def changed_in_branch(base: str, root: Path = ROOT) -> list[str]:
    return [p for p in git("diff", "--name-only", f"{base}...HEAD", root=root).splitlines()
            if is_behavior_mutation(p)]


def first_mutation_commit(base: str, root: Path = ROOT) -> str | None:
    for commit in git("rev-list", "--reverse", f"{base}..HEAD", root=root).splitlines():
        changed = git("diff-tree", "--no-commit-id", "--name-only", "-r", commit, root=root).splitlines()
        if any(is_behavior_mutation(p) for p in changed):
            return commit
    return None


def manifest_precedes(path: str, first_change: str, root: Path = ROOT) -> bool:
    # Git only: a record introduced in the *same* commit as source code is too late.
    proc = subprocess.run(
        ["git", "cat-file", "-e", f"{first_change}^:{path}"],
        cwd=root, capture_output=True, check=False,
    )
    return proc.returncode == 0


def check_branch(base: str, root: Path = ROOT) -> tuple[int, int]:
    ontology = read_json(root / ONTOLOGY)
    validate_ontology(ontology, root)
    mutated = changed_in_branch(base, root)
    if not mutated:
        return (0, 0)
    first = first_mutation_commit(base, root)
    if first is None:
        raise ValueError("FIRST_MUTATION_COMMIT_NOT_FOUND")
    candidate_paths = git("diff", "--name-only", f"{base}...HEAD", root=root).splitlines()
    manifests = [p for p in candidate_paths if p.startswith(str(CONSULTATIONS) + "/") and p.endswith(".json")]
    good = []
    for path in manifests:
        if not manifest_precedes(path, first, root):
            continue
        try:
            validate_consultation(read_json(root / path), ontology, mutated, root)
            good.append(path)
        except ValueError:
            continue
    if not good:
        raise ValueError("ONTOLOGY_CONSULTATION_REQUIRED_BEFORE_PROTOTYPE")
    return (len(mutated), len(good))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-ref", default=None, help="PR base commit to audit temporal consultation order")
    parser.add_argument("--consultation", default=None, help="Validate one pre-prototype consultation JSON")
    args = parser.parse_args()
    try:
        data = read_json(ROOT / ONTOLOGY)
        validate_ontology(data)
        if args.consultation:
            validate_consultation(read_json(ROOT / args.consultation), data, [])
        if args.base_ref:
            changed, manifests = check_branch(args.base_ref)
            print(f"ONTOLOGY_GATE_PASS changed={changed} early_consultations={manifests}")
        else:
            print("ONTOLOGY_SCHEMA_PASS (branch chronology not checked)")
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(f"ONTOLOGY_GATE_FAIL {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
