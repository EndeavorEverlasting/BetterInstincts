# Native gameplay authority — P00 doctrine / P01 enforced harness

**Product:** make Sims behave intelligently *inside the game*. The product is
the EA-native autonomy mechanic: patch-specific XML tuning, or where XML
cannot express the behavior, a proven embedded Sims 4 Python script hook.
A desktop agent pressing queue/HUD buttons repeatedly is **not** an
acceptable substitute for native autonomy, even when screen detection
and player-ownership gates are good.

## Precedence and seams

1. **EA_TUNING:** inspect the installed version's EA tuning with Sims 4
   Studio in read-only mode; identify interaction scoring/tests/TGI and
   determine whether a reversible XML override expresses the change.
2. **EA_SCRIPT:** only when source-proven native hooks are needed; inspect
   exact patch and embedded Python API signatures and package compatibility
   before implementing. Do not assume host Python 3.11 imports run in Sims.
3. **POLICY_ONLY:** offline deterministic reasoning, tests, training or
   prototypes. These never cancel, enqueue, patch tuning or confer runtime
   game authority. Carry a concrete successor issue for actual native work.
4. **HOST_LAB_ONLY:** user-authorized diagnostics, camera/object inspection,
   disposable household test setup, input/capture and manual game verification
   are allowed under the existing focus/idle, scene, save and one-effect
   admission contracts. No background clicker/Win32 input bridge may *be*
   the behavior engine or claim queue autonomy improvements from clicks.
5. **NON_GAMEPLAY:** development/build utilities with no game-behavior
   implementation.

Native does not outrank **human**. The player's ordered queue, own intent,
unknown origin, emergency needs, leisure/social character, autonomy settings,
save safety and patch compatibility remain mandatory even for a native hook.
Never change Windows Bluetooth, drivers, Print Screen, Escape/U mappings,
keyboard hooks or peripheral policy. A native-game hook should be bounded,
reversible, opt-in where needed and event-driven rather than per-frame global
polling. One source owner: `betterinstincts/autonomy_moderation.py` for current
per-household native policy; issue #171 owns exact-patch EA integration.
No parallel daemon, HWND clicker or duplicate scoring engine.

## Mandatory product-code PR review — machine enforced

`contracts/native-gameplay-authority.v1.json` is the machine contract;
`scripts.check_native_gameplay_authority` and the CI workflow enforce it.

Any PR modifying a file under `betterinstincts/*.py`, `tuning/` or
`native_mod/` must include a new or updated
`contracts/native-gameplay-decisions/<feature>.v1.json` **in the PR diff**,
covering every changed product file **exactly once**. A review row must contain
`path`, `route`, `reason` (at least 20 characters),
`game_effect_claim` (`NONE` or `OFFLINE_ONLY`). Policy-only work also
records `successor_issue`; host-lab-only work sets
`autonomy_runtime: false`; EA work declares `game_build` (exact) and
`ea_source_ref` (verified provenance). Existing core-gameplay policy owners
cannot use `HOST_LAB_ONLY` or `NON_GAMEPLAY`, and cannot import desktop
control primitives. A future new product file is not automatically exempt.

A compliant example for a pure offline policy update:

```json
{
  "schema": "betterinstincts.native-gameplay-decision/v1",
  "files": [
    {
      "path": "betterinstincts/autonomy_moderation.py",
      "route": "POLICY_ONLY",
      "reason": "Pure per-Sim recommendation without any actual EA queue mutation",
      "game_effect_claim": "NONE",
      "successor_issue": 171
    }
  ]
}
```

This JSON route declaration is not a game installation permit.
`GAME_CERTIFIED` is rejected by the routing declaration even if it names
a version; independently verified local `scripts.live_cert` plus actual
baseline/modified observations and rollback own gameplay evidence. Keep
the real package's source/tuning IDs, patch, authored hashes and results
in versioned local certification records, never guess EA APIs or distribute
proprietary EA game assets. Protected saves remain untouched.

Commands from the canonical repository checkout:

```sh
python -m scripts.check_native_gameplay_authority
python -m unittest tests.test_native_gameplay_authority -v
python -m scripts.check_native_gameplay_authority --base-ref <EXACT_PR_BASE_COMMIT_SHA>
python -m scripts.check_human_sovereignty --json
python -m scripts.check_peripheral_boundary
python -m scripts.check_horizon
```

CI's native architecture gate is **static source/decision admission only**.
It cannot guarantee independent Cursor agent rule activation, a locked down
Windows desktop, player input interception during an in-game script, or
any Sims runtime effect. A green PR and merged main remain distinct from
local repository checkout, installed package and observed playable behavior.

## Project status

P00/P01 repository-level native-first contract and prospective CI guard
are separate from the P08 native integration. Current policy PR #170 and
Horizon P00 closeout PR #172 were merged, but a packaged/game-verified EA
queue implementation has **not** been observed. The first runtime action is
an authorized read-only local exact-patch EA tuning/script inspection for
issue #171; the independent BI-002 hunger live-cert stage remains active.
