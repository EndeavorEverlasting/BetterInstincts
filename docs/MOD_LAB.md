# BetterInstincts Mod Lab — read-only bootstrap

**Status:** Offline inventory and API reconnaissance. NOT a playable mod, installer, or game-certification tool.

## Start on Windows or Linux Mint

From this repository's root, with developer Python 3.11+:

    python -m scripts.modlab --mods-root "PATH/TO/YOUR/EXPLICIT/Mods"
    python -m unittest discover -s tests -v
    python -m scripts.tuning_audit --xml "PATH/TO/YOUR/EXPLICIT_SIMS4STUDIO_EXPORT.xml"

The directory name must be Mods and must be selected explicitly. No auto-discovery, network, caches, background scans, automatic startup, file modification, installation, archive extraction or script imports. Output goes to stdout only. JSON includes relative mod paths and archive metadata, not the selected absolute path or third-party script bytes. Treat filenames as private when sharing a report.

## What is implemented

| Input | Read-only result | Proof ceiling |
| --- | --- | --- |
| .package | Size, DBPF magic, and bounded Type/Group/Instance index keys | Index keys only — NOT tuning semantics, TGI collision proof, or gameplay |
| .ts4script | Zip central-directory Python module names (.py/.pyc), depth warnings | Name overlaps are candidates, NOT proven runtime conflicts |
| Invalid inputs | Corrupt archives, unsafe module names, symlinks, bounded workloads | No fix, extraction, execution, or gameplay observation |
| One explicitly exported XML file | Existing scripts.tuning_audit identity, fingerprint and bounded metadata | No original EA XML stored or redistributed |

Budgets: at most 10,000 recognized mod files, 2,000 ZIP entries and 256 modules per archive, 64 MiB per package or script archive, 10,000 index entries per package, 256 reported TGI keys per package, and 16 components per archive member path. Unknown/malformed input yields warnings or BLOCKED; truncated resource listings set `truncated: true` and never claim a complete inventory. Linked files and directories are skipped; ZIP member payloads and package resource bodies are never decompressed or executed.

Diagnostic report hierarchy (stdout JSON only): `status` → `inspected_files` → per-item `issues` / `modules` / `package_index` → `module_overlap_candidates` → `findings` → `proof_ceiling`. Absolute Mods roots never appear in the payload.

## APIs and mechanisms to investigate

1. **Packages / modlets.** DBPF is a container, not a skill API. A bounded read-only Type/Group/Instance index parser now lives in `betterinstincts/dbpf.py` and is exercised by synthetic fixtures. Compare the same local file's resources to Sims 4 Studio before trusting keys for a hunger package. Do not infer TGI keys from filenames or package magic alone; index keys are not certified tuning IDs.
2. **Script modules.** A .ts4script archive carries Python modules, but module-name presence does not prove import success or runtime compatibility. Treat the Sims embedded Python version separately from developer Python; evaluate script imports/hooks in a disposable game session only.
3. **Motives, skills and autonomy.** Trace actual skill/statistic gains, tuning XML, interactions, autonomy scores and resource IDs in game-version-specific Sims 4 Studio exports. Exact Sims APIs, hook points, skill IDs and in-game behavior remain UNVERIFIED. First live gate is BI-002 hunger; subsequent skills are downstream of six needs and observed recurring income.
4. **Extensions.** XML Injector and the Lot51/S4CL libraries are potential integration points, not required dependencies. Verify each implementation, version compatibility and license before adoption. Prefer targeted tuning for hunger before any Python hook. No executable patches, memory injection, auto-updates or third-party code copying.
5. **Future manager actions.** Consider resource-overlap analysis, profiles and reversible activation of BetterInstincts-owned packages, but no writes to other creators' mods unless independently authorized and rollback-safe. The existing doctrine requires all installation changes to stay inside Mods/BetterInstincts under an explicit root.

## Prior-art reference leads, not copied dependencies

- https://github.com/TrollingDEAD/The-Sims-4-Mod-Manager-TS4MM — documents DBPF and script-module overlap strategies; broad Windows-first manager; no code reused.
- https://github.com/stark-studio-labs/sims4-mod-manager — documents a read-only package parser and separate packaging boundaries; inspect code/license independently.
- https://github.com/MAL22/Sims4-TuningInspector — tooling for exploring tuning objects / Python interfaces; game-host verification and license review required.
- See PRIOR_ART.md for previous Lot51, S4CL, XML Injector and Sims 4 Studio evidence.

## Next proof gate

Offline: inspect one operator-selected real Mods root (read-only), sanitize report, compare module-name and TGI findings to an independent tool / Sims 4 Studio on the same file, and keep BI-002 hunger resource research private (no EA XML in Git).
Game: BI-002 remains ACTIVE. Local game-capable agent must inspect exact Sims patch and packs, build one reversible hunger mod, record at least five vanilla and five modified trials plus rollback and player-command safety review. Mod Lab neither closes nor replaces that experiment.