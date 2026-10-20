# Multiple Sims 4 game versions — compatibility authority

**Goal:** publish mod variants that support several concrete game versions without breaking configurations already proven to work on older patches. New versions DO NOT retire old profiles by default.

## Why these mechanics
- [Lot51/core-library README](https://github.com/lot51/core-library/blob/main/README.md): semantic mod versions, dependency minimum version checks, avoid bundling Core; [Core 1.37 release](https://lot51.cc/mods/core-library/releases/1.37) documents a repaired regression in compatibility with <=1.116. **OBSERVED DOCUMENTATION**; separate mod dependency from exact game-patch proof.
- [The Sims 4 Modders Reference](https://thesims4moddersreference.org/tutorials/creating-xml-compare/): extract and retain per-patch XML for diffing. **DOCUMENTED WORKFLOW**; do not commit EA extracted game content to this repo.
- [Oops19/TS4-PatchXML](https://github.com/Oops19/TS4-PatchXML): XPath patching and game-version-scoped caches, with risks when an upstream XML element changes. **OBSERVED README/RELEASE DESIGN**, not adopted as a binary or mandatory dependency.
- [Sims4CommunityLibrary](https://github.com/DeviantGameMods/Sims4CommunityLibrary): minimum supported Sims patch and separate mod package release. **DOCUMENTED**; not proof of arbitrary newer patch compatibility.

**Adopt:** patch identifiers, explicit release compatibility statements, clear dependency floors, tuning-diff workflow. **Adapt:** one immutable certified profile per tested combination, and a separate revision when updating rather than silent overwrites. **Reject:** `latest` fallback, wildcard version claims, automatic mutation of old tuned configs, blanket reinstall of dependent library, redistributing EA XML. **EVIDENCE GAP:** actual tested game patches, hunger tuning IDs, artifact hashes and gameplay comparisons.

## Versioned contracts (already implemented)
- `compatibility/catalog.v1.json` is the ONLY profile index. It deliberately begins **empty**: nobody has certified any real game build.
- `compatibility/profiles/<profile_id>.json` owns one exact full Sims build string, OS platform (`windows`/`mac`), feature module, status (`experimental` / `certified`), tested tuning source SHA256, compiled package SHA256, and evidence pointer.
- Full game versions include all four fields (e.g. `1.121.342.1030` for Windows; Mac builds are a different four-field string). **Do not substitute a truncated three-field patch or claim PC/Mac equivalence**.
- `betterinstincts.compatibility.select_profile` matches exact `game_version` + `platform` + `module`; unknown patch returns `UNKNOWN_VERSION`, experimental returns `UNVERIFIED`, multiple certified alternatives return `AMBIGUOUS` until a profile ID is selected. No nearest-newer/older, silent broad ranges, or fallback.
- `scripts/check_backward_compat.py` compares old certified catalog rows, profile bytes and evidence bytes against Git base ref; removal/rewrite is rejected by CI. To fix already certified behavior, create a **new profile ID** rather than overwriting the previously working profile.
- `scripts/validate_doctrine.py` and CI require the compatibility policies and game-lab progress mechanisms. This is **repository-time compatibility selection**; it is not in-game runtime detection or packaging.

## Required local-game profile promotion (BI-002)
1. Inspect exact Sims 4 main-menu version, OS, installed packs, and S4S build. Do not guess. Start from the existing cert-run CLI documented in [BI-002](../plans/active/BI-002.md).
2. Capture genuine vanilla tuning resource IDs and fingerprints without checking in extracted copyrighted assets. Compare new patch tuning to the *prior local extraction* (if present) on the game host; record the affected resource IDs and diff summary. Keep raw extractions out of Git.
3. For a new patch create **a new** experimental profile ID; preserve earlier profiles. Require explicit path `compatibility/profiles/<id>.json`, the schema fields listed above, and a known user-selected game-mod location for **manual** installation.
4. Finish hunger A/B, rollback and mod-conflict game trials; call live-cert evaluator. Attach captured receipts (redact save names, user paths and personal data). A numerical pass is **review required**, not a certificate.
5. Maintainer reviews artifact hash, actual package, resource IDs, gameplay capture, test version/OS and conflict matrix. Only then append a `certified` profile and `certifications/<id>.json` accepted review record. Never substitute synthetic CI fixtures for real game evidence.
6. New Sims patch triggers new candidate profile and selective XML diff, **not edits to old certified files**. Keep prior release binaries/checksums accessible via archived release assets (future release process).

## Development artifacts versus player releases
Use a repo-local `dist/` for generated packages and local run reports, ignored by git. No writes to the user's Docs/Electronic Arts, saves, or other mods except an explicitly reviewed, user-initiated dedicated Mods subfolder. A protected/locked profile must not be silently replaced. Publish a matrix of explicit validated game version/platform/module and optional dependencies; all untested combinations are UNKNOWN, not supported. An experimental profile is not selected for normal release.

## Important limitation
This repository can enforce exact-profile selection and preservation at Git/CI time but **cannot yet automatically detect Sims' in-game version** or install the right `.package`. That adapter must be implemented with real game API/runtime evidence. Do not claim a file exists in the game simply because the offline selector can find its profile.
