#!/usr/bin/env python3
"""Cursor project pre-effect guard for operator desktop and saved data.

This is a project hook, not a Windows security boundary. Never changes
services, HID devices, input settings, game state, or OS files itself.
No prompt/body/file contents are logged. All decisions are side-effect free.
"""
from __future__ import annotations

import json
import ntpath
import os
from pathlib import Path
import re
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
MAX_PAYLOAD = 65536
MAX_COMMAND = 8192

# Only exact offline diagnostics are allowed. Interpreters, pipelines, file
# mutation, arbitrary shell execution and unknown commands are refused.
SAFE_SHELL = (
    re.compile(r"git\s+status(?:\s+(?:--short|--porcelain(?:=v[12])?|--branch))*", re.I),
    re.compile(r"git\s+diff(?:\s+(?:--check|--stat|--name-only|--cached|--staged))*", re.I),
    re.compile(r"git\s+log(?:\s+(?:--oneline|--stat|--decorate|-n\s+[1-9][0-9]?))*", re.I),
    re.compile(r"git\s+rev-parse\s+(?:HEAD|--show-toplevel|--abbrev-ref\s+HEAD)", re.I),
    re.compile(r"git\s+branch\s+--show-current", re.I),
    re.compile(r"git\s+ls-files", re.I),
    re.compile(r"(?:python|python3|py\s+-3)(?:\s+-B)?\s+-m\s+unittest(?:\s+discover(?:\s+-s\s+tests)?(?:\s+-v)?)?", re.I),
    re.compile(r"(?:python|python3|py\s+-3)(?:\s+-B)?\s+-m\s+scripts\.(?:check_ontology|validate_doctrine|check_scene_contract|check_horizon)", re.I),
    re.compile(r"(?:python|python3|py\s+-3)(?:\s+-B)?\s+-m\s+scripts\.check_peripheral_boundary", re.I),
    re.compile(r"(?:python|python3|py\s+-3)(?:\s+-B)?\s+-m\s+unittest\s+tests\.test_(?:peripheral_boundary|operator_boundary)(?:\s+-v)?", re.I),
    re.compile(r"(?:pwd|ls|dir|Get-Location)", re.I),
)

# Agent cannot remove its own policy through ordinary project Write tools.
POLICY_FILES = {
    "agents.md",
    ".cursor/hooks.json",
    ".cursor/hooks/operator_boundary.py",
    "contracts/operator-desktop-boundary.v1.json",
}


def _decision(allowed: bool, reason: str) -> dict[str, str]:
    if allowed:
        return {"permission": "allow"}
    msg = ("OPERATOR_DESKTOP_BOUNDARY:" + reason + ". Agent action denied; "
           "use an independently reviewed scope and operator-controlled "
           "execution path. Never reset input devices or mutate saves to fix capture.")
    return {"permission": "deny", "user_message": msg, "agent_message": msg}


def _safe_shell(command: Any) -> dict[str, str]:
    if not isinstance(command, str) or not command.strip() or len(command) > MAX_COMMAND:
        return _decision(False, "MISSING_OR_OVERSIZED_COMMAND")
    cmd = command.strip()
    if any(c in cmd for c in ("\n", "\r", "\x00", ";", "|", "&", ">", "<", chr(96), "$", "(", ")", "{", "}")):
        return _decision(False, "SHELL_COMPOSITION_DENIED")
    if any(p.fullmatch(cmd) for p in SAFE_SHELL):
        return _decision(True, "SAFE_READ_OR_TEST")
    return _decision(False, "SHELL_NOT_IN_SAFE_ALLOWLIST")


