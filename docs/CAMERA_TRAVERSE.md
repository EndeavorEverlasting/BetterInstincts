# Camera-safe host traversal (P95 + P97 + trifecta)

**Terminal user value:** agents can gather lot/map data for the next move without parking the mouse on the screen edge and leaving the Sims camera scrolling while they develop.

**Machine authority:** [`contracts/camera-traverse.v1.json`](../contracts/camera-traverse.v1.json)
**Library:** `betterinstincts/camera_traverse.py`
**CLI:** `python -m scripts.camera_traverse`
**Vocabulary:** [GLOSSARY.md](GLOSSARY.md)
**Program home:** [HOST_AUTONOMY.md](HOST_AUTONOMY.md)


## Semantic definition: screen edge versus camera-trigger region (2026-11-09)

**Screen edge** in operator shorthand is **not** the monitor bezel, the first/last literal pixel, or a prohibition against near-edge UI buttons. It means the portion of the **Sims 4 game client** where the pointer can cause camera translation by lingering. The single conservative host policy calls this `SCREEN_EDGE_CAMERA_TRIGGER_ZONE`: the current default 48px inset from each client boundary. Actual activation depends on exact game build, overlays, HUD coverage, input mode, and window geometry; 48px is a **protective margin**, not an experimentally established engine hitbox. All coordinates are client-relative; never substitute absolute desktop/monitor edges.

Interpret a pointer observation by **phase + target + ownership + camera outcome**, not by pixel location alone:

- **Idle/park** at a potential camera-trigger edge: **bad** for agent-owned pointer. Classify `CAMERA_EDGE_DWELL_FORBIDDEN` and require `SAFE_CURSOR_REST` before thinking, coding, waiting, vision sampling, or another world-target click.
- **A verified, brief HUD/control click near the edge:** **legitimate**. `TARGETED_CLICK` + fresh `UI_CHROME` attestation yields only `EDGE_UI_CLICK_HOST_ADMISSION` as a geometry candidate. Existing exact-mode/scene/save/player/idle controls must still admit the one click. Release, park the host-controlled cursor inside the client, and independently verify the HUD outcome. Do not mislabel this as `EDGE_MOUSE_PARK`.
- **Cursor transit through an edge:** not automatically a misclick; no prolonged dwell. Finish bounded movement and park safely.
- **Deliberate camera navigation:** must be host-owned, bounded, explicitly goal-scoped, and end at `SAFE_REST` plus fresh capture/camera revision before any world click. Never park near the edge while reasoning or keep stale target coordinates.
- **Unverified control or world-object target near the edge:** abstain and reobserve/reframe; do **not** use the transient HUD exception to bypass world framing.
- **Player-owned pointer:** yield and do not commandeer or reposition it merely because it is at an edge. A host must reacquire permitted control after the user becomes idle.

The machine-readable policy is in `contracts/camera-traverse.v1.json#edge_interaction`; the sole pure evaluator is `betterinstincts.camera_traverse.assess_edge_interaction` (also exposed via `evaluate_cursor_risk`). For agent CLI runs:

```sh
python -m scripts.camera_traverse evaluate --x 800 --y 20 --phase TARGETED_CLICK --target-kind UI_CHROME --target-verified
python -m scripts.camera_traverse evaluate --x 800 --y 20 --phase REST
python -m scripts.camera_traverse rest --session-id SID --process-id PID --execute
```

The first command **does not click**; it returns an explicit host-admission gate and mandatory post-click safe rest. The second shows the forbidden unattended dwell. The third requires a real admitted active session; do not run it against a player-owned cursor. `scripts.win32_input.send_click`, `send_right_click`, `send_wheel` and `right_drag` already default to `safe_rest_after=True`; caller overrides must be contained by an admitted higher-level finally/rest contract, never used as a permanent cursor park.

