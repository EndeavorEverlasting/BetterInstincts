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
