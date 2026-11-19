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
RUNTIME_MODULES = ("__init__", "installed_player_runtime", "player_learning",
                   "judgment_learning", "priority", "installation_profiles")
LAUNCH_PROFILE_CATALOG = "betterinstincts/installation-profiles.v1.json"
RUNTIME_MEMBERS = tuple(f"betterinstincts/{name}.pyc" for name in RUNTIME_MODULES) + (LAUNCH_PROFILE_CATALOG,)
TRAIT_MODULES = ("preference_prompts", "preference_native_map", "preference_response_port")
TRAIT_CATALOG = "betterinstincts/preference-prompts.v1.json"
TRAIT_MEMBERS = tuple(f"betterinstincts/{name}.pyc" for name in TRAIT_MODULES) + (TRAIT_CATALOG,)
FAIRY_DUST_MEMBER = "betterinstincts/fairy_dust.pyc"
FAME_MEMBER = "betterinstincts/fame.pyc"
PORTRAIT_MEMBER = "betterinstincts/portrait_handoff.pyc"
ACTIVITY_CHAIN_MODULES = ("activity_chain", "household_funds")
ACTIVITY_CHAIN_MEMBERS = tuple(f"betterinstincts/{name}.pyc" for name in ACTIVITY_CHAIN_MODULES)
MICROSYSTEM_MEMBER = "betterinstincts/microsystem_handoff.pyc"
RUNTIME_SEAM_MEMBER = "betterinstincts/runtime_seam.pyc"
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
    output_dir: Path, game_build: str, installed_player_runtime: bool = False,
    installed_trait_responder: bool = False, installed_fairy_dust: bool = False,
    installed_fame: bool = False, installed_portrait_handoff: bool = False,
    installed_activity_chain: bool = False, installed_microsystem_handoff: bool = False,
    installed_runtime_seam_port: bool = False,
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
    if installed_player_runtime and not _ref(proof.get("installed_player_runtime_binding_ref")):
        raise NativeEcologyPackageError("INSTALLED_PLAYER_RUNTIME_BINDING_PROOF_REQUIRED")
    if installed_trait_responder and (not installed_player_runtime
            or not _ref(proof.get("installed_trait_responder_binding_ref"))):
        raise NativeEcologyPackageError("INSTALLED_TRAIT_RESPONDER_BINDING_PROOF_REQUIRED")
    if installed_fairy_dust and (not installed_player_runtime
            or not _ref(proof.get("installed_fairy_dust_binding_ref"))):
        raise NativeEcologyPackageError("INSTALLED_FAIRY_DUST_BINDING_PROOF_REQUIRED")
    if installed_fame and (not installed_player_runtime
            or not _ref(proof.get("installed_fame_binding_ref"))):
        raise NativeEcologyPackageError("INSTALLED_FAME_BINDING_PROOF_REQUIRED")
    if installed_portrait_handoff and (not installed_player_runtime
            or not _ref(proof.get("installed_portrait_handoff_binding_ref"))):
        raise NativeEcologyPackageError("INSTALLED_PORTRAIT_HANDOFF_BINDING_PROOF_REQUIRED")
    if installed_activity_chain and (not installed_player_runtime
            or not _ref(proof.get("installed_activity_chain_binding_ref"))):
        raise NativeEcologyPackageError("INSTALLED_ACTIVITY_CHAIN_BINDING_PROOF_REQUIRED")
    if installed_microsystem_handoff and (not installed_portrait_handoff
            or not _ref(proof.get("installed_microsystem_handoff_binding_ref"))):
        raise NativeEcologyPackageError("INSTALLED_MICROSYSTEM_HANDOFF_BINDING_PROOF_REQUIRED")
    if installed_runtime_seam_port and (not installed_player_runtime
            or not _ref(proof.get("installed_runtime_seam_port_binding_ref"))):
        raise NativeEcologyPackageError("INSTALLED_RUNTIME_SEAM_PORT_BINDING_PROOF_REQUIRED")
    modules = {MODULE_PYC: _compile_py37(python37, source_path)}
    if installed_player_runtime:
        root = Path(__file__).resolve().parents[1] / "betterinstincts"
        for name, member in zip(RUNTIME_MODULES, RUNTIME_MEMBERS):
            modules[member] = _compile_py37(python37, root / (name + ".py"))
        modules[LAUNCH_PROFILE_CATALOG] = (root.parent / "contracts" / "installation-profiles.v1.json").read_bytes()
        if installed_trait_responder:
            for name, member in zip(TRAIT_MODULES, TRAIT_MEMBERS):
                modules[member] = _compile_py37(python37, root / (name + ".py"))
            modules[TRAIT_CATALOG] = (root.parent / "contracts" / "preference-prompts.v1.json").read_bytes()
        if installed_fairy_dust:
            modules[FAIRY_DUST_MEMBER] = _compile_py37(python37, root / "fairy_dust.py")
        if installed_fame:
            modules[FAME_MEMBER] = _compile_py37(python37, root / "fame.py")
        if installed_portrait_handoff:
            modules[PORTRAIT_MEMBER] = _compile_py37(python37, root / "portrait_handoff.py")
        if installed_activity_chain:
            for name, member in zip(ACTIVITY_CHAIN_MODULES, ACTIVITY_CHAIN_MEMBERS):
                modules[member] = _compile_py37(python37, root / (name + ".py"))
        if installed_microsystem_handoff:
            modules[MICROSYSTEM_MEMBER] = _compile_py37(python37, root / "microsystem_handoff.py")
        if installed_runtime_seam_port:
            modules[RUNTIME_SEAM_MEMBER] = _compile_py37(python37, root / "runtime_seam.py")
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
            for member, bytecode in modules.items():
                archive.writestr(member, bytecode)
        _check_archive(tmp, installed_player_runtime, installed_trait_responder,
                       installed_fairy_dust, installed_fame, installed_portrait_handoff,
                       installed_activity_chain, installed_microsystem_handoff,
                       installed_runtime_seam_port)
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
    if installed_player_runtime:
        receipt["installed_player_runtime"] = True
    if installed_trait_responder:
        receipt["installed_trait_responder"] = True
    if installed_fairy_dust:
        receipt["installed_fairy_dust"] = True
    if installed_fame:
        receipt["installed_fame"] = True
    if installed_portrait_handoff:
        receipt["installed_portrait_handoff"] = True
    if installed_activity_chain:
        receipt["installed_activity_chain"] = True
    if installed_microsystem_handoff:
        receipt["installed_microsystem_handoff"] = True
    if installed_runtime_seam_port:
        receipt["installed_runtime_seam_port"] = True
    package_path.write_bytes(package)
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return {"package": str(package_path), "manifest": str(receipt_path),
            "sha256": receipt["package_sha256"],
            "proof": "BUILD_ONLY_NOT_NATIVE_GAME_ACTIVATION"}


