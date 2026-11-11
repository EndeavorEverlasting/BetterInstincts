"""P01 completeness/coverage check for BetterInstincts human-first operation.

Repository-static policy verification; not a Windows security sandbox or an
assertion that an independently running Cursor agent has adopted the policy.
"""
from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = Path("contracts/human-first-harness.v1.json")
SCHEMA = "betterinstincts.human-first-harness/v1"
KINDS = {"SCREEN_EFFECT", "PASSIVE_OBSERVATION", "OS_CONFIGURATION", "POLICY"}
STATUSES = {
    "STATIC_POLICY_ONLY", "ADOPTED_GATED", "ADOPTED_READ_ONLY_WITH_CALLBACK_TRUST",
    "ADOPTED_PASSIVE_CAPTURE", "MIXED_PATHS_REVIEW_REQUIRED",
    "UNADOPTED_LEGACY_NO_LIVE_AUTHORITY", "LOW_LEVEL_CALLER_GATE_ONLY",
    "REPOSITORY_HOOK_UNVERIFIED_LOCAL_ACTIVATION", "STATIC_DENY_ONLY",
    "READ_ONLY_PRESENCE_SENSOR",
}
NOT_PROVED = {
    "MIXED_PATHS_REVIEW_REQUIRED", "UNADOPTED_LEGACY_NO_LIVE_AUTHORITY",
    "LOW_LEVEL_CALLER_GATE_ONLY", "REPOSITORY_HOOK_UNVERIFIED_LOCAL_ACTIVATION",
}
ONTOLOGY_IDS = {f"BI-ONT-{n:03}" for n in range(31, 36)}
CONCEPTS = {
    "EFFECT_ADMISSION_CLASS", "PASSIVE_BACKGROUND_LANE", "HUMAN_CONTROL_RECLAIM",
    "OS_INPUT_CAPABILITY", "AGENT_ADOPTION_COVERAGE",
}


class HarnessCoverageError(ValueError):
    pass


def _file(root: Path, path: str) -> Path:
    if not isinstance(path, str) or not path:
        raise HarnessCoverageError("INVALID_PATH:" + str(path))
    p = Path(path)
    if p.is_absolute() or ".." in p.parts:
        raise HarnessCoverageError("INVALID_PATH:" + str(path))
    target = root / p
    if target.is_symlink() or not target.is_file():
        raise HarnessCoverageError("REQUIRED_PATH_MISSING:" + path)
    return target