def _scope(path: Any, root: str | Path) -> tuple[bool, str]:
    if not isinstance(path, str) or not path.strip() or len(path) > 4096 or "\x00" in path:
        return False, "MISSING_OR_INVALID_PATH"
    root_s = str(root)
    # Reject Windows absolute paths when regression tests run on Linux.
    if os.name != "nt" and not ntpath.splitdrive(root_s)[0] and ntpath.splitdrive(path)[0]:
        return False, "OUTSIDE_REPOSITORY_OR_SYMLINK_ESCAPE"
    if os.name == "nt" or ntpath.splitdrive(root_s)[0]:
        if os.name == "nt":
            base = Path(root_s).resolve()
            target = (Path(path) if Path(path).is_absolute() else base / path).resolve()
            inside = target == base or base in target.parents
            rel = target.relative_to(base).as_posix().lower() if inside else ""
        else:
            base = ntpath.normcase(ntpath.normpath(root_s))
            target = ntpath.normcase(ntpath.normpath(path if ntpath.isabs(path) else ntpath.join(base, path)))
            inside = target.startswith(base + "\\")
            rel = target[len(base) + 1:].replace("\\", "/") if inside else ""
    else:
        base = Path(root_s).resolve()
        target = (Path(path) if Path(path).is_absolute() else base / path).resolve()
        inside = target != base and base in target.parents
        rel = target.relative_to(base).as_posix().lower() if inside else ""
    if not inside or not rel:
        return False, "OUTSIDE_REPOSITORY_OR_SYMLINK_ESCAPE"
    if rel in POLICY_FILES:
        return False, "GUARD_POLICY_SELF_MUTATION"
    # Protect local execution controls and secrets, not just this hook file.
    # A path must remain inside the repo AND outside protected subtrees.
    if (rel == ".git" or rel.startswith(".git/")
            or rel == ".cursor" or rel.startswith(".cursor/")
            or rel.startswith(".github/workflows/")
            or any(part == ".env" or part.startswith(".env.") for part in rel.split("/"))
            or rel.endswith((".pem", ".p12", ".pfx", ".key"))):
        return False, "HARNESS_OR_SECRET_MUTATION"
    return True, "REPOSITORY_SCOPED_WRITE"


def evaluate(payload: dict[str, Any], *, root: str | Path = ROOT) -> dict[str, str]:
    if not isinstance(payload, dict):
        return _decision(False, "INVALID_HOOK_PAYLOAD")
    event = payload.get("hook_event_name")
    if event == "beforeShellExecution" or (event is None and "command" in payload):
        return _safe_shell(payload.get("command"))
    if event == "preToolUse" or "tool_name" in payload:
        tool = str(payload.get("tool_name", "")).strip().lower()
        arguments = payload.get("tool_input")
        if tool in {"shell", "terminal", "run_command", "bash", "powershell"}:
            if not isinstance(arguments, dict):
                return _decision(False, "SHELL_ARGUMENTS_UNKNOWN")
            return _safe_shell(arguments.get("command"))
        if tool in {"delete", "deletefile", "removefile", "delete_file"}:
            return _decision(False, "AGENT_FILE_DELETION_DENIED")
        if tool in {"write", "edit", "edit_file", "applypatch", "apply_patch", "write_file"}:
            if not isinstance(arguments, dict):
                return _decision(False, "WRITE_ARGUMENTS_UNKNOWN")
            target = next((arguments[k] for k in ("file_path", "path", "target_path") if k in arguments), None)
            allowed, reason = _scope(target, root)
            return _decision(allowed, reason)
        # This hook only subscribes to effectful tool classes. Unrecognized
        # names (including WriteFile or a renamed executor) cannot bypass it.
        return _decision(False, "UNRECOGNIZED_EFFECTFUL_TOOL")
    return _decision(False, "UNRECOGNIZED_HOOK_EVENT")


def main() -> int:
    try:
        raw = sys.stdin.buffer.read(MAX_PAYLOAD + 1)
        if len(raw) > MAX_PAYLOAD:
            result = _decision(False, "HOOK_PAYLOAD_TOO_LARGE")
        else:
            obj = json.loads(raw.decode("utf-8-sig"))
            result = evaluate(obj)
    except (UnicodeError, ValueError, TypeError, OSError):
        result = _decision(False, "MALFORMED_HOOK_INPUT")
    print(json.dumps(result, ensure_ascii=True, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
