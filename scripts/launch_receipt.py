"""Explicit, private launch and intervention receipts for the Windows play entry."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
from uuid import uuid4

from betterinstincts.save_policy import REF_RE

SCHEMA = "betterinstincts.play-launch-receipt/v1"
LIMIT = 32_768
MAX_LAUNCHES = 128
MAX_ASSISTS_PER_LAUNCH = 32


def begin(mode: str, *, root: Path) -> tuple[Path, dict]:
    """Create a run's receipt before effects, under the owned runtime directory."""
    from betterinstincts.control_handoff import HandoffError, _named_screen_lock

    run_id = uuid4().hex
    folder = root / "play-receipts"
    path = folder / run_id / "launch.json"
    try:
        with _named_screen_lock("play-receipt-store.lock", lock_root=root / "locks"):
            if folder.is_symlink():
                raise ValueError("PLAY_RECEIPT_STORE_UNSAFE")
            if folder.exists() and has_reached_capacity((p for p in folder.iterdir() if p.is_dir()), MAX_LAUNCHES):
                raise ValueError("PLAY_RECEIPT_STORE_FULL_ARCHIVE_OLDER_RUNS")
            path.parent.mkdir(parents=True, exist_ok=False)
    except HandoffError as exc:
        raise ValueError("PLAY_RECEIPT_STORE_BUSY_RETRY") from exc
    receipt = {
        "schema": SCHEMA, "run_id": run_id, "startup_mode": mode,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "status": "in_progress", "stage": "startup", "automation_gaps": [],
    }
    try:
        write_result(path, receipt)
    except (OSError, ValueError):
        path.parent.rmdir()
        raise
    return path, receipt


def has_reached_capacity(paths, limit: int) -> bool:
    return any(index >= limit for index, _ in enumerate(paths, start=1))


def write_result(path: Path, receipt: dict) -> None:
    # Every blocked Play gate becomes a stable, private, machine-readable seam.
    # This only records source recovery obligations; it never grants effects.
    if receipt.get("schema") == SCHEMA and receipt.get("status") == "blocked" and receipt.get("automation_gaps"):
        from scripts.seam_closure import record

        closure = record(path, receipt)
        if closure is not None:
            receipt["seam_closure"] = closure
    raw = json.dumps(receipt, sort_keys=True, indent=2) + "\n"
    if len(raw.encode("utf-8")) > LIMIT:
        raise ValueError("PLAY_RECEIPT_TOO_LARGE")
    staged = path.with_name(uuid4().hex + ".tmp")
    try:
        with staged.open("x", encoding="utf-8") as output:
            output.write(raw)
        os.replace(staged, path)
    finally:
        staged.unlink(missing_ok=True)


def gap(stage: str, reason: str, step: str, owner: str, *, actor: str = "human_or_agent") -> dict:
    return {"kind": "MISSING_REPOSITORY_LOGIC", "stage": stage, "reason": reason,
            "required_actor": actor, "required_step": step, "repository_owner": owner}


def record_assistance(path: Path, *, actor: str, stage: str, step: str, owner: str,
                      before: str, during: str, after: str) -> Path:
    """Append a distinct immutable row without promoting assistance to native proof."""
    if actor not in {"human", "agent"} or not all(
        isinstance(value, str) and 0 < len(value.strip()) <= 500 for value in (stage, step, owner)
    ):
        raise ValueError("INVALID_ASSISTANCE_DESCRIPTION")
    refs = (before, during, after)
    if any(not REF_RE.fullmatch(ref) for ref in refs) or len(set(refs)) != len(refs):
        raise ValueError("DISTINCT_BEFORE_DURING_AFTER_CAPTURES_REQUIRED")
    if path.name != "launch.json" or path.is_symlink() or path.stat().st_size > LIMIT:
        raise ValueError("UNSAFE_PLAY_RECEIPT")
    receipt = json.loads(path.read_text(encoding="utf-8"))
    if (not isinstance(receipt, dict) or receipt.get("schema") != SCHEMA
            or path.parent.name != receipt.get("run_id")):
        raise ValueError("INVALID_PLAY_RECEIPT")
    row = {
        "schema": SCHEMA, "run_id": receipt["run_id"], "record_type": "ASSISTED_STEP",
        "observed_at": datetime.now(timezone.utc).isoformat(),
        **gap(stage, "ASSISTED_STEP_OBSERVED", step, owner, actor=actor),
        "before_ref": before, "during_ref": during, "after_ref": after,
        "proof_ceiling": "REPORTED_ASSISTANCE_NOT_HOST_AUTOMATION_OR_SAVE_PROOF",
    }
    from betterinstincts.control_handoff import HandoffError, _named_screen_lock

    target = path.parent / ("assistance-" + uuid4().hex + ".json")
    try:
        with _named_screen_lock("play-receipt-store.lock", lock_root=path.parent.parent.parent / "locks"):
            if has_reached_capacity(path.parent.glob("assistance-*.json"), MAX_ASSISTS_PER_LAUNCH):
                raise ValueError("PLAY_ASSISTANCE_STORE_FULL_ARCHIVE_OLDER_ENTRIES")
            write_result(target, row)
    except HandoffError as exc:
        raise ValueError("PLAY_RECEIPT_STORE_BUSY_RETRY") from exc
    return target


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", required=True, type=Path)
    parser.add_argument("--actor", required=True, choices=("human", "agent"))
    for field in ("stage", "step", "owner", "before", "during", "after"):
        parser.add_argument("--" + field, required=True)
    args = vars(parser.parse_args(argv))
    path = args.pop("receipt")
    try:
        print(record_assistance(path, **args))
    except (ValueError, OSError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