def validate_manifest(manifest: dict, root: Path = ROOT) -> dict:
    if not isinstance(manifest, dict) or manifest.get("schema") != SCHEMA:
        raise HarnessCoverageError("HARNESS_SCHEMA_INVALID")
    root = Path(root)
    for key in (
        "canonical_governance", "doctrine", "ontology", "glossary", "effect_authority",
        "presence_owner", "admission_owner", "background_owner",
        "operator_desktop_guard", "host_settings_guard", "path_contract", "path_resolver",
        "harness_validator", "scoped_skill", "operator_report", "ci_workflow",
    ):
        _file(root, manifest.get(key))
    ontology = json.loads(_file(root, manifest["ontology"]).read_text(encoding="utf-8"))
    glossary = json.loads(_file(root, manifest["glossary"]).read_text(encoding="utf-8"))
    authority = json.loads(_file(root, manifest["effect_authority"]).read_text(encoding="utf-8"))
    if ontology.get("revision", 0) < 5 or not CONCEPTS.issubset(ontology.get("concepts", {})):
        raise HarnessCoverageError("P00_ONTOLOGY_CONCEPTS_MISSING")
    if not ONTOLOGY_IDS.issubset({x.get("id") for x in ontology.get("invariants", [])}):
        raise HarnessCoverageError("P00_ONTOLOGY_INVARIANTS_MISSING")
    if not CONCEPTS.issubset(glossary.get("terms", {})):
        raise HarnessCoverageError("P00_GLOSSARY_MISSING")
    classes = authority.get("effect_classes", {})
    if set(classes) != {
        "SCREEN_EFFECT", "GAME_MUTATION", "PASSIVE_OBSERVATION",
        "BACKGROUND_REASONING", "OS_CONFIGURATION",
    } or classes["OS_CONFIGURATION"].get("decision") != "ALWAYS_DENY":
        raise HarnessCoverageError("EFFECT_AUTHORITY_TAXONOMY_BYPASS")
    if classes["SCREEN_EFFECT"].get("operator_idle_required") is not True or classes["GAME_MUTATION"].get("operator_idle_required") is not True:
        raise HarnessCoverageError("GAME_OR_SCREEN_IDLE_GATE_MISSING")
    if classes["PASSIVE_OBSERVATION"].get("screen") is not False or classes["BACKGROUND_REASONING"].get("screen") is not False:
        raise HarnessCoverageError("BACKGROUND_CLASS_ESCALATED_TO_SCREEN")
    if authority.get("unknown") != "DENY":
        raise HarnessCoverageError("UNKNOWN_EFFECT_MUST_DENY")
    ci = _file(root, manifest["ci_workflow"]).read_text(encoding="utf-8")
    if "python -m scripts.check_human_sovereignty" not in ci or "python -m scripts.check_peripheral_boundary" not in ci:
        raise HarnessCoverageError("CI_ENFORCEMENT_WIRING_MISSING")
    agents = _file(root, manifest["canonical_governance"]).read_text(encoding="utf-8")
    doctrine = _file(root, manifest["doctrine"]).read_text(encoding="utf-8")
    if len(agents) > 3600 or any(k not in agents for k in ("P00/P01 interaction sovereignty","check_human_sovereignty.py","Print Screen")):
        raise HarnessCoverageError("GOVERNANCE_ROUTING_MISSING_OR_OVERSIZED")
    if any(k not in doctrine for k in ("EFFECT_ADMISSION_CLASS","PASSIVE_OBSERVATION","SCREEN_EFFECT","OS_CONFIGURATION","BI-002")):
        raise HarnessCoverageError("DOCTRINE_HUMAN_FIRST_COVERAGE_MISSING")
    sources = manifest.get("sources")
    if not isinstance(sources, list) or not sources:
        raise HarnessCoverageError("NO_ADAPTER_INVENTORY")
    seen: set[str] = set()
    unproven: list[str] = []
    for entry in sources:
        if not isinstance(entry, dict):
            raise HarnessCoverageError("INVALID_ADAPTER")
        path, kind, status, marker = (entry.get(x) for x in ("path","classification","status","marker"))
        if not isinstance(path, str) or path in seen:
            raise HarnessCoverageError("DUPLICATED_OR_UNKNOWN_ADAPTER")
        seen.add(path)
        if kind not in KINDS or status not in STATUSES or not isinstance(marker, str) or not marker:
            raise HarnessCoverageError("UNCLASSIFIED_ADAPTER:" + path)
        source = _file(root, path).read_text(encoding="utf-8")
        if marker not in source:
            raise HarnessCoverageError("ADAPTER_ADMISSION_ANCHOR_MISSING:" + path)
        if kind == "OS_CONFIGURATION" and status not in {
            "REPOSITORY_HOOK_UNVERIFIED_LOCAL_ACTIVATION", "STATIC_DENY_ONLY",
        }:
            raise HarnessCoverageError("HOST_OS_AUTHORITY_ESCALATED:" + path)
        if kind == "SCREEN_EFFECT" and status in {"ADOPTED_READ_ONLY_WITH_CALLBACK_TRUST","ADOPTED_PASSIVE_CAPTURE"}:
            raise HarnessCoverageError("SCREEN_EFFECT_AS_BACKGROUND:" + path)
        if kind == "PASSIVE_OBSERVATION" and status not in {
            "ADOPTED_PASSIVE_CAPTURE", "ADOPTED_READ_ONLY_WITH_CALLBACK_TRUST",
            "READ_ONLY_PRESENCE_SENSOR",
        }:
            raise HarnessCoverageError("BACKGROUND_REVIEW_REQUIRED:" + path)
        if kind == "PASSIVE_OBSERVATION" and _has_call(
            source, {"SendInput", "SetCursorPos", "SetForegroundWindow", "keybd_event"}
        ):
            raise HarnessCoverageError("PASSIVE_SENSOR_INPUT_MUTATION:" + path)
        if status == "READ_ONLY_PRESENCE_SENSOR" and not _has_call(source, {"GetLastInputInfo"}):
            raise HarnessCoverageError("PRESENCE_SENSOR_PROBE_MISSING:" + path)
        if status == "ADOPTED_GATED":
            required_calls = entry.get("admission_calls")
            if required_calls is not None:
                if not isinstance(required_calls, list) or not required_calls or any(
                    not isinstance(name, str) or not _has_call(source, {name})
                    for name in required_calls
                ):
                    raise HarnessCoverageError("FALSE_ADOPTED_GATE_CLAIM:" + path)
            elif not _has_call(
                source, {"admitted_screen_lease", "CooperativeScreenQueue", "confirm"}
            ):
                raise HarnessCoverageError("FALSE_ADOPTED_GATE_CLAIM:" + path)
        if status == "UNADOPTED_LEGACY_NO_LIVE_AUTHORITY":
            entrypoint = entry.get("guard_entrypoint")
            if not _legacy_guard_call(source, path, entrypoint):
                raise HarnessCoverageError("UNADOPTED_RUNTIME_GUARD_MISSING:" + path)
        if status in NOT_PROVED:
            unproven.append(path)
    if len(manifest.get("proof_dimensions", [])) < 7 or "WINDOWS_HUMAN_INTERRUPT_OBSERVED" not in manifest["proof_dimensions"]:
        raise HarnessCoverageError("PROOF_DIMENSIONS_COLLAPSED")
    scan = manifest.get("source_scan") or {}
    needles = scan.get("needles")
    if not isinstance(needles, list) or not needles:
        raise HarnessCoverageError("ADAPTER_DISCOVERY_MISSING")
    unregistered = _unregistered_sources(manifest, root, registered=seen)
    if unregistered:
        raise HarnessCoverageError("UNREGISTERED_EFFECT_SOURCE:" + ",".join(unregistered))
    return {
        "state": "HUMAN_FIRST_HARNESS_PASS_STATIC_ONLY",
        "registered_adapters": len(sources),
        "unproven_runtime_or_mixed_adapters": unproven,
        "local_hook_or_physical_input_proof": "NOT_OBSERVED",
        "proof_ceiling": "GITHUB_SOURCE_AND_CI_ONLY_NOT_LOCAL_GAME_OR_EXTERNAL_AGENT_ENFORCEMENT",
    }



