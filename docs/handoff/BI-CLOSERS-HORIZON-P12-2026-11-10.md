# P12 — Closers handoff (Horizon-aware) — 2026-11-10

**Repo:** EndeavorEverlasting/BetterInstincts  
**Path:** `C:/Users/CheeksMcClappeth/dev/BetterInstincts`  
**Branch:** `main` @ `a94f114` (dirty; matches `origin/main` tip; uncommitted floor-map/camera/placement work)  
**Horizon gate:** **BI-002** (`ACTIVE_GAME_UNPROVEN`). `check_horizon` topology PASS; `game_certification=NOT_PROVED`.  
**Durable execution owner:** `plans/active/BI-HORIZON-EXECUTION-WIDE-20261110.v1.json` (repo-wide stages H0→H1→MAP→BI-002→Horizon).  
**Closers pack (P02/P12 only):** `plans/active/BI-CLOSERS-HORIZON-20261110.v1.json`

## Owned / forbidden
- **Own:** land dirty harness; BI-002 live hunger cert; needs→map during hunger; FG S2 panel observe; builder placement live sensor.
- **Forbidden:** promote BI-003+; claim BI-005 from diy_skill_force; OS cron; Gallery/online; grab without Escape; rezoom away from operator Build T frame; close BI-002 from CI/offline.

## Changed this chat (uncommitted / local)
Floor map + memorial + needs opportunistic map; `BUILD_TOP_DOWN_MAP`; Select-inspect Escape+bbox-center; builder placement auto-map via `host_listener` (not OS cron); graph link relations; bad census script disabled after grab regression.

## Proof reached
- contract + static unit tests (floor map / zoom / room traverse / lot_focus)
- live H0: **NEW save PROVED** — `My Saved Game 6` / `Slot_00000007.save` (2026-11-10 04:29); UI list attested; no delete/overwrite
- live: Build T earlier; Escape after grab; PrintWindow captures; Options/Save As/ADD NEW SAVE coords calibrated
- **not** BI-002 hunger trials; **not** Skills LOCAL_OBSERVED PASS; **not** builder live sensor cert; **not** Horizon stage close

## Next command
```powershell
cd $env:USERPROFILE\dev\BetterInstincts
python -m scripts.live_cert status --run-id bi002-game1-20261107   # baseline 2/5 INCOMPLETE
python -m scripts.check_horizon
# Live truth + ordered gates: plans/active/BI-HORIZON-EXECUTION-WIDE-20261110.v1.json#live_truth_20261110 / next_gates_ordered
# Gate 1: recover a LIVING hunger subject (Charlee/Olga are ghosts); gate 2: recenter+zoom so fridge pie opens; never set_stat drain without queued food
```

## Copy-paste next agent
Open `plans/active/BI-HORIZON-EXECUTION-WIDE-20261110.v1.json` first for stage order, proof ceilings, and forbidden save ops; then `plans/active/BI-CLOSERS-HORIZON-20261110.v1.json` for launch_order C1–C6. H0 new-save is PROVED (`My Saved Game 6`). Horizon current_gate is BI-002 only. Execute C1 land then C2 hunger. Do not treat Fifth Gear S2 or floor-map offline as hunger cert or BI-005. lot_focus OFF_LOT recovers via Enter, not street roam. Never delete saves.
