# Oldest-first lab save trial preference (MoonWake P00 → P01)

**Status:** repository-only priority advisory. No installed Sims 4 runtime, live menu action, save-file read, or automatic resume was performed.

## Corrected operator intent

The earlier statement “latest = most disposable” was backwards. More recent saves usually contain more recent decisions and may be needed to undo mistakes discovered days later. **Prefer the oldest save as a disposable-trial candidate; preserve newer saves more strongly.**

Age is a **priority signal**, not proof of authorization. The oldest unknown or player-created save is **not** a lab disposable save. To prevent irreversible regressions, the existing `betterinstincts.save_policy.decide` is still the only candidate admission guard. Only `LAB_DISPOSABLE` lab-created, current-run/current-capture/current-build operator-attested entries can be ranked. Never rank `USER_PROTECTED`, `UNKNOWN_PROTECTED` or `LAB_CONTINUATION` as disposable.

**No automatic save selection, Resume, Load User Save, overwrite, deletion, migration, file scan or disk save editing.** Game-host's separately gated explicit chosen-save flow still applies. This ranking cannot issue a screen/game effect permit. If there is no eligible disposable save, the answer is no eligible candidate, not “use the newest save” or “restart The Sims.”

## Canonical owners and the P00/P01 sequence

- **P00 — Governance Doctrine Installer:** `AGENTS.md`, `docs/AGENT_OPERATING_RULES.md`, `contracts/save-policy.v1.json`. Correct the inverted operator instruction while preserving the existing save and player sovereignty protections.
- **P01 — Harness Infrastructure Builder:** `scripts/save_candidate_priority.py`, `scripts/check_save_candidate_priority.py`, `tests/test_save_candidate_priority.py` and the normal CI workflow. No product-code or EA-native changes are needed to make a safe ranking advisory.
- Existing authority: `betterinstincts/save_policy.py` and `scripts/save_guard.py`; do not introduce a competing save classifier. Operator review and screen admission remain separate from an advisory.
- Chronology and scope receipt: `contracts/consultations/BI-SAVE-OLDEST-FIRST-P00-P01-20261114.v1.json`.

## Source and algorithm

1. Take **only an explicitly supplied private lab register** in `betterinstincts.save-register/v1` format. Do not enumerate or read game saves, `Documents/Electronic Arts` or profile directories.
2. For every record classified `LAB_DISPOSABLE`, call the canonical `decide()` with `SELECT_FOR_PLAY`, exact current run, captured slot identity and exact game patch. Admission is `OPERATOR_ATTESTED_SELECTION_ONLY`, not independent proof of save origin.
3. Require each eligible lab record to have `lab_created_at_utc` (canonical `YYYY-MM-DDTHH:MM:SSZ` UTC) and `lab_creation_time_confirmed: true`. This is explicitly **operator-attested lab chronology**, not the filesystem modification time or a filename guess.
4. Sort admitted candidates by increasing lab creation time. The oldest gets priority 1. Preserve recent lab and personal saves by avoiding them in trials when an older eligible lab save exists.
5. If **any** labelled disposable lab candidate has missing/invalid age or a mismatched capture/run/build/origin guard, abstain rather than silently prefer a newer save. If timestamps tie, abstain as chronology ambiguous. Exclude protected/continuation records regardless of age.
6. Return a read-only ranked list with `selected_save_id: null`, `control_permit: null`, `automatic_input: false` and no save-file access. The operator must still choose; the host rechecks separately before any action.

This is a deterministic review order, **not** a destructive “older saves are safe to delete” policy. External backups, EA cloud sync and version history are not inferred from lab timestamps. Do not synthesize a date to make a blocked trial proceed.

## Operator/local agent entrypoint

```sh
python -m scripts.check_save_candidate_priority
python -m unittest tests.test_save_candidate_priority -v
python -m scripts.save_candidate_priority \
  --registry dist/game-host/operator-lab-register.json \
  --run-id <EXISTING_LAB_RUN_ID> \
  --game-version <OBSERVED_FULL_PATCH>
```

The registry remains private and is not created or populated automatically. If it lacks creation receipts, inspect only the already authorized lab evidence with the operator; do not restart a prior completed vanilla/modded trial to fabricate a timestamp.

## Verification and handoff

CI's independent `P00/P01 oldest-first save trial advisory` step runs both the completeness validator and the negative/positive fixtures. Source/CI validation is **not** live game or local MoonWake prompt-walker proof. A later local agent should use the ranked advisory only when actual lab receipts exist and maintain the existing no-auto-select game host boundary. BI-002 live A/B evidence remains independently owned.
