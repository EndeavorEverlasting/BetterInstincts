"""P01 static native-gameplay route admission; CI, not an EA runtime sandbox.

A source manifest is evidence that an agent classified the mechanism, not proof
that the installed Sims 4 runtime or an external Cursor agent obeyed it.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = Path("contracts/native-gameplay-authority.v1.json")
SCHEMA = "betterinstincts.native-gameplay-authority/v1"
DECISION_SCHEMA = "betterinstincts.native-gameplay-decision/v1"
TERMS = ("GAMEPLAY_IMPLEMENTATION_ROUTE", "NATIVE_MECHANIC_EVIDENCE", "HOST_LAB_BOUNDARY")
INVARIANTS = ("BI-ONT-042", "BI-ONT-043", "BI-ONT-044", "BI-ONT-045")
ROUTES = frozenset(("EA_TUNING", "EA_SCRIPT", "POLICY_ONLY", "HOST_LAB_ONLY", "NON_GAMEPLAY"))


class NativeGameplayError(ValueError):
    pass


def _safe_path(path: str) -> bool:
    if not isinstance(path, str) or not path or "\\\\" in path or "\\" in path:
        return False
    parsed = PurePosixPath(path)
    return not parsed.is_absolute() and ".." not in parsed.parts and path == parsed.as_posix()


def _checked_json(root: Path, rel: str) -> dict:
    if not _safe_path(rel):
        raise NativeGameplayError("UNSAFE_REVIEW_PATH:" + str(rel))
    path = root / rel
    if path.is_symlink() or not path.is_file():
        raise NativeGameplayError("MISSING_NATIVE_OWNER:" + rel)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise NativeGameplayError("INVALID_NATIVE_OWNER:" + rel) from exc
    if not isinstance(data, dict):
        raise NativeGameplayError("NATIVE_OWNER_NOT_OBJECT:" + rel)
    return data


def validate_contract(manifest: dict, root: Path = ROOT) -> dict:
    if not isinstance(manifest, dict) or manifest.get("schema") != SCHEMA:
        raise NativeGameplayError("NATIVE_CONTRACT_SCHEMA_INVALID")
    if manifest.get("native_first") is not True:
        raise NativeGameplayError("EA_NATIVE_FIRST_REGRESSION")
    routes = manifest.get("routes", {})
    if not isinstance(routes, dict) or set(routes) != ROUTES:
        raise NativeGameplayError("NATIVE_ROUTE_ENUM_CHANGED")
    for name, spec in routes.items():
        if not isinstance(spec, dict) or not spec.get("role"):
            raise NativeGameplayError("NATIVE_ROUTE_UNDEFINED:" + name)
        if spec.get("game_effect_candidate") is not (name in {"EA_TUNING", "EA_SCRIPT"}):
            raise NativeGameplayError("HOST_OR_POLICY_PROMOTED_TO_GAME_EFFECT:" + name)
    source = manifest.get("source_policy", {})
    if source.get("product_code_prefix") != "betterinstincts/" or source.get("product_code_suffix") != ".py":
        raise NativeGameplayError("PRODUCT_ROUTE_COVERAGE_REMOVED")
    core = source.get("core_policy_paths")
    if not isinstance(core, list) or len(core) != len(set(core)) or not core:
        raise NativeGameplayError("CORE_GAMEPLAY_OWNERS_UNDEFINED")
    if source.get("core_allowed_routes") != ["POLICY_ONLY", "EA_TUNING", "EA_SCRIPT"]:
        raise NativeGameplayError("CORE_GAMEPLAY_DESKTOP_PATH_UNBLOCKED")
    if not isinstance(source.get("core_desktop_input_sentinels"), list) or len(source["core_desktop_input_sentinels"]) < 10:
        raise NativeGameplayError("CORE_DESKTOP_INPUT_GUARD_MISSING")
    for path in core:
        if not _safe_path(path) or not path.startswith("betterinstincts/") or not path.endswith(".py"):
            raise NativeGameplayError("BAD_CORE_OWNER_PATH:" + str(path))
        f = root / path
        if f.is_symlink() or not f.is_file():
            raise NativeGameplayError("CORE_GAMEPLAY_OWNER_MISSING:" + path)
        violations = inspect_core_source(f.read_text(encoding="utf-8"), source["core_desktop_input_sentinels"])
        if violations:
            raise NativeGameplayError("DESKTOP_INPUT_IN_GAMEPLAY_CORE:" + path + ":" + ",".join(violations))
    review = manifest.get("change_review", {})
    if review.get("schema") != DECISION_SCHEMA or review.get("directory") != "contracts/native-gameplay-decisions/":
        raise NativeGameplayError("NATIVE_REVIEW_GUARD_REMOVED")
    ontology = _checked_json(root, manifest.get("ontology", ""))
    glossary = _checked_json(root, "contracts/glossary.v1.json")
    if ontology.get("revision", 0) < 8 or not set(TERMS).issubset(ontology.get("concepts", {})):
        raise NativeGameplayError("NATIVE_ONTOLOGY_MISSING")
    if not set(INVARIANTS).issubset({v.get("id") for v in ontology.get("invariants", [])}):
        raise NativeGameplayError("NATIVE_ONTOLOGY_INVARIANT_MISSING")
    if not set(TERMS).issubset(glossary.get("terms", {})):
        raise NativeGameplayError("NATIVE_GLOSSARY_MISSING")
    harness = manifest.get("harness", {})
    for key in ("validator", "tests", "workflow", "cursor_rule", "governance",
                "detailed_governance", "operator_report"):
        rel = harness.get(key)
        if not _safe_path(rel) or not (root / rel).is_file():
            raise NativeGameplayError("MISSING_NATIVE_HARNESS:" + key)
    ci = (root / harness["workflow"]).read_text(encoding="utf-8")
    if "python -m scripts.check_native_gameplay_authority" not in ci:
        raise NativeGameplayError("NATIVE_CI_GATE_NOT_WIRED")
    agents = (root / harness["governance"]).read_text(encoding="utf-8")
    detail = (root / harness["detailed_governance"]).read_text(encoding="utf-8")
    doctrine = (root / "docs/DOCTRINE.md").read_text(encoding="utf-8")
    if ("Native gameplay: EA tuning/scripts; GUI lab-only." not in agents or
            "contracts/native-gameplay-decisions/" not in detail or
            "GAMEPLAY_IMPLEMENTATION_ROUTE" not in doctrine):
        raise NativeGameplayError("NATIVE_GOVERNANCE_ROUTING_MISSING")
    return {"state": "PASS", "core_owners": len(core), "proof": manifest.get("proof_ceiling")}


def inspect_core_source(source: str, sentinels: list[str]) -> list[str]:
    """Conservative source sentinel, not a replacement for reviews of dynamic code."""
    return [token for token in sentinels if re.search(r"\b" + re.escape(token) + r"\b", source)]


def _reviewed_file(path: str, manifest: dict) -> bool:
    if not _safe_path(path):
        raise NativeGameplayError("UNSAFE_CHANGED_PATH:" + str(path))
    source = manifest["source_policy"]
    return ((path.startswith(source["product_code_prefix"]) and
             path.endswith(source["product_code_suffix"]))
            or any(path.startswith(prefix) for prefix in source["native_mod_prefixes"]))


def validate_route_decisions(manifest: dict, changed: list[str], decisions: list[dict]) -> dict:
    """Require a reviewed route for each changed game product file, not only cores."""
    required = {path for path in changed if _reviewed_file(path, manifest)}
    covered: dict[str, str] = {}
    core = set(manifest["source_policy"]["core_policy_paths"])
    for decision in decisions:
        if not isinstance(decision, dict) or decision.get("schema") != DECISION_SCHEMA:
            raise NativeGameplayError("NATIVE_DECISION_SCHEMA_INVALID")
        entries = decision.get("files")
        if not isinstance(entries, list) or not entries:
            raise NativeGameplayError("NATIVE_DECISION_FILES_MISSING")
        for entry in entries:
            if not isinstance(entry, dict):
                raise NativeGameplayError("NATIVE_DECISION_ENTRY_INVALID")
            path, route = entry.get("path"), entry.get("route")
            if not _safe_path(path) or path not in required:
                raise NativeGameplayError("NATIVE_DECISION_PATH_UNRELATED:" + str(path))
            if path in covered:
                raise NativeGameplayError("NATIVE_DECISION_DUPLICATE:" + path)
            if route not in ROUTES:
                raise NativeGameplayError("NATIVE_DECISION_UNKNOWN_ROUTE:" + path)
            if path in core and route not in manifest["source_policy"]["core_allowed_routes"]:
                raise NativeGameplayError("GAMEPLAY_CORE_CANNOT_USE_DESKTOP:" + path)
            if any(path.startswith(p) for p in manifest["source_policy"]["native_mod_prefixes"]) and route not in {"EA_SCRIPT","EA_TUNING"}:
                raise NativeGameplayError("NATIVE_MOD_PATH_REQUIRES_EA_ROUTE:" + path)
            if not isinstance(entry.get("reason"), str) or len(entry["reason"].strip()) < 20:
                raise NativeGameplayError("NATIVE_ROUTE_REASON_MISSING:" + path)
            claim = entry.get("game_effect_claim")
            if claim not in {"NONE", "OFFLINE_ONLY", "GAME_CERTIFIED"}:
                raise NativeGameplayError("NATIVE_EFFECT_CLAIM_INVALID:" + path)
            if claim == "GAME_CERTIFIED":
                # The local versioned live-cert mechanism owns this proof.
                # A developer-authored routing declaration is not that evidence.
                raise NativeGameplayError("NATIVE_ROUTE_CANNOT_SELF_CERTIFY:" + path)
            if route in {"POLICY_ONLY","HOST_LAB_ONLY","NON_GAMEPLAY"}:
                if claim != "NONE" or (route == "POLICY_ONLY" and
                                       not isinstance(entry.get("successor_issue"), int)):
                    raise NativeGameplayError("NON_NATIVE_GAME_EFFECT_CLAIM:" + path)
                if route == "HOST_LAB_ONLY" and entry.get("autonomy_runtime") is not False:
                    raise NativeGameplayError("HOST_LAB_AS_AUTONOMY_RUNTIME:" + path)
            else:
                if (claim != "OFFLINE_ONLY" or
                        not isinstance(entry.get("game_build"),str) or
                        entry["game_build"].lower() in {"unknown","latest","any",""} or
                        not isinstance(entry.get("ea_source_ref"),str) or
                        len(entry["ea_source_ref"].strip()) < 8):
                    raise NativeGameplayError("EA_NATIVE_SOURCE_EVIDENCE_MISSING:" + path)
            covered[path] = route
    missing = sorted(required-set(covered))
    if missing:
        raise NativeGameplayError("UNROUTED_PRODUCT_CHANGE:" + ",".join(missing))
    return {"state":"PASS","changed_product_files":len(required),"declared_routes":covered}


def git_changed(root: Path, base: str) -> list[str]:
    # GitHub PR provides trusted base SHA; never use shell or untrusted ref names.
    if not re.fullmatch(r"[0-9a-f]{40}", base):
        raise NativeGameplayError("INVALID_PR_BASE_SHA")
    result = subprocess.run(["git","diff","--name-only",f"{base}...HEAD"],
                            cwd=root,capture_output=True,text=True,check=False)
    if result.returncode:
        raise NativeGameplayError("NATIVE_GIT_DIFF_FAILED:" + result.stderr.strip())
    return [s for s in result.stdout.splitlines() if s]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root",type=Path,default=ROOT)
    parser.add_argument("--base-ref",default=None,help="PR base 40-character commit SHA")
    parser.add_argument("--json",action="store_true")
    args = parser.parse_args()
    try:
        manifest = _checked_json(args.root, CONTRACT.as_posix())
        report = validate_contract(manifest,args.root)
        if args.base_ref:
            changed=git_changed(args.root,args.base_ref)
            prefix=manifest["change_review"]["directory"]
            added=[p for p in changed if p.startswith(prefix) and p.endswith(".json")]
            decisions=[_checked_json(args.root,p) for p in added]
            report["pr_route_review"]=validate_route_decisions(manifest,changed,decisions)
    except (NativeGameplayError,OSError,UnicodeError) as exc:
        print("NATIVE_GAMEPLAY_AUTHORITY_FAIL "+str(exc))
        return 1
    if args.json:
        print(json.dumps(report,sort_keys=True))
    else:
        print("NATIVE_GAMEPLAY_AUTHORITY_PASS "+json.dumps(report,sort_keys=True))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
