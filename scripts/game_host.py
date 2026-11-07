#!/usr/bin/env python3
"""Explicit Windows Sims 4 game-session adapter; no save edits or game API claims."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
import time

from betterinstincts.save_policy import SavePolicyError, selected_save_guard

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "dist" / "game-host"
RUN_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{1,49}$")
ALIAS_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{2,63}$")
REF_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_:.-]{2,119}$")
VERSION_RE = re.compile(r"^\d+\.\d+\.\d+\.\d+$")
EXE_NAMES = {"ts4_x64.exe", "ts4.exe"}
SCHEMA = "betterinstincts.game-host/v1"
METRICS = {"hunger", "bladder", "energy", "hygiene", "fun", "social",
           "funds", "skill", "action_queue_length", "sim_lag_ms"}
MAX_SAMPLE_BYTES = 65536
MAX_SAMPLE_ROWS = 64


class GateError(ValueError):
    """A validation or unproven-runtime gate; never interpreted as success."""


def run_root(run_id: str) -> Path:
    if not RUN_ID_RE.fullmatch(run_id):
        raise GateError("INVALID_RUN_ID")
    output = OUTPUT.resolve()
    dest = (OUTPUT / run_id).resolve()
    if not dest.is_relative_to(output):
        raise GateError("SESSION_PATH_ESCAPE")
    return dest


def profile(path: Path) -> tuple[dict, str]:
    raw = path.read_bytes()
    if len(raw) > 16384:
        raise GateError("PROFILE_TOO_LARGE")
    cfg = json.loads(raw)
    if cfg.get("schema") != SCHEMA or cfg.get("platform") != "windows":
        raise GateError("INVALID_PROFILE_SCHEMA_OR_PLATFORM")
    if cfg.get("save_mode") not in {"new", "chosen"}:
        raise GateError("INVALID_SAVE_MODE")
    if not ALIAS_RE.fullmatch(str(cfg.get("save_alias", ""))):
        raise GateError("DISPOSABLE_SAVE_ALIAS_REQUIRED")
    version = cfg.get("game_version")
    if version is not None and not VERSION_RE.fullmatch(str(version)):
        raise GateError("INVALID_FULL_GAME_VERSION")
    exe = Path(str(cfg.get("game_executable", "")))
    if not exe.is_absolute() or exe.name.lower() not in EXE_NAMES:
        raise GateError("EXPLICIT_SIMS_EXECUTABLE_REQUIRED")
    if not exe.is_file():
        raise GateError("GAME_EXECUTABLE_NOT_FOUND")
    templates = cfg.get("templates")
    if not isinstance(templates, dict):
        raise GateError("TEMPLATE_MAP_REQUIRED")
    required = (["new_game"] if cfg["save_mode"] == "new"
                else ["load_game", "save_tile", "play"])
    for name in required:
        rel = templates.get(name)
        if not isinstance(rel, str) or not rel.endswith(".png"):
            raise GateError("MISSING_TEMPLATE_" + name.upper())
        candidate = (path.resolve().parent / rel).resolve()
        # All UI templates live next to the explicit local profile, never in Git.
        if not candidate.is_relative_to(path.resolve().parent) or not candidate.is_file():
            raise GateError("INVALID_TEMPLATE_" + name.upper())
    return cfg, hashlib.sha256(raw).hexdigest()


def steps(cfg: dict) -> list[str]:
    return (["new_game"] if cfg["save_mode"] == "new"
            else ["load_game", "save_tile", "play"])


def plan(cfg: dict, digest: str) -> dict:
    return {"state": "PREFLIGHT_ONLY", "profile_sha256": digest,
            "mode": cfg["save_mode"], "save_alias": cfg["save_alias"],
            "game_version": cfg.get("game_version") or "UNKNOWN_VERSION",
            "exe_name": Path(cfg["game_executable"]).name,
            "ui_steps": steps(cfg),
            "proof_ceiling": "NO_GAME_LAUNCHED_NO_SAVE_SELECTED",
            "next": "launch --execute, then navigate --execute --disposable-confirmed"}


def append_event(root: Path, state: str, **data) -> dict:
    events = root / "events.jsonl"
    if events.is_symlink():
        raise GateError("EVENTS_SYMLINK_BLOCKED")
    if events.stat().st_size > 65536:
        raise GateError("EVENTS_LIMIT_EXCEEDED")
    row = {"schema": SCHEMA, "timestamp_utc": datetime.now(timezone.utc).isoformat(),
           "state": state, **data}
    with events.open("a", encoding="utf-8") as sink:
        sink.write(json.dumps(row, sort_keys=True) + "\n")
    return row


def load(run_id: str) -> tuple[Path, dict, list[dict]]:
    root = run_root(run_id)
    if root.is_symlink() or (root / "run.json").is_symlink() or (root / "events.jsonl").is_symlink():
        raise GateError("SESSION_SYMLINK_BLOCKED")
    if (root / "events.jsonl").stat().st_size > 65536:
        raise GateError("EVENTS_LIMIT_EXCEEDED")
    manifest = json.loads((root / "run.json").read_text(encoding="utf-8"))
    if manifest.get("schema") != SCHEMA or manifest.get("run_id") != run_id:
        raise GateError("INVALID_SESSION_MANIFEST")
    rows = [json.loads(s) for s in (root / "events.jsonl").read_text(encoding="utf-8").splitlines()]
    if len(rows) > 80 or not rows or any(r.get("schema") != SCHEMA for r in rows):
        raise GateError("INVALID_SESSION_EVENTS")
    return root, manifest, rows


def launch(run_id: str, cfg: dict, digest: str, execute: bool) -> dict:
    if not execute:
        raise GateError("LAUNCH_REQUIRES_EXPLICIT_EXECUTE")
    if sys.platform != "win32":
        raise GateError("LOCAL_WINDOWS_GAME_HOST_REQUIRED")
    root = run_root(run_id)
    root.mkdir(parents=True, exist_ok=False)
    manifest = {"schema": SCHEMA, "run_id": run_id, "profile_sha256": digest,
                "mode": cfg["save_mode"], "save_alias": cfg["save_alias"],
                "game_version": cfg.get("game_version"), "platform": "windows",
                "exe_name": Path(cfg["game_executable"]).name}
    (root / "run.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    (root / "events.jsonl").write_text("", encoding="utf-8")
    append_event(root, "SESSION_CREATED")
    exe = Path(cfg["game_executable"])
    try:
        proc = subprocess.Popen([str(exe)], cwd=str(exe.parent),
                                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL, close_fds=True)
    except OSError as exc:
        append_event(root, "LAUNCH_FAILED", reason=type(exc).__name__)
        raise GateError("GAME_LAUNCH_FAILED") from exc
    return append_event(root, "LAUNCH_DISPATCHED",
                        process_id=proc.pid, proof_ceiling="PROCESS_DISPATCH_ONLY")


def navigate(run_id: str, cfg: dict, digest: str, execute: bool,
             disposable_confirmed: bool, timeout: int = 45, gui=None) -> dict:
    if not execute or not disposable_confirmed:
        raise GateError("NAVIGATION_REQUIRES_EXECUTE_AND_DISPOSABLE_SAVE_CONFIRMATION")
    if not 1 <= timeout <= 90:
        raise GateError("INVALID_UI_TIMEOUT")
    root, meta, rows = load(run_id)
    if meta["profile_sha256"] != digest or meta["mode"] != cfg["save_mode"]:
        raise GateError("PROFILE_CHANGED_SINCE_LAUNCH")
    if rows[-1]["state"] != "LAUNCH_DISPATCHED":
        raise GateError("LAUNCH_DISPATCH_REQUIRED")
    # Before even opening Load Game, require exact binding to an operator-attested
    # lab-origin slot. A lab-style name, title screenshot or boolean alone is not proof.
    if cfg["save_mode"] == "chosen":
        try:
            selected_save_guard(cfg, run_id)
        except SavePolicyError as exc:
            raise GateError("SAVE_SELECTION_PROTECTED:" + str(exc)) from exc
    if gui is None:
        if sys.platform != "win32":
            raise GateError("LOCAL_WINDOWS_GUI_REQUIRED")
        try:
            import pyautogui as gui
        except ImportError as exc:
            raise GateError("PYAutoGUI_NOT_INSTALLED") from exc
    gui.FAILSAFE = True
    gui.PAUSE = 0.3
    base = Path(cfg["_profile_path"]).resolve().parent
    for step in steps(cfg):
        template = str((base / cfg["templates"][step]).resolve())
        deadline = time.monotonic() + timeout
        found = None
        while time.monotonic() < deadline:
            try:
                matches = list(gui.locateAllOnScreen(template, grayscale=False))
            except Exception as exc:
                if type(exc).__name__ == "ImageNotFoundException":
                    matches = []
                else:
                    raise GateError("UI_IMAGE_MATCH_ERROR") from exc
            if len(matches) > 1:
                raise GateError("AMBIGUOUS_UI_TARGET_" + step.upper())
            if len(matches) == 1:
                found = matches[0]
                break
            time.sleep(0.5)
        if found is None:
            raise GateError("UI_TARGET_TIMEOUT_" + step.upper())
        gui.click(gui.center(found))
        # Durable per-click checkpoint: never replay a partly completed UI flow.
        append_event(root, "UI_CLICK_DISPATCHED", ui_step=step,
                     proof_ceiling="CLICK_DISPATCH_ONLY")
    state = ("NEW_GAME_CAS_REQUESTED" if cfg["save_mode"] == "new"
             else "CHOSEN_SAVE_PLAY_REQUESTED")
    return append_event(root, state, ui_steps=steps(cfg),
                        proof_ceiling="UI_CLICK_DISPATCH_ONLY")


def confirm(run_id: str, capture_ref: str, game_version: str | None,
            disposable_confirmed: bool) -> dict:
    if not disposable_confirmed:
        raise GateError("DISPOSABLE_SAVE_CONFIRMATION_REQUIRED")
    if not REF_RE.fullmatch(capture_ref):
        raise GateError("INVALID_CAPTURE_REFERENCE")
    if not game_version or not VERSION_RE.fullmatch(game_version):
        raise GateError("EXACT_GAME_VERSION_REQUIRED")
    root, meta, rows = load(run_id)
    if rows[-1]["state"] not in {"CHOSEN_SAVE_PLAY_REQUESTED", "NEW_GAME_CAS_REQUESTED",
                                  "LIVE_REPORTED_UNREVIEWED"}:
        raise GateError("NAVIGATION_NOT_PROVEN")
    if meta["game_version"] and meta["game_version"] != game_version:
        raise GateError("GAME_VERSION_MISMATCH")
    return append_event(root, "LIVE_REPORTED_UNREVIEWED", capture_ref=capture_ref,
                        game_version=game_version,
                        proof_ceiling="OPERATOR_ATTESTATION_NOT_INDEPENDENT_GAME_PROOF")


def poll(run_id: str, sample_file: Path) -> dict:
    root, _, rows = load(run_id)
    if rows[-1]["state"] not in {"LIVE_REPORTED_UNREVIEWED", "SAMPLE_INGESTED_UNVERIFIED"}:
        raise GateError("LIVE_OBSERVATION_GATE_REQUIRED")
    if sample_file.is_symlink() or sample_file.stat().st_size > MAX_SAMPLE_BYTES:
        raise GateError("SAMPLE_FILE_UNSAFE_OR_TOO_LARGE")
    raw = sample_file.read_bytes()
    lines = raw.decode("utf-8").splitlines()
    if not 1 <= len(lines) <= MAX_SAMPLE_ROWS:
        raise GateError("SAMPLE_ROW_COUNT_INVALID")
    checked = []
    for line in lines:
        r = json.loads(line)
        if r.get("schema") != "betterinstincts.object-sample/v1":
            raise GateError("SAMPLE_SCHEMA_INVALID")
        if r.get("metric") not in METRICS or not REF_RE.fullmatch(str(r.get("object_key", ""))):
            raise GateError("UNSAFE_SAMPLE_FIELDS")
        value = r.get("value")
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise GateError("INVALID_SAMPLE_VALUE")
        if not -1000000000 <= value <= 1000000000:
            raise GateError("SAMPLE_VALUE_OUT_OF_BOUNDS")
        if set(r) != {"schema", "object_key", "metric", "value", "captured_at"}:
            raise GateError("SAMPLE_FIELDS_NOT_ALLOWLISTED")
        if not isinstance(r["captured_at"], str) or len(r["captured_at"]) > 50:
            raise GateError("SAMPLE_TIMESTAMP_INVALID")
        checked.append(r["metric"])
    return append_event(root, "SAMPLE_INGESTED_UNVERIFIED",
                        sample_sha256=hashlib.sha256(raw).hexdigest(),
                        samples=len(checked), metrics=sorted(set(checked)),
                        proof_ceiling="EXTERNAL_SAMPLE_NOT_GAME_API_PROOF")


def status(run_id: str) -> dict:
    _, meta, rows = load(run_id)
    observed_version = next(
        (row["game_version"] for row in reversed(rows)
         if row["state"] == "LIVE_REPORTED_UNREVIEWED"), None)
    return {"run_id": run_id, "mode": meta["mode"],
            "save_alias": meta["save_alias"], "state": rows[-1]["state"],
            "events": len(rows),
            "game_version": observed_version or meta["game_version"] or "UNKNOWN_VERSION",
            "game_certification": "NOT_GRANTED_BY_HOST_ADAPTER"}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("plan", "launch", "navigate"):
        p = sub.add_parser(name)
        p.add_argument("--profile", type=Path, required=True)
        if name != "plan":
            p.add_argument("--run-id", required=True)
            p.add_argument("--execute", action="store_true")
        if name == "navigate":
            p.add_argument("--disposable-confirmed", action="store_true")
            p.add_argument("--timeout", type=int, default=45)
    p = sub.add_parser("confirm")
    p.add_argument("--run-id", required=True)
    p.add_argument("--capture-ref", required=True)
    p.add_argument("--game-version", required=True)
    p.add_argument("--disposable-confirmed", action="store_true")
    p = sub.add_parser("poll")
    p.add_argument("--run-id", required=True)
    p.add_argument("--sample-file", required=True, type=Path)
    sub.add_parser("status").add_argument("--run-id", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command in ("plan", "launch", "navigate"):
            cfg, digest = profile(args.profile)
            cfg["_profile_path"] = str(args.profile)
            if args.command == "plan":
                result = plan(cfg, digest)
            elif args.command == "launch":
                result = launch(args.run_id, cfg, digest, args.execute)
            else:
                result = navigate(args.run_id, cfg, digest, args.execute,
                                  args.disposable_confirmed, args.timeout)
        elif args.command == "confirm":
            result = confirm(args.run_id, args.capture_ref, args.game_version,
                             args.disposable_confirmed)
        elif args.command == "poll":
            result = poll(args.run_id, args.sample_file)
        else:
            result = status(args.run_id)
    except (GateError, FileExistsError, FileNotFoundError, OSError,
            ValueError, UnicodeError, KeyError, TypeError) as exc:
        print(json.dumps({"state": "BLOCKED", "reason": str(exc)}, sort_keys=True))
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
