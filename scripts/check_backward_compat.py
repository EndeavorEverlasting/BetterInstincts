#!/usr/bin/env python3
"""CI gate: a previously certified profile or its acceptance must not mutate."""
import argparse
import json
import subprocess
import sys
from pathlib import Path

from betterinstincts.compatibility import load_catalog, CompatibilityError

ROOT = Path(__file__).resolve().parents[1]

def git_read(ref, path):
    result = subprocess.run(["git", "show", ref + ":" + path], cwd=ROOT, capture_output=True)
    return result.stdout if result.returncode == 0 else None

def check(base_ref, root=ROOT, old_reader=git_read):
    current = load_catalog(root)
    old_raw = old_reader(base_ref, "compatibility/catalog.v1.json")
    if old_raw is None:
        # Initial bootstrap is legal ONLY when base has no compatibility tree.
        prior = subprocess.run(["git", "ls-tree", "-r", "--name-only", base_ref, "--", "compatibility/"],
                               cwd=ROOT, capture_output=True)
        if prior.returncode != 0 or prior.stdout.strip():
            raise CompatibilityError("BASE_CATALOG_UNAVAILABLE_WITH_PRIOR_PROFILES")
        old_raw = json.dumps({"schema": current["schema"], "profiles": []}).encode()
    try:
        old = json.loads(old_raw)
    except (TypeError, ValueError) as exc:
        raise CompatibilityError("BAD_BASE_CATALOG") from exc
    if old.get("schema") != current["schema"]:
        raise CompatibilityError("CATALOG_SCHEMA_REGRESSION")
    active = {r["id"]: r for r in current["profiles"]}
    for previous in old.get("profiles", []):
        if previous.get("status") != "certified":
            continue
        key = previous["id"]
        if key not in active or active[key] != previous:
            raise CompatibilityError("CERTIFIED_PROFILE_REWRITTEN:" + key)
        for path in (previous["path"],):
            saved = old_reader(base_ref, path)
            local = (root / path).read_bytes()
            if saved is None or saved != local:
                raise CompatibilityError("CERTIFIED_PROFILE_CONTENT_CHANGED:" + key)
        profile = json.loads((root / previous["path"]).read_text(encoding="utf-8"))
        evidence_path = profile["evidence_ref"]
        before = old_reader(base_ref, evidence_path)
        if before is None or before != (root / evidence_path).read_bytes():
            raise CompatibilityError("CERTIFICATION_CONTENT_CHANGED:" + key)
    return {"status": "PASS", "certified_preserved": sum(r["status"] == "certified" for r in old.get("profiles", []))}

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--base-ref", required=True)
    args = p.parse_args()
    try:
        print(json.dumps(check(args.base_ref)))
    except (CompatibilityError, OSError, KeyError, ValueError) as exc:
        print("BACKWARD_COMPAT_BLOCKED:" + str(exc), file=sys.stderr)
        return 2
    return 0

if __name__ == "__main__":
    sys.exit(main())
