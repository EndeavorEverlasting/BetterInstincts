"""Versioned, explicitly certified Sims 4 patch compatibility; no game API access."""
import hashlib
import json
import re
from pathlib import Path

SCHEMA = "betterinstincts.compatibility/v1"
VERSION_RE = re.compile(r"^[0-9]+(?:\.[0-9]+){3}$")
ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{1,79}$")
SHA_RE = re.compile(r"^[a-f0-9]{64}$")
COMMIT_RE = re.compile(r"^[a-f0-9]{40}$")
PLATFORMS = {"windows", "mac"}
MODULES = {"hunger", "bladder", "energy", "hygiene", "fun", "social",
           "needs", "income", "skills", "career", "household"}
STATES = {"experimental", "certified"}

class CompatibilityError(ValueError):
    pass

def load_catalog(root):
    """Parse and validate only repo-owned profile paths. No wildcard patch ranges."""
    root = Path(root).resolve()
    doc = json.loads((root / "compatibility/catalog.v1.json").read_text(encoding="utf-8"))
    if not isinstance(doc, dict) or doc.get("schema") != SCHEMA or not isinstance(doc.get("profiles"), list):
        raise CompatibilityError("INVALID_CATALOG_SCHEMA")
    ids = set()
    for row in doc["profiles"]:
        if not isinstance(row, dict):
            raise CompatibilityError("INVALID_PROFILE_ROW")
        profile_id, version = row.get("id"), row.get("game_version")
        if not isinstance(profile_id, str) or not ID_RE.fullmatch(profile_id):
            raise CompatibilityError("INVALID_PROFILE_ID")
        if profile_id in ids:
            raise CompatibilityError("DUPLICATE_PROFILE_ID")
        ids.add(profile_id)
        if not isinstance(version, str) or not VERSION_RE.fullmatch(version):
            raise CompatibilityError("INVALID_GAME_VERSION")
        if row.get("platform") not in PLATFORMS or row.get("module") not in MODULES:
            raise CompatibilityError("INVALID_PROFILE_TARGET")
        if row.get("status") not in STATES:
            raise CompatibilityError("INVALID_PROFILE_STATUS")
        expected = "compatibility/profiles/" + profile_id + ".json"
        if row.get("path") != expected:
            raise CompatibilityError("PROFILE_PATH_MUST_BE_CANONICAL")
        path = root / expected
        if not path.is_file() or not path.resolve().is_relative_to((root / "compatibility/profiles").resolve()):
            raise CompatibilityError("MISSING_OR_UNSAFE_PROFILE")
        profile = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(profile, dict) or any(profile.get(k) != row.get(k) for k in ("id", "game_version", "platform", "module", "status")):
            raise CompatibilityError("PROFILE_CATALOG_MISMATCH")
        for name in ("tuning_source_sha256", "package_sha256"):
            v = profile.get(name)
            if v is not None and (not isinstance(v, str) or not SHA_RE.fullmatch(v)):
                raise CompatibilityError("INVALID_SHA256")
        if row["status"] == "certified":
            if not all(profile.get(k) for k in ("tuning_source_sha256", "package_sha256", "evidence_ref", "source_commit_sha")):
                raise CompatibilityError("CERTIFICATION_REQUIRES_PROOF_POINTERS")
            if not isinstance(profile["source_commit_sha"], str) or not COMMIT_RE.fullmatch(profile["source_commit_sha"]):
                raise CompatibilityError("INVALID_CERTIFIED_SOURCE_COMMIT")
            if not str(profile["evidence_ref"]).startswith("certifications/"):
                raise CompatibilityError("INVALID_CERTIFICATION_POINTER")
            evidence = root / profile["evidence_ref"]
            if not evidence.is_file() or not evidence.resolve().is_relative_to((root / "certifications").resolve()):
                raise CompatibilityError("MISSING_CERTIFICATION")
            cert = json.loads(evidence.read_text(encoding="utf-8"))
            if (cert.get("profile_id") != profile_id or cert.get("status") != "MAINTAINER_ACCEPTED"
                or cert.get("game_version") != version or cert.get("package_sha256") != profile["package_sha256"]
                or cert.get("source_commit_sha") != profile["source_commit_sha"]):
                raise CompatibilityError("CERTIFICATION_NOT_ACCEPTED")
    return doc

def select_profile(catalog, game_version, platform, module, profile_id=None):
    """Only exact patch + platform + module is eligible; ambiguous matches fail closed."""
    if not isinstance(game_version, str) or not VERSION_RE.fullmatch(game_version):
        return {"status": "UNKNOWN_VERSION", "profile": None}
    matches = [r for r in catalog["profiles"] if r["game_version"] == game_version and
               r["platform"] == platform and r["module"] == module and
               (profile_id is None or r["id"] == profile_id)]
    certified = [r for r in matches if r["status"] == "certified"]
    if not certified:
        return {"status": "UNVERIFIED" if matches else "UNKNOWN_VERSION", "profile": None}
    if len(certified) != 1:
        return {"status": "AMBIGUOUS", "profile": None}
    return {"status": "SELECTED", "profile": certified[0]}

def sha256(data):
    return hashlib.sha256(data).hexdigest()
