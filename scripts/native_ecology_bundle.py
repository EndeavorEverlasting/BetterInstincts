"""Fail-closed, reversible packaging gate for a locally source-proven Sims ecology hook.

This is a developer BUILD/INSTALL tool, not a native hook. No runnable EA entry
point is bundled by this repository until local exact-patch source inspection.
Use Python 3.7 bytecode, explicit verified hook source and a disposable trial.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path

PROOF_SCHEMA = "betterinstincts.native-ecology-hook-proof/v1"
MOD_FILE = "BetterInstincts_Ecology.ts4script"
MANIFEST_FILE = "BetterInstincts_Ecology.ownership.json"
MODULE_PYC = "BetterInstincts_Ecology.pyc"
MAX_SOURCE_BYTES = 250_000
MAX_PYC_BYTES = 1_000_000


class NativeEcologyPackageError(ValueError):
    pass


def _hash(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _ref(value: object) -> bool:
    return isinstance(value, str) and 8 <= len(value) <= 500 and all(
        ord(ch) >= 32 for ch in value
    )


def verify_hook_proof(proof: object, *, source: bytes, game_build: str) -> dict:
    """Require explicit source-bound local hook evidence, not a guessed API."""
    if (not isinstance(proof, dict) or proof.get("schema") != PROOF_SCHEMA
            or proof.get("game_build") != game_build
            or not isinstance(game_build, str)
            or not game_build or game_build.lower() in {"unknown", "latest"}
            or proof.get("embedded_python") != "3.7"
            or proof.get("source_sha256") != _hash(source)
            or not _ref(proof.get("installed_ea_source_ref"))
            or not _ref(proof.get("native_event_signature_ref"))
            or not _ref(proof.get("native_queue_signature_ref"))
            or not _ref(proof.get("native_import_activation_ref"))
            or proof.get("player_preemption_verified") is not True):
        raise NativeEcologyPackageError("LOCAL_EA_HOOK_PROOF_REQUIRED")
    return proof


def _compile_py37(interpreter: Path, source: Path) -> bytes:
    if not interpreter.is_file() or not source.is_file():
        raise NativeEcologyPackageError("PY37_OR_SOURCE_MISSING")
    try:
        probe = subprocess.run(
            [str(interpreter), "-c",
             "import sys; print('{}.{}'.format(*sys.version_info[:2]))"],
            capture_output=True, text=True, check=True, timeout=12,
        )
        if probe.stdout.strip() != "3.7":
            raise NativeEcologyPackageError("PYTHON_3_7_REQUIRED")
        with tempfile.TemporaryDirectory(prefix="bi-ecology-bytecode-") as temp:
            output = Path(temp) / MODULE_PYC
            subprocess.run(
                [str(interpreter), "-c",
                 "import py_compile,sys;py_compile.compile(sys.argv[1],cfile=sys.argv[2],doraise=True)",
                 str(source), str(output)],
                capture_output=True, text=True, check=True, timeout=30,
            )
            payload = output.read_bytes()
    except (subprocess.SubprocessError, OSError) as exc:
        raise NativeEcologyPackageError("PY37_COMPILE_FAILED") from exc
    if not 16 <= len(payload) <= MAX_PYC_BYTES:
        raise NativeEcologyPackageError("PY37_BYTECODE_INVALID")
    return payload


def build_package(
    *, python37: Path, source_path: Path, hook_proof_path: Path,
    output_dir: Path, game_build: str,
) -> dict:
    """Compile an independently inspected hook, never arbitrary host policy."""
    if source_path.name != "BetterInstincts_Ecology.py":
        raise NativeEcologyPackageError("NATIVE_ENTRY_MODULE_NAME_REQUIRED")
    if source_path.is_symlink() or hook_proof_path.is_symlink():
        raise NativeEcologyPackageError("SOURCE_SYMLINK_DENIED")
    source = source_path.read_bytes()
    if not 1 <= len(source) <= MAX_SOURCE_BYTES:
        raise NativeEcologyPackageError("NATIVE_SOURCE_SIZE_INVALID")
    proof = verify_hook_proof(
        json.loads(hook_proof_path.read_text(encoding="utf-8")),
        source=source, game_build=game_build,
    )
    bytecode = _compile_py37(python37, source_path)
    if output_dir.is_symlink():
        raise NativeEcologyPackageError("OUTPUT_SYMLINK_DENIED")
    output_dir.mkdir(parents=True, exist_ok=True)
    package_path = output_dir / MOD_FILE
    receipt_path = output_dir / MANIFEST_FILE
    if package_path.exists() or receipt_path.exists():
        raise NativeEcologyPackageError("PACKAGE_OUTPUT_ALREADY_EXISTS")
    with tempfile.TemporaryDirectory(prefix="bi-ecology-package-") as temp:
        tmp = Path(temp) / MOD_FILE
        with zipfile.ZipFile(tmp, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr(MODULE_PYC, bytecode)
        with zipfile.ZipFile(tmp) as archive:
            if archive.namelist() != [MODULE_PYC]:
                raise NativeEcologyPackageError("PACKAGE_CONTENT_INVALID")
        package = tmp.read_bytes()
    receipt = {
        "schema": "betterinstincts.native-ecology-ownership/v1",
        "game_build": game_build,
        "package_sha256": _hash(package),
        "source_sha256": _hash(source),
        "hook_evidence_sha256": _hash(json.dumps(proof, sort_keys=True).encode("utf-8")),
        "module": MODULE_PYC,
        "game_certified": False,
        "live_activation_observed": False,
    }
    package_path.write_bytes(package)
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return {"package": str(package_path), "manifest": str(receipt_path),
            "sha256": receipt["package_sha256"],
            "proof": "BUILD_ONLY_NOT_NATIVE_GAME_ACTIVATION"}


def _read_manifest(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if (not isinstance(data, dict)
            or data.get("schema") != "betterinstincts.native-ecology-ownership/v1"
            or data.get("game_certified") is not False
            or data.get("live_activation_observed") is not False
            or not isinstance(data.get("package_sha256"), str)
            or len(data["package_sha256"]) != 64):
        raise NativeEcologyPackageError("OWNERSHIP_MANIFEST_INVALID")
    return data


def install_package(
    *, mods_dir: Path, package_path: Path, manifest_path: Path,
    game_closed_confirmed: bool,
) -> dict:
    """Install only to explicitly selected Mods path, never auto-discover hosts."""
    if not game_closed_confirmed:
        raise NativeEcologyPackageError("GAME_CLOSED_CONFIRMATION_REQUIRED")
    if (mods_dir.is_symlink() or not (mods_dir / "Resource.cfg").is_file()
            or package_path.is_symlink() or manifest_path.is_symlink()):
        raise NativeEcologyPackageError("MODS_LOCATION_OR_SOURCE_UNVERIFIED")
    receipt = _read_manifest(manifest_path)
    package = package_path.read_bytes()
    if _hash(package) != receipt["package_sha256"]:
        raise NativeEcologyPackageError("PACKAGE_HASH_MISMATCH")
    with zipfile.ZipFile(package_path) as archive:
        if archive.namelist() != [MODULE_PYC]:
            raise NativeEcologyPackageError("PACKAGE_CONTENT_INVALID")
    owned = mods_dir / "BetterInstincts"
    if owned.is_symlink() or (owned.exists() and list(owned.iterdir())):
        raise NativeEcologyPackageError("MODS_OWNERSHIP_COLLISION")
    owned.mkdir(exist_ok=True)
    installed = owned / MOD_FILE
    manifest = owned / MANIFEST_FILE
    try:
        installed.write_bytes(package)
        manifest.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
        if _hash(installed.read_bytes()) != receipt["package_sha256"]:
            raise NativeEcologyPackageError("INSTALL_READBACK_MISMATCH")
    except BaseException:
        installed.unlink(missing_ok=True)
        manifest.unlink(missing_ok=True)
        raise
    return {"installed": str(installed), "sha256": receipt["package_sha256"],
            "proof": "FILE_INSTALL_ONLY_GAME_ACTIVATION_UNPROVEN"}


def uninstall_package(*, mods_dir: Path, game_closed_confirmed: bool) -> dict:
    """Remove only unmodified installer-owned files; never touch other Mods."""
    if not game_closed_confirmed or mods_dir.is_symlink():
        raise NativeEcologyPackageError("GAME_CLOSED_CONFIRMATION_REQUIRED")
    owned = mods_dir / "BetterInstincts"
    if owned.is_symlink():
        raise NativeEcologyPackageError("MODS_OWNERSHIP_COLLISION")
    manifest = owned / MANIFEST_FILE
    installed = owned / MOD_FILE
    receipt = _read_manifest(manifest)
    if not installed.is_file() or _hash(installed.read_bytes()) != receipt["package_sha256"]:
        raise NativeEcologyPackageError("OWNED_PACKAGE_MODIFIED")
    installed.unlink()
    manifest.unlink()
    if not list(owned.iterdir()):
        owned.rmdir()
    return {"removed": str(installed), "proof": "OWNED_FILE_REMOVED_ONLY"}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Version-proven Sims ecology script package gate")
    commands = parser.add_subparsers(dest="command", required=True)
    build = commands.add_parser("build")
    for flag in ("python37", "source", "hook-proof", "output-dir", "game-build"):
        build.add_argument("--" + flag, required=True)
    install = commands.add_parser("install")
    for flag in ("mods-dir", "package", "manifest"):
        install.add_argument("--" + flag, required=True)
    install.add_argument("--confirm-game-closed", action="store_true")
    remove = commands.add_parser("uninstall")
    remove.add_argument("--mods-dir", required=True)
    remove.add_argument("--confirm-game-closed", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.command == "build":
            result = build_package(
                python37=Path(args.python37), source_path=Path(args.source),
                hook_proof_path=Path(args.hook_proof), output_dir=Path(args.output_dir),
                game_build=args.game_build,
            )
        elif args.command == "install":
            result = install_package(
                mods_dir=Path(args.mods_dir), package_path=Path(args.package),
                manifest_path=Path(args.manifest),
                game_closed_confirmed=args.confirm_game_closed,
            )
        else:
            result = uninstall_package(
                mods_dir=Path(args.mods_dir), game_closed_confirmed=args.confirm_game_closed,
            )
    except (NativeEcologyPackageError, OSError, ValueError, zipfile.BadZipFile) as exc:
        print("BLOCKED:", str(exc))
        return 2
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
