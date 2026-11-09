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