def _check_archive(path: Path, installed_runtime: bool, installed_trait: bool = False,
                   installed_fairy_dust: bool = False, installed_fame: bool = False,
                   installed_portrait_handoff: bool = False, installed_activity_chain: bool = False,
                   installed_microsystem_handoff: bool = False,
                   installed_runtime_seam_port: bool = False) -> None:
    expected = [MODULE_PYC, *(RUNTIME_MEMBERS if installed_runtime else ()),
                *(TRAIT_MEMBERS if installed_trait else ()),
                *([FAIRY_DUST_MEMBER] if installed_fairy_dust else []),
                *([FAME_MEMBER] if installed_fame else []),
                *([PORTRAIT_MEMBER] if installed_portrait_handoff else []),
                *(ACTIVITY_CHAIN_MEMBERS if installed_activity_chain else ()),
                *([MICROSYSTEM_MEMBER] if installed_microsystem_handoff else []),
                *([RUNTIME_SEAM_MEMBER] if installed_runtime_seam_port else [])]
    with zipfile.ZipFile(path) as archive:
        members = archive.namelist()
        legacy = [member for member in expected if member not in RUNTIME_MEMBERS[-2:]]
        if members != expected and members != legacy:
            raise NativeEcologyPackageError("PACKAGE_CONTENT_INVALID")


def _read_manifest(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if (not isinstance(data, dict)
            or data.get("schema") != "betterinstincts.native-ecology-ownership/v1"
            or (any(data.get(key) is True for key in
                    ("installed_trait_responder", "installed_fairy_dust", "installed_fame",
                     "installed_portrait_handoff", "installed_activity_chain",
                     "installed_runtime_seam_port"))
                and data.get("installed_player_runtime") is not True)
            or (data.get("installed_microsystem_handoff") is True
                and data.get("installed_portrait_handoff") is not True)
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
    _check_archive(package_path, receipt.get("installed_player_runtime") is True,
                   receipt.get("installed_trait_responder") is True,
                   receipt.get("installed_fairy_dust") is True, receipt.get("installed_fame") is True,
                   receipt.get("installed_portrait_handoff") is True,
                   receipt.get("installed_activity_chain") is True,
                   receipt.get("installed_microsystem_handoff") is True,
                   receipt.get("installed_runtime_seam_port") is True)
    owned = mods_dir / "BetterInstincts"
    if owned.is_symlink() or (owned.exists() and any(
        not (item.name == "player-learning.sqlite3" and item.is_file() and not item.is_symlink()
             and receipt.get("installed_player_runtime") is True)
        for item in owned.iterdir()
    )):
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
    build.add_argument("--installed-player-runtime", action="store_true",
                       help="Include the listener and gate for a source-proven native binding")
    build.add_argument("--installed-trait-responder", action="store_true",
                       help="Include the exact-build, adapter-bound trait decline handler")
    build.add_argument("--installed-fairy-dust", action="store_true",
                       help="Include the exact-build, adapter-bound Fairy Dust policy")
    build.add_argument("--installed-fame", action="store_true",
                       help="Include the exact-build, adapter-bound Fame microsystem")
    build.add_argument("--installed-portrait-handoff", action="store_true",
                       help="Include shared portrait selection for a source-proven native binding")
    build.add_argument("--installed-activity-chain", action="store_true",
                       help="Include the activity planner for a source-proven native chain binding")
    build.add_argument("--installed-microsystem-handoff", action="store_true",
                       help="Include household queue arbitration for a source-proven native binding")
    build.add_argument("--installed-runtime-seam-port", action="store_true",
                       help="Include advisory runtime notices for a source-proven adapter port")
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
                game_build=args.game_build, installed_player_runtime=args.installed_player_runtime,
                installed_trait_responder=args.installed_trait_responder,
                installed_fairy_dust=args.installed_fairy_dust, installed_fame=args.installed_fame,
                installed_portrait_handoff=args.installed_portrait_handoff,
                installed_activity_chain=args.installed_activity_chain,
                installed_microsystem_handoff=args.installed_microsystem_handoff,
                installed_runtime_seam_port=args.installed_runtime_seam_port,
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
