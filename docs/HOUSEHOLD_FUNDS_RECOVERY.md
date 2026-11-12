# Household funds: exact target, observed fallback, platform scope

The **active** Sims 4 household is selected by the running game, not by a
portrait, save name, installation path, or Steam/EA/Epic launcher. Never edit a
save file or give agents Windows peripheral control. This is an opt-in
**Windows host-lab** operation, **not** an installed game-native money mod.

## Runtime identity and distribution compatibility

The existing Windows host adapter attaches to the operator-supplied
`--process-id` of the foreground running `TS4_x64.exe` or `TS4.exe`,
and an ACTIVE `--session-id`. It verifies that executable **basename**,
not a drive prefix, Steam path, EA installation directory, or launcher
window. Explicit custom installation locations therefore do not require a
special path rule. Profile-based **launching** is separate and uses a
user-chosen absolute executable; no recursive discovery, registry scan,
environment mutation, or installer is authorized by this feature.

| Game/channel | Policy and host claim | Remaining proof |
| --- | --- | --- |
| EA app / Steam / Epic on Windows | Same read-only plan and Windows PID adapter, independent of install directory | Real local executable, scene, patch and before/after HUD trial per channel |
| Different Windows disk or Steam library | No hardcoded path in funds injection; attach to verified live game PID | Local session/PID and console-focus proof |
| Free base game, EA Play, legacy trial/other edition | Planner supported; Windows adapter only if verified Sims executable identity and scene | Edition-specific game command behavior **unverified** |
| macOS / consoles | Plan and explanation only; Windows SendInput adapter is **not** portable | A separate platform-native, permissioned adapter and game certification |

EA publishes `Ctrl+Shift+C`, `testingcheats true`, `money N` (exact
balance), `motherlode` (+50,000), and `kaching` (+1,000):
https://www.ea.com/games/the-sims/the-sims-4/faq/cheats .
The separate EA app is required even for Steam/Epic PC versions:
https://www.ea.com/ea-app .
A storefront name is **not** a patch/build certification. Check the exact
four-field game patch in the menu; preserve older compatibility profiles.

## Safe route and exact local command sequence

First have a disposable household loaded and observe the current funds and
mode (live/build/buy). Run a read-only plan from the checked-out repo:

```powershell
python -m scripts.funds_inject plan --amount 1000000 --funds 38 --game-mode live
python -m scripts.funds_inject inject --amount 1000000 --funds 38 --game-mode live
```

Obtain the exact Sims PID, activate an explicit `host_listener` session by
the existing operator-controlled flow, and ensure the operator is idle.
For a calibrated Ctrl+Shift+C path, this one effect is admitted through the
existing screen lease; no F1, portrait selection, fixed-pixel clicks or Esc:

```powershell
python -m scripts.funds_inject inject --amount 1000000 --funds 38 --game-mode live --execute --process-id ACTUAL_PID --session-id ACTIVE_SESSION --receipt dist/game-host/funds-exact-001.json
```

**Alternative console arming, not another toggle:** if automatic Ctrl+Shift+C
is unreliable, the operator can open the cheat console, visibly confirm the
command input is ready, then leave the game idle for the screen lease. This
skips the chord rather than toggling an already-open console closed:

```powershell
python -m scripts.funds_inject inject --amount 1000000 --funds 38 --game-mode live --console-open-method operator-ready --console-ready --execute --process-id ACTUAL_PID --session-id ACTIVE_SESSION
```

The result is only `FUNDS_INJECT_DISPATCHED_NOT_VERIFIED` with a
`dispatch_ref` and `console_input_focus_proof` label. **It is not a
confirmed game effect.** Read the post-command household funds HUD and
record an independent observation reference:

```powershell
python -m scripts.funds_inject verify --amount 1000000 --funds-before 38 --funds-after 1000000 --evidence-ref hud:post-exact-001
```

## Recovery when exact money was actually observed to do nothing

Do not chain `motherlode` after `money` or retry because a keyboard
injection returned without an exception. Wait until the original command
has settled, confirm the current game and HUD, and explicitly confirm that
the balance is **unchanged**. Take the actual `dispatch_ref` from the
earlier result and a distinct post-dispatch HUD reference.

```powershell
python -m scripts.funds_inject recover --amount 1000000 --funds-before 38 --funds-after 38 --game-mode live --prior-dispatch-ref dispatch:PASTE_ACTUAL_REF --evidence-ref hud:post-exact-001 --confirmed-noop
```

Review the plan. Only then execute **one** fallback using the same active
PID/session and chosen console method:

```powershell
python -m scripts.funds_inject recover --amount 1000000 --funds-before 38 --funds-after 38 --game-mode live --prior-dispatch-ref dispatch:PASTE_ACTUAL_REF --evidence-ref hud:post-exact-001 --confirmed-noop --execute --process-id ACTUAL_PID --session-id ACTIVE_SESSION
```

After the fallback, observe a **new** HUD capture and separately classify
whether the target was reached, the balance increased partially, or no
change was established:

```powershell
python -m scripts.funds_inject verify --route recovery --amount 1000000 --funds-before 38 --funds-after-exact 38 --funds-after 50038 --prior-dispatch-ref dispatch:PASTE_ACTUAL_REF --no-op-evidence-ref hud:post-exact-001 --evidence-ref hud:post-additive-001 --confirmed-noop
```

`FUNDS_PROGRESS_ATTESTED_BY_EXTERNAL_OBSERVATION` is not success.
The next action requires a new current balance, renewed player/scene checks,
and a separately authorized plan. Never reuse a HUD reference from the
original no-op attempt as the fallback result evidence.

The deterministic order is: `motherlode` if the remaining gap is at least
§50,000; otherwise `kaching` if at least §1,000; otherwise
`NO_EXACT_ADDITIVE_FALLBACK`. There is **one** additive command per
invocation, never more than the target gap, and no automatic continuation.
A partly increased balance must be observed before any new plan. Non-1,000
remainders cannot be completed exactly using those additive cheats alone.
Diagnose exact-money input/patch support instead of overshooting. This is a
test-setup convenience, **not** evidence of earned income.

## P08 local acceptance matrix

On disposable saves, run separate trials for each available installation
channel and exact game patch. Record game storefront, full build, executable
basename/PID, chosen mode, user-active/idle transition, console-open method,
pre/post capture IDs, actual dispatch reference and balance. Cover:

- Exact command succeeds; does not reduce already-richer household.
- Exact command no-ops; explicitly confirmed fallback increments by exactly
  +50,000 or +1,000 without overshoot, with fresh separate HUD evidence.
- Console chord fails/already open; operator-ready path does not re-toggle.
- Foreground/agent session/user activity changes; abort without wrong-window input.
- Unsupported executable, unobserved balance, tiny remainder, delayed effects,
  repeated evidence and tampered command stack; all fail closed.

No provider-side unit test, launch dispatch, screenshot claim or CI job can
replace in-game P08 observation. The original BI-002 hunger certification
remains separate and open. Source contract:
`contracts/host-funds.v1.json`; implementation:
`betterinstincts/funds_inject.py` and `scripts/funds_inject.py`.
