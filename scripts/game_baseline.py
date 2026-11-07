#!/usr/bin/env python3
"""Prepare a genuine BI-002 vanilla baseline recorder from an attested Live Mode session.

Reads an existing game-host event receipt; initializes only ignored, repo-local
dist/live-cert data. No game access, fabricated metrics, UI automation or save edits.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from betterinstincts.live_eval import EvidenceError
from scripts import game_host, live_cert

ALLOWED_HOST_STATES = {"LIVE_REPORTED_UNREVIEWED", "SAMPLE_INGESTED_UNVERIFIED"}


def prepare(run_id: str, *, output: Path = live_cert.OUTPUT) -> dict:
    _, host_meta, events = game_host.load(run_id)
    if events[-1]["state"] not in ALLOWED_HOST_STATES:
        raise game_host.GateError("LIVE_MODE_ATTESTATION_REQUIRED")
    live_receipts = [row for row in events if row["state"] == "LIVE_REPORTED_UNREVIEWED"]
    if not live_receipts:
        raise game_host.GateError("LIVE_MODE_ATTESTATION_REQUIRED")
    version = live_receipts[-1].get("game_version")
    if not isinstance(version, str) or not game_host.VERSION_RE.fullmatch(version):
        raise game_host.GateError("EXACT_LIVE_GAME_VERSION_REQUIRED")
    if host_meta.get("platform") != "windows" or host_meta.get("mode") not in {"new", "chosen"}:
        raise game_host.GateError("EXPECTED_WINDOWS_GAME_HOST")
    if host_meta.get("game_version") and host_meta["game_version"] != version:
        raise game_host.GateError("GAME_VERSION_MISMATCH")
    location = live_cert.run_root(run_id, output)
    if location.exists():
        meta, _ = live_cert.load(run_id, output)
        if meta["game_version"] != version or meta["platform"] != "windows":
            raise game_host.GateError("EXISTING_BASELINE_SESSION_VERSION_MISMATCH")
        disposition = "EXISTING_RECORDER_PRESERVED"
    else:
        live_cert.init(run_id, version, "windows", live_cert.PENDING_STUDIO, output=output)
        disposition = "BASELINE_RECORDER_CREATED"
    progress = live_cert.status(run_id, output)
    return {
        "state": disposition,
        "run_id": run_id,
        "game_version": version,
        "baseline_trials": progress["counts"]["baseline"],
        "modified_trials": progress["counts"]["modified"],
        "rollback_trials": progress["counts"]["rollback"],
        "next_stage": progress["next_stage"],
        "proof_ceiling": "RECORDER_READY_NOT_GAMEPLAY_METRICS_OR_CERTIFICATION",
        "studio_build": live_cert.load(run_id, output)[0]["sims4studio_build"],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True, help="Existing, locally attested game-host run ID")
    args = parser.parse_args(argv)
    try:
        result = prepare(args.run_id)
    except (game_host.GateError, EvidenceError, FileExistsError, FileNotFoundError,
            KeyError, ValueError, OSError, TypeError) as exc:
        print(json.dumps({"state": "BLOCKED", "reason": str(exc)}, sort_keys=True))
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