**Live certification boundary:** P82 offline tests prove classification and guard behavior only. P08 must observe the exact Sims client, changing camera revision and screen imagery over sustained cursor dwell, then demonstrate that valid edge HUD clicks still work and admitted safe rest stops camera movement. Tests must also include player interruption and window geometry. A CI PASS is not P08 proof.

## Problem

Sims pans the camera when the cursor sits in the edge band (default **48px**). Agents often push the mouse to the edge to scan — or leave it on the cheat-console strip / bottom HUD after a click — then switch to coding with the cursor still there. The camera keeps drifting and the next observation is garbage.

**Mandatory park:** `scripts.win32_input.send_click` / `send_wheel` / `right_drag` default `safe_rest_after=True` and call `park_safe_cursor_rest()`. Skill-force and other host mouse work must end at `SAFE_CURSOR_REST`. Agents using Computer Use must not leave the cursor on the viewport edge; prefer hotkeys, then park with `python -m scripts.camera_traverse rest --execute ...` or interior center (~client 50%/50%).

## Selected architecture: `CAMERA_SAFE_TRAVERSE`

| Option | Verdict |
| --- | --- |
| Keep ad-hoc edge scrolling in agent chat | **Reject** — recreates EDGE_MOUSE_PARK / CONTINUOUS_EDGE_HOLD |
| Clone Automation OmniParser/PaddleOCR/VLM into this repo | **Reject now** — licensing, weights, and observe≠act seam belong upstream; BI already has PrintWindow |
| Host-owned capture-first + bounded right-drag + mandatory SAFE_CURSOR_REST | **Select** |

### Call stack

```text
observe cursor / scan need
  -> camera_traverse.evaluate_cursor_risk
  -> if EDGE_BAND: CAMERA_SAFE_REST (park interior; withhold needs clicks)
  -> else if scan needed: plan CAPTURE_OBSERVE? -> RIGHT_DRAG_PAN* -> SAFE_REST
  -> house_state non-mutating CAMERA_PAN_ZOOM / CAPTURE_ONLY / OBSERVE_ONLY
  -> optional scripts.camera_traverse --execute via screen_admit (one plan)
```

Non-mutating camera/UI browse remains lease-free under `house_state` (`CAMERA_PAN_ZOOM`, `CAPTURE_ONLY`, `OBSERVE_ONLY`).

## CLI

```sh
python -m scripts.camera_traverse classify --x 5 --y 540
python -m scripts.camera_traverse plan --capture-only
python -m scripts.camera_traverse plan --dir E --dir N
python -m scripts.camera_traverse rest --session-id SID --process-id PID --execute
```

`--execute` requires an ACTIVE host_listener session + PID through `screen_admit`. Capture steps defer to `scripts.game_capture`; this CLI does not invent scene claims.

## P97 prior-art disposition

| Source | Decision |
| --- | --- |
| Automation `docs/VISUAL_INTELLIGENCE_STACK.md` observe≠act / consumer-owned actuation | **ADAPT** seam; do not vendor donor engines |
| TokenCorridor visual-intelligence incubation (deterministic before VLM) | **ADAPT** escalation order |
| Existing BI `scripts/game_capture.py` PrintWindow | **ADOPT** as primary see-without-edge-pan sensor |
| Direct OmniParser / PaddleOCR / Qwen clone into BetterInstincts | **REJECT** for this sprint |