def _has_call(source: str, names: set[str]) -> bool:
    """Require an actual Python call expression, not comments or string markers."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return False
    return any(
        isinstance(node, ast.Call) and (
            isinstance(node.func, ast.Name) and node.func.id in names or
            isinstance(node.func, ast.Attribute) and node.func.attr in names
        )
        for node in ast.walk(tree)
    )


def _legacy_guard_call(source: str, path: str, entrypoint: object) -> bool:
    """Require a direct, literal, deny-only call in the listed public entrypoint."""
    if not isinstance(entrypoint, str) or not entrypoint:
        return False
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return False
    for fn in tree.body:
        if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)) or fn.name != entrypoint:
            continue
        for statement in fn.body:
            if not isinstance(statement, ast.Expr) or not isinstance(statement.value, ast.Call):
                continue
            call = statement.value
            if not isinstance(call.func, ast.Name) or call.func.id != "deny_unadopted_live_effect":
                continue
            if len(call.args) != 1 or not isinstance(call.args[0], ast.Constant):
                continue
            if call.args[0].value == path and not call.keywords:
                return True
    return False

def _unregistered_sources(manifest: dict, root: Path, *, registered: set[str]) -> list[str]:
    scan = manifest.get("source_scan") or {}
    needles = scan.get("needles") or []
    unregistered = []
    for base in scan.get("roots", []):
        folder = root / base
        if not folder.is_dir():
            raise HarnessCoverageError("SOURCE_SCAN_ROOT_MISSING:" + str(base))
        for path in sorted(folder.glob("**/*.py")):
            if not path.is_file() or path.is_symlink():
                continue
            rel = path.relative_to(root).as_posix()
            if rel == manifest["harness_validator"] or rel == manifest["host_settings_guard"]:
                continue
            code = path.read_text(encoding="utf-8-sig")
            if any(token in code for token in needles) and rel not in registered:
                unregistered.append(rel)
    return unregistered


def validate(root: Path = ROOT) -> dict:
    manifest = json.loads(_file(root, MANIFEST.as_posix()).read_text(encoding="utf-8"))
    return validate_manifest(manifest, root)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        receipt = validate()
    except (ValueError, KeyError, TypeError, OSError, UnicodeError, json.JSONDecodeError) as exc:
        print("HUMAN_FIRST_HARNESS_FAIL " + str(exc))
        return 1
    if args.json:
        print(json.dumps(receipt, sort_keys=True))
    else:
        print(f"HUMAN_FIRST_HARNESS_PASS adapters={receipt['registered_adapters']} "
              f"not_live_verified={len(receipt['unproven_runtime_or_mixed_adapters'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
