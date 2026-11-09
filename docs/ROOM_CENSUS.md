# Room census — operator runbook

**Executable owner:** [`betterinstincts/room_census.py`](../betterinstincts/room_census.py) and [`contracts/room-census.v1.json`](../contracts/room-census.v1.json). **State owner:** [`betterinstincts/house_state.py`](../betterinstincts/house_state.py). **Definitions:** [glossary](GLOSSARY.md) / [machine terms](../contracts/glossary.v1.json).

## Offline interface

Read an **existing, explicitly supplied** revisioned lot model; the census does not discover game files or rooms itself.

```sh
python -m scripts.room_census taxonomy
python -m scripts.room_census evaluate --model dist/house-state/<run_id>/<lot>.model.json
```

Build/Buy observations can optionally pass `lot_model` to `build_floor_activity` / `host_listener` for a compact advisory summary. Full item lists remain in the explicit census result. Every observed story can be listed; missing coverage is **not** evidence that a floor or room does not exist. No game inputs or save mutations.

**P08 live-game gate:** independently certify exact-patch floor/room geometry, indoor/outdoor boundaries, object presence and style observations on a protected-safe lab session; offline CI cannot close BI-002.

**Prompt routing:** Moonwake **P95 → P124 → P78** (glossary/documentation diet); Trifecta **P08** live proof, **P82** measured offline tests, **P07** integration. See [prompt provenance](PROMPT_INVOCATIONS.md).
