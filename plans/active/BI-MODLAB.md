# BI-MODLAB — custom Mod Lab bootstrap / API reconnaissance

**Identity:** tooling lane only. Horizon **BI-004** remains *recurring income* and must not be reused for Mod Lab. **State:** inventory + P04 handoff + bounded DBPF TGI index on main. **Purpose:** safe modlet, script, package-index and future skill-inspection without replacing the autonomy roadmap.

## Parent objective and continuity

BetterInstincts improves Sims 4 autonomy across all six adult needs, then sustainable income, observed skill growth and careers without overriding direct player commands. BI-002 hunger gameplay certification remains ACTIVE and is not bypassed by this additive mod-manager lane.

## Owner lanes and explicit scope

- HOST CURRENT_CHAT_RUNTIME: GitHub connector source work and isolated Python fixture execution. GitHub is provider, not runtime.
- HOST CI_OR_REMOTE_RUNNER: full repository tests and backward-compatibility/doctrine/horizon checks.
- HOST LOCAL_AGENT_RUNTIME: read-only real Mods root, Sims 4 Studio/tuning analysis, disposable game trial. Never infer the local game patch from an offline scanner.
- HOST OPERATOR_OR_PHYSICAL_RUNTIME: player control, actual save/session decisions.
- Owned: betterinstincts/modlab.py, betterinstincts/dbpf.py, scripts/modlab.py, tests/test_modlab.py, tests/test_dbpf.py, docs/MOD_LAB.md, this sprint and the final P04 handoff; additive README and ledger references.
- Forbidden: modifying saves, scanning arbitrary user directories, EA assets, mod installation/toggling, binaries, script execution, background scans, changes to older certified profiles and third-party contents.
- Repo preflight: refresh `main` before new work; do not invent a second Mod Lab ID.

## Trifecta execution contract

- P08 live runtime proof: game host and exact patch may be BLOCKED_LOCAL_GAME_ACCESS. Fixture CLI is not Sims gameplay.
- P82 prototype/measure/refine: hypotheses — (1) central-directory inspection yields useful module leads without executing mods; (2) a bounded DBPF index reader yields TGI keys from synthetic packages without reading payloads. Falsifiers: absolute path leak, writes, archive/package payload execution/extraction, symlink traversal, budget bypass, treating overlaps or TGI lists as conflict/gameplay proof. Synthetic fixture checks measure these.
- P07 integrate: source + tests + documentation; git branch/PR, regression CI, merge only proven safe slice.
- P04 finalize after Trifecta: plans/active/BI-MODLAB.HANDOFF.md owns actual branch/PR/test status, runtime partition and one exact first local command.

## Acceptance

    python -m unittest discover -s tests -v
    python -m scripts.modlab --mods-root "<explicit Mods directory>"
    python -m scripts.check_horizon
    python scripts/validate_doctrine.py
    python scripts/check_tracked_assets.py

Require explicit BLOCKED/nonzero for invalid roots and exceeded scan budgets. Never claim DBPF resource conflicts, skill callbacks, working Sims API hooks, playable mod or game compatibility from file metadata alone.
