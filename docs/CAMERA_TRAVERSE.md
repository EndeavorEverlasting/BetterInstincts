# Camera-safe host traversal (P95 + P97 + trifecta)

**Terminal user value:** agents can gather lot/map data for the next move without parking the mouse on the screen edge and leaving the Sims camera scrolling while they develop.

**Machine authority:** [`contracts/camera-traverse.v1.json`](../contracts/camera-traverse.v1.json)
**Library:** `betterinstincts/camera_traverse.py`
**CLI:** `python -m scripts.camera_traverse`
**Vocabulary:** [GLOSSARY.md](GLOSSARY.md)
**Program home:** [HOST_AUTONOMY.md](HOST_AUTONOMY.md)

## Problem

Sims pans the camera when the cursor sits in the thin edge band. Agents often push the mouse to the edge to scan, then switch to coding with the cursor still there — the camera keeps drifting and the next observation is garbage.

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
