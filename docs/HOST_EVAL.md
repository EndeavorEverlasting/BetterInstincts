# Host journey evaluator — P95 + P67 + P62

Pure deterministic, offline evaluation for the chosen-save boot-to-map-to-Live call stack and six-needs recovery. It **does not** access the Windows Sims process or certify a playable mod.

**Journey:** supplied versioned scenes/PrintWindow observations -> `scripts.host_eval` -> `betterinstincts.host_eval` -> exact-patch/registered-LAB-save/scene/timing/viewport/safety gates -> existing `host_stack.evaluate_turn` + need delta scorer -> independent metrics, findings and next-upgrade codes. No clicks, restarts or save modifications in evaluator.

**Run:** `python -m scripts.host_eval --out dist/host-eval/current.json`. The receipt is ignored and must remain inside the `dist/host-eval` root. Fixtures: `tests/fixtures/host-eval.v1.json`. CI and `python -m unittest tests.test_host_eval -v` enforce 14 positive/negative and historical regression cases.

**Black incident:** the `black_viewport` fixture blocks when PrintWindow remains FULL_CLIENT_BLACK; the restart case only passes on **synthetic**, explicitly authorized restart plus disposable relaunch and PrintWindow recheck. Historical PID 45380 is **not** evidence that the process is still running. Before applying the already-authorized `viewport_recover` command, the local agent must check the current TS4 window/PID and verify the disposable run. No Resume, Richardson/user saves, overwrite or forced termination. See `contracts/viewport-black.v1.json`.

**Next local-agent gate:** resolve fresh process; run the existing guarded restart if still needed, then launch/select registered Charlee LabLab disposable save and verify PrintWindow CONTENT_PRESENT plus two independent map/Live cues. Prefer Send Alone; control the home lot, ensure required objects, recover hunger/bladder/energy/hygiene/fun/social to green, and Save As a new BI_CONT slot only after green with authorization. Record real capture references and turn observations for the evaluator. Keep BI-002 vanilla 5 + modified 5 hunger trials and rollback separate from this offline suite.

**Whims and skills:** optional before/after observed slots and skill levels are measured; absence is SENSOR_NOT_SUPPLIED. Six measurement slots do not assert six live game whims exist, and no Sims API hook is claimed. Eval proof ceiling: offline supplied evidence; game and mod certification remain unresolved.