Full matrix: [PRIOR_ART.md](PRIOR_ART.md#2026-11-08--p97-camera-safe-traverse--visual-observation).

## Proof ceiling

`OFFLINE_CAMERA_SAFE_TRAVERSE_NOT_LIVE_CAMERA_PROOF`. Live SendInput park/pan remains `LOCAL_OBSERVED` click dispatch until a disposable lab P08 proves the camera stops after SAFE_REST. Does **not** close BI-002.

## Camera-first world-object targeting — P00 / P01 / P95 / Trifecta

**Rule:** make the visual situation easy *before* attempting the world action. Fixed HUD/UI chrome is not a camera target and keeps its existing exact-build calibration. For an in-world object, `betterinstincts.camera_traverse.assess_world_target` is the single pure framing owner, composed by `host_stack.evaluate_turn(world_target=...)` and the opt-in `host_listener` observation route. The authoritative thresholds and bounded retry budget live in `contracts/camera-traverse.v1.json`; do not clone them into an agent-only prompt or a second mouse service.

**Call stack (offline policy, not a click):** world-target intent → current `capture_ref` and host-sourced target box/visibility/occlusion/camera revision → camera-first framing assessment → if not ready, bounded existing `plan_traverse` from *host-observed* directions → admitted local host executes any explicitly authorized camera movement → mandatory safe-interior rest → **fresh capture and target re-detection** → assess again → only when comfortably framed, `WORLD_TARGET_AWAIT_HOST_ADMISSION` → separate scene/save/player/idle and exact native window admission → one effect → post-effect observation. No source module here issues SendInput.

Input: `world_target={"target_id":"A-OK Bloomer", "observation":{"source":"HOST_CAPTURE","target_id":"A-OK Bloomer","capture_ref":"capture:target-frame","camera_revision":"camera:42","target_visible":true,"occluded":false,"bbox_client":[840,420,1020,600],"framing_attempts":0}, "reframe_directions":[]}`, with matching `capture_ref`, explicit `client_width` and `client_height` on `evaluate_turn`. The bounding box is `[left,top,right,bottom]` in client pixels, not guessed absolute screen coordinates. A clear interior object of sufficient size produces a **candidate** center point, never a control permit. Missing/stale evidence requests a new observation; small/occluded/edge-clipped objects request a camera reframe. With no measured direction, capture/inspect instead of blind pan. Three failed reframe attempts require human review rather than thrashing.

**Trifecta:** P95 owns the call-stack and failure model; P82 owns fixed-point/negative tests in `tests/test_camera_traverse.py`; P07 owns bounded branch/CI integration; P08 requires actual Sims 4 patch calibration, camera-motion validation, player interruption, multi-angle world-object trials and independently observed click outcomes before any game-certification claim. Existing 15-second human-idle and save-protection gates are unchanged. A pan *invalidates* pre-pan target coordinates and scene observations; do not reuse them after camera movement. This is applicable to object selection for needs, build placement, inventory and other in-world tasks, without constraining future agent strategies for how a host supplies the directions.


## Active-Sim camera center and follow — keyboard + code without portrait clicking

**Separate commands, separate effects:** In Live mode Enter centers the active Sim **once**, Shift + Enter centers the current lot **once**, and Space selects the next household Sim (only by explicit player decision). Continuous follow is **not** the effect of Enter. EA documents Enter and portrait right-click as different operations. The host must never invent a native follow keyboard key, repeatedly press Enter to mimic tracking, or click the Sim portrait as a covert fallback.

**P95 call stack:** explicit CENTER_ACTIVE_SIM, CENTER_CURRENT_LOT or FOLLOW_ACTIVE_SIM intent → current host capture/selected Sim/Live scene/two independent cues → betterinstincts.sim_camera.plan_sim_camera → host_stack / opt-in listener (read-only) → existing CooperativeScreenQueue 15-second-idle checkpoint and exclusive desktop lease → one keyboard chord via scripts.win32_input.send_key_chord (center) **or** one approved in-game camera API call through scripts.sim_camera.follow_active_sim_in_game (follow) → independent post-action observation. The app-defined Ctrl+Alt+Shift+F is an **app-scoped intent mapping**, not a native Sims key or an installed OS/global listener. It must be connected to an opt-in installed extension to become a usable physical shortcut.

**Game code port:** follow_active_sim_in_game(expected_sim_id, admit=..., observe=...) is invoked only within the actual Sims Python runtime with a compatible, pre-existing Sims4CommunityLib installation. It resolves CommonSimUtils.get_active_sim_info, verifies identity + loaded instance and independent admission, then delegates CommonCameraUtils.start_focus_on_sim(info, follow=True). No third-party code or game runtime is bundled. API source: https://github.com/DeviantGameMods/Sims4CommunityLibrary/blob/main/Scripts/sims4communitylib/utils/misc/common_camera_utils.py (CC BY 4.0; BetterInstincts calls its API, not copied code).

**One-shot Windows key port:** scripts.sim_camera.center_on_admitted_host(command, session_id=..., process_id=..., observe=...) needs a real, current Live-mode host sensor, exact process/session, idle player and fresh revalidation. It dispatches Enter or Shift+Enter through the shared Win32 input owner without moving the cursor. The CLI command python -m scripts.sim_camera --command CENTER_ACTIVE_SIM is inspection-only: route printing never starts input.

**Non-disruption invariants:** no automatic relock or continuous poll, no portrait-mouse fallback, no effects while the player owns camera, types into text/cheat/chat input, opens dialogs, changes active Sim, or interrupts a queued action. Camera plans always have execute_allowed=false; input dispatch ACK is *not* follow proof. P08 must witness camera tracking over time while Sim walks and verify player takeover/switching Sim remains respected.


## 2026-11-09 — regression: camera drifts during pixel-target reconnaissance

**Observed failure class:** an agent starts collecting target pixel coordinates while its cursor remains in the Sims viewport edge band. Sims pans the camera during the agent's reasoning; the old target coordinates become meaningless, and repeated clicks send the agent further away.

**Canonical, enforceable owner:** camera_traverse.assess_drift_recovery uses contracts/camera-traverse.v1.json drift_recovery. host_stack.evaluate_turn(camera_recovery=...) prioritizes the recovery gate over generic traversal and world-target actions; host_listener accepts a bounded optional camera_recovery object. The recovery contract is not a replacement for the old cursor-rest, native focus and world-framing owners.

**Deterministic recovery order:** (1) Respect player camera, active input/overlays, exact-game scene, human presence and save approval. (2) If cursor is in the edge band, emit CAMERA_SAFE_REST only; admitted script camera_traverse rest parks it in the interior. (3) **Take a new capture**; never measure world pixel targets from the camera view that drifted before resting. (4) If camera remains displaced, center on active Sim with Enter, or center lot with Shift+Enter for a lot/world-object intent; optionally use the already-registered game API follow route only when requested. (5) Reacquire a new capture with a new camera revision after any camera motion. (6) For a world object, only traverse using directions supplied by the current host observation. (7) Re-detect target bounding box and verify its capture_ref, camera_revision, visibility, occlusion and interior bounds before proposing one click. (8) The separate screen-admitted native world-click port rechecks these facts at its final action boundary; the app never auto-reclicks after uncertainty.

**Camera reanchor budget:** at most two attempts before CAMERA_RECOVERY_MANUAL_REVIEW. After a first lot reanchor, a world target needs host-observed direction; without it the gate requests observation rather than endlessly hitting Shift+Enter. An optional Sims portrait right-click is only a **P08-calibrated future adapter** with verified selected Sim and player-safe authorization; the present policy forbids uncalibrated portrait clicking. Native Enter/Shift+Enter are one-shot focus, not continuous follow, and current S4CL focus-follow requires the actual game extension and a permitted target. No global hooks or automatic ongoing camera lock.

**Recovery input shape:** camera_recovery = {"target_kind":"WORLD_OBJECT","target_id":"A-OK Bloomer","observation":{"source":"HOST_CAPTURE","capture_ref":"capture:host-turn","camera_revision":"camera:9","camera_displaced":true,"camera_reanchor_attempts":0,"cursor_client":[1918,540],"mode":"LIVE","scene_id":"live_mode","game_version":"<exact catalog version>","capture_quality":"CONTENT_PRESENT","viewport_state":"NORMAL","player_camera_owned":false,"text_entry_active":false,"modal_open":false,"player_queue_owned":false,"save_authorized":true,"independent_cues":[{"source":"visual","token":"live_hud"},{"source":"operator","token":"live_confirmed"}]}}. All fields are host observations, never model-invented. The sample is not authorization or an instruction to mutate a real save.

**P82 proof vs P08:** tests/test_camera_traverse.py and tests/test_screen_atlas.py cover edge rest, one-shot focus, counted retries, stale camera revisions, direct world-click refusal, player takeover and preserved HUD coordinates. This remains offline host policy and injected-port regression protection until exact-build live Sims trials verify real drift stops, camera follow, repeated target acquisition and zero disturbance to the player.


## 2026-11-09 — Pause Live simulation before target reacquisition (P95 / P124 / Trifecta)

The camera-drift recovery sequence now **freezes game simulation time before targeting Live-mode Sims or world objects**, but only when the host has reliable clock evidence. EA confirms P, 0 and backtick are pause toggles, not idempotent commands (https://www.ea.com/games/the-sims/tips-and-tricks). Consequently, **never blind-tap P**: if Live is already paused, emit GAME_PAUSED_FOR_TARGETING and send no input; if Live is confirmed playing, emit GAME_PAUSE_REQUIRED with a *single* P key; if the state is unknown/mismatched, emit GAME_PAUSE_REOBSERVE without input. There is no automatic resume in this camera-targeting workflow.

**P95 call stack:** trusted Live host capture with independent mode cues → cursor SAFE_REST if edge-panning → corroborated game-clock sensor and HUD pause indicator → request one admitted P only if PLAYING → capture **new** frame confirming game clock stillness and pause icon → reanchor Sim/lot if necessary → measured camera traverse → new camera revision + capture after camera motion → re-detect world target → screen_atlas.enqueue_world_game_click requires unchanged camera and paused clock revisions at final human-idle/action checkpoint → at most one click. Existing host_stack.evaluate_turn(camera_recovery=...) and host_listener continue to route this owner; this is **not** a second game controller.

**Evidence shape:** provide a nested game_clock in the trusted host observation, e.g. {"source":"HOST_GAME_CLOCK","capture_ref":"capture:recover-1","camera_revision":"camera:9","game_version":"<exact game build>","clock_revision":"clock:12","speed_state":"PAUSED","pause_indicator_active":true,"clock_still_during_sample":true,"pause_origin":"PLAYER"}. Clock and HUD pause indicator must agree; this is a host sensor, not model inference. The clock revision must change if game time advances or a speed transition occurs. The separate scripts.camera_traverse.pause_game_on_admitted_host is an opt-in **injected** local adapter requiring a fresh sensor and the existing exact PID, active session, human-idle lease. It dispatches at most one P and rechecks state; no auto-repeat, auto-resume, game launch or global keyboard hook. User-owned pause remains untouched.

**Important limitations:** pausing gameplay does **not** freeze the movable camera, user cursor, player input, or every UI refresh. Earlier camera-revision/safe-rest/foreground and player ownership gates still apply. The Skills panel may remain stale while paused; the existing skill-force PLAY_BRIEF_OBSERVE_REPAUSE owner (5–10s 1x, inspect, re-pause) is preserved and must not be replaced by a paused-only screenshot. The host needs physical P08 validation of Sims patch, clock/pause sensor, known paused vs running cases, safe agent-initiated pause, and post-camera target click before live certification.

## ROOM_MAP_TRAVERSE — leave Sim center to map a room (2026-11-10)

**Operator corrections:** default active-Sim center stays. For room graph census: **Build F3 → T top-down → `BUILD_TOP_DOWN_MAP` room-fit zoom (default across agents/host; preserve the operator-centered frame — do not re-zoom/pan once attested) → Select-click one item → read bottom-right params → document name + `client_xy` → Escape → next**. Capture via PrintWindow. Offline only (no Gallery/EA Connect). On grab/hold: **Escape immediately**; never place/sell/inventory.

**Algorithm (offline plan → admitted live):**
1. `REQUIRE_NAMED_MAP_GOAL` (`goal_id` + `target_kind`).
2. Escape overlays; **hotkey** `F3` Build (observe-only — no catalog place).
3. Hotkey `T` Build top-down; hotkey `X` / safe-interior wheel zoom out until the room fits.
4. Capture/observe furniture one-by-one; upsert floor-map **graph** (landmarks → edges → targets). No LMB on objects.
5. On erroneous grab: Escape (repeat if still held) → resume hotkey-only census.
6. Optional: local **Save to My Library** folder control only — never Gallery share.
7. Hotkey `F1` restore Live + `SAFE_CURSOR_REST`.

Live `OBJECT_PICK_IDENTIFY` remains a separate path for Order/pie after the graph exists — not the census authority.

**Memorialization (continuous):** once mapped, an object is `MEMORIALIZED` with `expected_interactions` and frozen durable fields. Casual re-observations do not rewrite it. At interact time, if an expected interaction is absent (e.g. Order missing → Online Charity instead), mark `STALE_NEEDS_REMAP` and remap **only that node**. Owners: `contracts/lot-floor-map.v1.json#memorialization`, `memorialize_object` / `assess_interaction_against_memorial`.

**Needs opportunity (preferred):** when `host_stack` investigates a `world_target` for needs, `opportunistic_needs_map` records/assesses that object in the profile floor map. Prefer this natural path over Build-mode sampling sprints; Build `T` stays the fallback for unknowns/stale-only nodes.

**Builder placement auto-map (installed host):** while BetterInstincts is installed, cooperative `host_listener` Build/Buy ticks record builder **LMB place** events into the floor graph (`record_builder_placement`, bbox **center**, optional `SEATED_AT`/`ON_TOP_OF` links). This is **not** OS cron/Task Scheduler; `bootstrap uninstall` removes the managed launcher and stops it. Agent Select-inspect still requires **bbox-center click + Escape**; grab without Escape is a regression.

**Owners:** `contracts/camera-traverse.v1.json#room_map_traverse`, `betterinstincts/room_map_traverse.py`, graph writeback `betterinstincts/lot_floor_map.py`. CLI: `python -m scripts.lot_floor_map room-traverse-plan` / `record-room-landmarks`. Proof ceiling offline plan + local graph store — not live click cert.

## Active-Sim-only camera invariant (2026-11-09)

After repeated observed agent drift toward a top-down street, the **default camera frame is the active Sim**, not an arbitrary place. During admitted host control, `host_stack.evaluate_turn(..., sim_camera_observation=...)` now requests `CAMERA_ACTIVE_SIM_CENTER_REQUIRED` unless observation proves the active Sim is already centered or followed. Native `Enter` centers the active Sim; `Shift+Enter` centers a lot, not a Sim. Neither keystroke alone establishes continuous game API follow.

The only exception is a target/goal map lease: current `HOST_CAPTURE`, independent scene cues, exact active Sim ID and camera revision, Live mode, known `HOST_TASK` goal and named target, lease age at most 30 seconds, no more than eight bounded pan steps. Map traversal first requires an active-Sim anchor. It terminates in SAFE_REST, admitted `Enter` restoration (or observed existing follow) and a **new observation**; an input acknowledgment is not a visual proof. Human activity, focus loss, invalid mode, changed Sim or modal suspends automation and leaves restore pending. No polling or global key capture.

`scripts.camera_traverse plan` still offers a read-only plan. Generic `--execute` now refuses map pan/zoom without an injected trusted sensor and goal lease. The host-side `_execute_plan(..., map_goal=..., observe=..., now_ms=...)` performs mandatory cleanup inside the same admission lease; `rest --execute` remains an independently admitted cursor park. Core authority: `contracts/camera-traverse.v1.json`; implementation: `betterinstincts/active_sim_camera_lock.py`; checks: `tests/test_active_sim_camera_lock.py`. P00/P01 retain governance and harness, P95 owns call-stack design, P141 identified this gap, P124 integrates existing owners. Trifecta proof remains separate for code, CI, merge and live Sims.

## 2026-11-09 correction — portrait right-click follows; Enter merely centers

The canonical Sims 4 control distinctions are essential to the semantic layer:

- **Right-click the selected active Sim's portrait** (household portrait cluster, left side of the HUD to the right of the calendar/phone) to **follow** that Sim. This is the preferred default while BetterInstincts has admitted game-screen control. EA reference: https://www.ea.com/games/the-sims/tips-and-tricks
- **Enter** centers **once** on the active Sim. It is a temporary recovery/fallback, **not a follow lock**.
- **Shift+Enter** centers once on the **current lot**, not the active Sim. It must not substitute for the default Sim view.

Machine ownership: `contracts/portrait-follow.v1.json` and `betterinstincts/portrait_follow.py`. A right-click needs a fresh screenshot-derived **selected active Sim ID**, exact current portrait rectangle, portrait/layout/Sim revisions, independent visual+operator cues, unoccluded Live HUD, same capture reference, exact game PID/session and idle host lease. No static inferred portrait coordinates, free world right-click, or retries of an ambiguous click. `scripts/sim_camera.py::follow_active_portrait_on_admitted_host` uses `scripts/win32_input.py::send_right_click` and observes whether Sims actually entered follow; the Python callback and mouse dispatch are not themselves proof of follow.

`active_sim_camera_lock` now distinguishes **follow observed** from **centered once**. When the selected portrait is attested, request `CAMERA_PORTRAIT_FOLLOW_REQUIRED`; a centered static view instead requires portrait attestation and is not considered locked. Where the exact portrait is temporarily unavailable, `Enter` may center once for safe recovery without declaring the preferred follow behavior achieved. After a named-map goal lease, the injected traverse executor prefers a verified portrait right-click and only falls back to Enter as one-shot centering; afterward the host must recapture before target clicks or queue continuation. Player camera ownership and unresolved event overlays always win.

**Live integration gate:** The running Windows host/participating Playwright agents must actually call the canonical portrait and overlay ports with fresh observation. A PR merge alone does not install or certify UI behavior. Record the game build, exact active Sim, portrait hitbox, selection/layout revisions, first right-click, following observation, interrupted event test and subsequent scene-change observations. No EA Connect; stay offline.

## Escape is not a traverse close (2026-11-09)

Escape while Live opens the **Travel map / pause MENU**. It is never the household-traverse or cheat-console close and is never spammed. Close the console with **Ctrl+Shift+C** (`CTRL_SHIFT_C_TOGGLE`) and advance portraits with **Space**. One deliberate Escape-cancel of an *observed* dialog (for example CAS when the operator asked to cancel) is the only allowed use. Machine owner: `contracts/diy-skill-force.v1.json` `ui_forbids`, evaluated by `betterinstincts.diy_skill_force.evaluate_ui_action`.

## 2026-11-09 — agent zoom ladder (RIGHT_CLICK_VIEW default)

Operator-attested ladder for **every** agent (P01 harness, not chat preference):

| Mode | Zoom-in fraction of max | When |
| --- | --- | --- |
| **RIGHT_CLICK_VIEW** (Screenshot 2 / default) | **0.85** (15% pullback from max close / Screenshot 3) | Default agent work; portrait right-click follow first |
| **ENVIRONMENT_NAV** | **0.50** | Named environment planning / understanding / move planning only |
| **TRAVEL_AFAR** (Screenshot 1 / 4) | **0.0** full zoom-out | Verified long-distance travel goal only — never a parked default |
| **MAX_CLOSE** (Screenshot 3) | **1.0** | Reference extreme; not the agent default |

Machine owner: `contracts/camera-traverse.v1.json#agent_zoom_policy`, `assess_agent_zoom_mode` / `plan_agent_default_view`. `active_sim_camera_lock` fails closed when the observed view is street top-down without a travel goal. Wheel notch distances require local P08 calibration; offline plans set `requires_live_calibration=true` and never grant input.

**Zoomed-in overlay clear:** at RIGHT_CLICK_VIEW or MAX_CLOSE, after BetterInstincts has `metadata_tracked` + `accounted_by=BETTER_INSTINCTS`, propose dismiss for expanded opportunity panel, expanded bottom-right panels, cheat console, expanded phone (extensible). Unresolved decision overlays never clear as clutter. Owner: `scene_ui_semantics.assess_overlay_clear_after_metadata`.

## 2026-11-10 — ZOOM_MODE ≠ ZOOM_CONTROL; OBJECT_PICK_IDENTIFY

**Operator corrections:** Zooming in is **not** a right-click. Zooming in is Live hotkey **Z** (zoom out **X**); **scroll wheel** also zooms. When picking a world object, **traverse → zoom in → screenshot → identify → click**. Do not identify from street top-down.

| Semantic | Meaning | Actuator |
| --- | --- | --- |
| **ZOOM_MODE** `RIGHT_CLICK_VIEW` | Target distance 0.85 of max close (+ follow posture) | Not an input |
| **ZOOM_CONTROL** `CAMERA_ZOOM_IN` | Zoom closer | **Z** (KEY) or scroll wheel |
| **ZOOM_CONTROL** `CAMERA_ZOOM_OUT` | Zoom farther | **X** (KEY) or scroll wheel |
| Portrait RMB | Follow active Sim | Not zoom |
| Enter / Shift+Enter | Center Sim / lot once | Not zoom |

Catalog: `contracts/ui-chrome.v1.json` LIVE `CAMERA_ZOOM_IN` / `CAMERA_ZOOM_OUT`; `contracts/camera-traverse.v1.json#zoom_controls` + `#object_pick_identify`. Planner: `plan_object_pick_identify` / `python -m scripts.camera_traverse object-pick-plan --target-id ID`. Lean skill-force typing still forbids mid-beat zoom (separate beat).

## 2026-11-10 — lot focus (LOT_OFF_FOCUS)

When the camera shows **scenery off the active household lot** (street, canal, neighborhood top-down), agents must **not** street-roam or pan without bound. Classify with `betterinstincts/lot_focus.assess_lot_focus`; machine policy in `contracts/camera-traverse.v1.json#lot_focus`.

| State | Meaning |
| --- | --- |
| **ON_LOT** | Camera/scenery on the active household lot |
| **OFF_LOT_STREET** | Street/neighborhood view; often `TRAVEL_AFAR` without a verified long-distance travel goal |
| **OFF_LOT_WATER** | Canal/waterfront off-lot scenery |
| **UNKNOWN** | Insufficient host/operator lot-focus cues — reobserve |

**Cues:** missing Live HUD, `zoom_mode_observed` = `TRAVEL_AFAR` without travel goal, `camera_lot_kind`, `camera_on_active_household_lot`, `lot_focus_cues` from host/operator.

**Restore:** `CENTER_ACTIVE_SIM` via **Enter** only in the default plan. **Shift+Enter** (lot center) is forbidden as the default Sim restore. `host_stack.evaluate_turn` emits `lot_focus` and gates `LOT_OFF_FOCUS_RESTORE_REQUIRED` ahead of discretionary camera work.

Proof ceiling: `OFFLINE_LOT_FOCUS_POLICY_NOT_LIVE_CAMERA_CERTIFIED`. Consultation: `contracts/consultations/BI-LOT-OFF-FOCUS-20261110.v1.json`.
