# Natural semantic survey — portable SLAM strengthening

**State:** offline, read-only candidate. **Owner:** `betterinstincts/observation_sweep.py`; EA index owner `betterinstincts/ea_geometry_intake.py`. Original semantic 3D model and floor graph remain canonical; no new map cache. This does not certify live Sims interaction or decode native building geometry.

## P141 strategy before Fifth Gear

Evaluated (1) reconstructing undocumented EA machine code at runtime; (2) fixed N/NE/E ring and multiple drags; (3) a persistent screen-pixel click atlas; and (4) an EA-source-first semantic map with a stationary-first, minimum-novelty camera gesture. Selected (4). Native executable hooking has no verified, versioned ABI; DBPF only proves TGI keys and sizes, not floor/story/wall positions. Geometry can be promoted only after a lawful, exact-build, read-only decoder and measured local samples. A 2D screen overlap is not 3D containment or wall elevation.

## Stable call stack

1. Exact app location is irrelevant: `from betterinstincts.observation_sweep import plan_observation_sweep`. Python 3.11+ standard library, OS-independent `pathlib`, no cwd assumption or hardcoded Sims install path.
2. If the operator expressly selects a disposable `.package`, `inspect_ea_package(path, declared_game_build="1.121.361.1020")` inspects its DBPF index and SHA-256 by bounded read. Version is **declared**, not discovered or verified. Never walk user home, open `saves`/`Tray` or `Slot_00000007`, decompress assets, ship EA content or execute EA native code.
3. Only a separately admitted EA geometry reader or calibrated screen sensor supplies camera/floor-revision-bound candidate views with two distinct independent evidence references. `plan_observation_sweep` validates identity, same camera and floor, novelty, path size, viewport bounds and previous view.
4. **Reuse existing coverage** when the object is already observed. **Capture in place** when geometry is missing or uncertain. **Hold** on stale camera. **Yield** to a player. At most one continuously eased trajectory is a possible next view; never a default 2–4 stop-start compass motion, never auto-return in an A-B-A loop.
5. `plan_room_map_traverse(..., survey={...})` surfaces the advisory proposal. The old `ring_directions` field remains solely for backward-compatible map documentation; it must not be interpreted as automatic actuation. Any actual game input needs current player idle/focus, scene/save/lot/target admission, single host owner, post-motion capture, and a verified disposable run. All plans return `execute_allowed=false` and no permit.

## Verification, guardrails and performance

```sh
python -m unittest tests.test_observation_sweep tests.test_ea_geometry_intake -v
python -m scripts.semantic_preflight --consultation contracts/consultations/BI-NATURAL-SEMANTIC-SURVEY-20261112.v1.json --operation repo_mutation --file betterinstincts/observation_sweep.py --file betterinstincts/ea_geometry_intake.py --file betterinstincts/room_map_traverse.py
python -m scripts.check_native_gameplay_authority --base-ref MAIN_SHA
python -m scripts.check_world_traversal_harness
```

Max 32 candidates, 64 observations/required IDs, bounded 13-waypoint pure computation and no polling or writes. Tests cover deterministic ordering, no-motion path, monotone one-gesture easing, previous-view guard, stale and player-active gates, symlink/protected-save rejection and identical package identity from different directory roots.

**P08 remains unobserved:** this provider connection is not the operator's Sims host. A native-game capability would still require exact patch tuning/script-source research, approved disposable scene and full protected regression. Existing BI-002 hunger gate and sensor PR #159 remain independent.


## 2026-11-12 — P97 → P141 → Fifth Gear feedback and motion hardening

P97 evaluated ROS Nav2's bounded, failure-aware smoothing and active-perception information gain; source citations and pattern dispositions are in [PRIOR_ART.md](PRIOR_ART.md). P141 rejected autonomous background input control, duplicate dense SLAM infrastructure and smoothing without post-motion feedback. P95 designed a backward-compatible keyword-only extension of the existing pure planner. P82 falsifiers cover stale/insufficient evidence, opt-in, pending motion, recent-view cycles, and a quintic curve. P08 actual Sims scene/camera test is NOT_RUN outside the operator's local game host. P07/P124 integrate the single owner, decision contract, tests and documentation.

**New read-only API:** \`plan_observation_sweep(..., motion_opt_in=False, pending_view_id=None, recent_view_ids=())\`.
- \`motion_opt_in=False\` defaults to **HOLD**; setting it true authorizes *consideration of a proposal*, never an actual game motion or unattended watcher.
- \`pending_view_id\` blocks subsequent gestures until a separate host captures and independently reconciles what actually happened; the host must not clear it without observed results.
- \`recent_view_ids\` (max 8) suppresses recent-cycle A↔B or A↔B↔C proposals. No persistent tracking or storage is created here; external approved host owns provenance and bounded memory.
- Each candidate now must provide aligned \`evidence_refs\` and distinct \`evidence_source_classes\` using \`HOST_CAPTURE\`, \`EA_FILE\`, or \`OPERATOR_REVIEW\`. These are semantic labels from an independently admitted sensor, *not proof of authenticity* in isolation. Legacy unclassified candidates are deliberately non-actionable.
- A selected sweep has at most 13 waypoints from the quintic \`10t³−15t⁴+6t⁵\`, with zero endpoint velocity and acceleration in normalized time and no reversal. Tiny sub-8px proposals are skipped. Waypoints do not determine real host gesture timing or guarantee visible motion quality.

**No covert behavior:** no silent daemon, polling worker, focus stealing, telemetry, stealth logging or autonomous mouse movement is enabled. Product aspiration is imperceptible overhead, not concealed user control.

**Local proof gate:** genuine consented disposable Sims session with calibrated viewpoint inputs, camera actuator temporal profile, input interruption probes, FPS/latency measurements and A/B path recordings. Only then can actual smoothness and gameplay correctness be certified.
