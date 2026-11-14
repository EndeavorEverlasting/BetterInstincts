# Bottom-right HUD panel intelligence — source and screenshot stage

**Owner:** `betterinstincts/hud_panel_state.py` (host perception and non-effect intent only).
**Contract:** `contracts/bottom-right-panel-states.v1.json`.
**Consultation:** `BI-BOTTOM-RIGHT-PANEL-STATE-SIXTH-GEAR-20261114`.
**Proof:** eight of eight November 14 operator-provided 1919×1079 screenshots classified in an offline, non-OCR pixel run. Native Sims effect **not** certified.

## Semantic ontology

Each canonical bottom-right module (`ui_microsystems` owns the IDs and `ui_chrome` owns hotkeys) has separate fields:

| Property | Domain | Meaning |
| --- | --- | --- |
| `panel_id` | Existing canonical panel name | Which module is being observed |
| `visibility` | `COLLAPSED`, `CONDENSED`, `EXPANDED`, `UNKNOWN` | Whether this module is open and at maximum height |
| `expansion` | [0,1] or null | Continuous normalized height within calibrated min/max, not item scroll |
| `inventory_scroll` | `UNKNOWN` until separately observed | Scroll position of the *contents* |
| `selected_sim` | `UNKNOWN` until independently read | Actor/portrait; never guessed from panel geometry |
| `panel_owner` | `HOST`, `OPERATOR`, `UNKNOWN` | Which actor initiated the panel; unknown is not a host permit |

**Condensed is not a single pixel size.** A panel stays condensed throughout the continuum below its measured maximum. Expanded means maximum, collapsed means that *module* is absent. The bottom-right navigation strip is not itself an expanded inventory panel.

## Perception adapter

The first attested host image sensor recognizes the personal inventory on game build `1.121.361.1020` and exactly `1919×1079` pixels. It uses two independent pixel-color cues: the **Filter Items...** title band and the **Drag here to sell** band. It does not invoke OCR or an agent to label the picture. From the title's measured Y anchor, it estimates continuous height against max≈217px and min≈727px. Conflicting cues, wrong build, game mode, or resolution yield `UNKNOWN`, not a guessed action. The attached screenshots were read for offline classification, not committed to the public repository.

User capture classification:
- Screenshot 1: inventory collapsed.
- Screenshot 2: condensed minimum.
- Screenshot 3: expanded maximum.
- Screenshots 4–7: condensed at approximately 75%, 57%, 40%, 28%.
- Screenshot 8: condensed minimum.
- Screenshot 9: cropped navigation strip; useful for module order, **not** an inventory height measurement.

Each *other* module uses the shared generic `classify_calibrated_bounds` semantics only after its own physical sensor, two independent cues and min/max measurements are attested. Until then its visual presence is `UNKNOWN`. Existing Skills panel grip calibration is not automatically an inventory drag calibration.

## Run once against an operator-approved capture

Host Python must have Pillow available. Run with an explicit image; no background capture or global input listener:

```sh
python -m scripts.hud_panel_state --image "capture.png" --mode LIVE --patch 1.121.361.1020
python -m scripts.hud_panel_state --image "capture.png" --mode LIVE --intent INVENTORY_AUDIT
```

The second command intentionally returns `HOLD` without fresh `--operator-idle --panel-owner HOST --scene-fresh --sim-fresh --visible-panel-id personal_inventory` confirmations. Even with those supplied, it returns a **non-executable** intent proposal, never mouse or keyboard input.

## Deterministic posture policy

- **QUICK_STATUS / SINGLE_ITEM** → condensed when host-owned and already open; no needless resize if already in compact range.
- **LONG_LIST / INVENTORY_AUDIT / SCROLL_SEARCH** → expanded to maximize visible entries, reducing mouse interactions; *scroll traversal* remains a separate owner.
- **FINISHED** → collapsed **only if opened/owned by the host**, otherwise leave the operator's panel intact.
- **Unknown purpose, conflicting cues, current different panel, active operator, stale scene/Sim identity** → `HOLD`.
- **Required open/resize/close** → semantic `REQUEST_...` with `execute_allowed: false`; independent effect admission must route through the existing `ui_chrome` hotkeys, `screen_atlas` calibration, and `CooperativeScreenQueue`. The proposal cannot itself click, drag or toggle a live panel.

**Native boundary:** The previously live-verified `SimTravel` observer receipt does not establish UI drag, interaction completion or gameplay dispatch. This module cannot dispatch. If a future locally admitted host test uses the screen, it must preserve the paused sleep action and player-first 15-second idle/focus/queue protocol. The native mod's installed garden automation and rollback still require separate issue #171/BI-002 local certification.

## Validation

```sh
python -m unittest tests.test_hud_panel_state -v
python -m scripts.check_native_gameplay_authority --base-ref <EXACT_PR_BASE_COMMIT_SHA>
python -m scripts.semantic_preflight --consultation contracts/consultations/BI-BOTTOM-RIGHT-PANEL-STATE-SIXTH-GEAR-20261114.v1.json --operation repo_mutation --file betterinstincts/hud_panel_state.py
python -m scripts.check_human_sovereignty --json
```

Static and screenshot classifications are independent of packaging, branch merge and observed gameplay. No user files or game assets need be distributed.
