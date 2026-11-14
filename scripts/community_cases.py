"""Manual, opt-in export and validation of portable reviewed *semantic* cases.

No passive capture, network, import into gameplay, model adoption, or developer
approval. Local observation references are never present in exported bundles.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

from betterinstincts.judgment_learning import (
    JudgmentLearningError, _action, _context, _example, _patch,
)
from scripts.community_candidate import _read_json, CandidateError

ROOT = Path(__file__).resolve().parents[1]
SUBMISSIONS = ROOT / "community" / "submissions"
SCHEMA = "betterinstincts.community-learning.cases/v1"
POLICY = "UNTRUSTED_REVIEW_ONLY_NO_GAME_OR_OS_EFFECT"
MAX_CASES = 128
MAX_INPUT = 150_000
MAX_BUNDLE = 65_536


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("ascii")


def _hash(value: object) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _case_digest(game_version: str, platform: str, case: dict) -> str:
    return _hash({"game_version": game_version, "platform": platform,
                  "context": case["context"], "action": case["action"],
                  "outcome": case["outcome"]})


def build_bundle(examples: object) -> dict:
    """Emit only enumerated semantics from explicitly reviewed local examples."""
    if not isinstance(examples, list) or not 1 <= len(examples) <= MAX_CASES:
        raise CandidateError("REVIEWED_CASE_BATCH_LIMIT")
    rows, seen = [], set()
    version, platform = None, None
    for supplied in examples:
        try:
            event = _example(supplied)
        except (JudgmentLearningError, KeyError, TypeError, ValueError) as exc:
            raise CandidateError("UNREVIEWED_OR_UNSAFE_SOURCE_EXAMPLE") from exc
        if version is None:
            version, platform = event["game_version"], event["platform"]
        if (event["game_version"], event["platform"]) != (version, platform):
            raise CandidateError("MIXED_GAME_VERSION_OR_PLATFORM")
        row = {key: event[key] for key in ("context", "action", "outcome")}
        row["case_sha256"] = _case_digest(version, platform, row)
        if row["case_sha256"] in seen:
            raise CandidateError("DUPLICATE_SEMANTIC_CASE")
        seen.add(row["case_sha256"])
        rows.append(row)
    rows.sort(key=lambda row: row["case_sha256"])
    bundle = {"schema": SCHEMA, "game_version": version,
              "platform": platform, "cases": rows,
              "effect_policy": POLICY, "review_state": "UNREVIEWED"}
    bundle["bundle_sha256"] = _hash(bundle)
    validate_bundle(bundle)
    return bundle


def validate_bundle(value: object) -> dict:
    if not isinstance(value, dict) or set(value) != {
        "schema", "game_version", "platform", "cases", "effect_policy",
        "review_state", "bundle_sha256",
    }:
        raise CandidateError("COMMUNITY_CASE_BUNDLE_SCHEMA_INVALID")
    if (value["schema"] != SCHEMA or value["effect_policy"] != POLICY
            or value["review_state"] != "UNREVIEWED"):
        raise CandidateError("COMMUNITY_CASE_AUTHORITY_INVALID")
    try:
        version = _patch(value["game_version"])
    except (JudgmentLearningError, TypeError) as exc:
        raise CandidateError("COMMUNITY_CASE_PATCH_INVALID") from exc
    platform = value["platform"]
    if platform not in ("windows", "linux", "macos"):
        raise CandidateError("COMMUNITY_CASE_PLATFORM_INVALID")
    rows = value["cases"]
    if not isinstance(rows, list) or not 1 <= len(rows) <= MAX_CASES:
        raise CandidateError("COMMUNITY_CASE_COUNT_INVALID")
    seen, labels = set(), {}
    for row in rows:
        if not isinstance(row, dict) or set(row) != {
            "context", "action", "outcome", "case_sha256",
        }:
            raise CandidateError("COMMUNITY_CASE_UNKNOWN_FIELDS")
        try:
            context, action = _context(row["context"]), _action(row["action"])
        except (JudgmentLearningError, TypeError, ValueError) as exc:
            raise CandidateError("COMMUNITY_CASE_ENUM_INVALID") from exc
        if row["outcome"] not in ("helpful", "harmful"):
            raise CandidateError("COMMUNITY_CASE_OUTCOME_INVALID")
        digest = _case_digest(version, platform, {
            "context": context, "action": action, "outcome": row["outcome"],
        })
        if row["case_sha256"] != digest:
            raise CandidateError("COMMUNITY_CASE_DIGEST_MISMATCH")
        if digest in seen:
            raise CandidateError("COMMUNITY_CASE_REPLAY")
        seen.add(digest)
        context_action = (_canonical(context), action)
        labels.setdefault(context_action, set()).add(row["outcome"])
    if [row["case_sha256"] for row in rows] != sorted(seen):
        raise CandidateError("COMMUNITY_CASE_ORDER_INVALID")
    expect = _hash({k: v for k, v in value.items() if k != "bundle_sha256"})
    if value["bundle_sha256"] != expect:
        raise CandidateError("COMMUNITY_BUNDLE_DIGEST_MISMATCH")
    if len(_canonical(value)) > MAX_BUNDLE:
        raise CandidateError("COMMUNITY_BUNDLE_SIZE_LIMIT")
    return {"state": "STRUCTURAL_PASS_MAINTAINER_REVIEW_REQUIRED",
            "cases": len(rows),
            "opposing_label_contexts": sum(len(x) > 1 for x in labels.values()),
            "execute_allowed": False, "safe_to_promote": False,
            "provenance_attested": False, "share_consent_attested": False}


def read_bundle(path: Path) -> dict:
    item = _read_json(path, MAX_BUNDLE)
    validate_bundle(item)
    return item


def export_to(path: Path, bundle: dict) -> None:
    validate_bundle(bundle)
    if (path.is_symlink() or path.parent.is_symlink()
            or not path.parent.is_dir()):
        raise CandidateError("COMMUNITY_EXPORT_PATH_UNSAFE")
    payload = _canonical(bundle) + b"\n"
    if len(payload) > MAX_BUNDLE:
        raise CandidateError("COMMUNITY_EXPORT_OVERSIZE")
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(path, flags, 0o600)
    except FileExistsError as exc:
        raise CandidateError("COMMUNITY_EXPORT_TARGET_EXISTS") from exc
    with os.fdopen(fd, "wb") as dest:
        dest.write(payload)


def audit_repo() -> dict:
    """Bounded CI check: validate manual, data-only PR submissions. No imports."""
    if SUBMISSIONS.is_symlink() or not SUBMISSIONS.is_dir():
        raise CandidateError("COMMUNITY_SUBMISSIONS_DIRECTORY_UNSAFE")
    files = list(SUBMISSIONS.iterdir())
    if len(files) > 257:
        raise CandidateError("COMMUNITY_SUBMISSIONS_CAP")
    accepted = 0
    for path in files:
        if path.name == "README.md":
            continue
        if path.is_symlink() or not path.is_file() or path.suffix != ".json":
            raise CandidateError("COMMUNITY_SUBMISSION_UNEXPECTED_FILE")
        read_bundle(path)
        accepted += 1
    return {"state": "REPOSITORY_STRUCTURAL_AUDIT_PASS",
            "bundles": accepted, "execute_allowed": False,
            "safe_to_promote": False}


def run(argv: list[str] | None = None) -> dict:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    export = commands.add_parser("export", help="Separate explicit sharing decision")
    export.add_argument("--reviewed-examples", required=True, type=Path)
    export.add_argument("--out", required=True, type=Path)
    export.add_argument("--ack-share-reviewed-cases", action="store_true")
    validate = commands.add_parser("validate", help="Offline structural review")
    validate.add_argument("--bundle", required=True, type=Path)
    commands.add_parser("audit-repo", help="Validate only explicitly submitted PR files")
    args = parser.parse_args(argv)
    if args.command == "export":
        if not args.ack_share_reviewed_cases:
            raise CandidateError("EXPLICIT_COMMUNITY_SHARING_ACK_REQUIRED")
        bundle = build_bundle(_read_json(args.reviewed_examples, MAX_INPUT))
        export_to(args.out, bundle)
        return {"state": "LOCAL_SANITIZED_CASE_BUNDLE_NOT_UPLOADED",
                "cases": len(bundle["cases"]), "execute_allowed": False,
                "safe_to_promote": False}
    if args.command == "validate":
        return validate_bundle(read_bundle(args.bundle))
    return audit_repo()


def main() -> int:
    try:
        print(json.dumps(run(), sort_keys=True))
        return 0
    except (CandidateError, JudgmentLearningError, OSError, ValueError,
            TypeError, KeyError, OverflowError) as exc:
        print(json.dumps({"state": "BLOCKED", "reason": str(exc),
                          "execute_allowed": False}, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
