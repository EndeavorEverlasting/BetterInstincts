# Seam Closure Loop (SCL) — repeatable missing-capability recovery

**Owner:** BetterInstincts Play/host handoff (scripts/seam_closure.py).
**Authority:** Read-only recovery and explicit user-launched bootstrap. No new Sims, save, OS, Shell or desktop effect permit.

## Definition and lifecycle

A *seam* is an unimplemented or unbound transition from one repository capability to another. A stale checkout, missing calibrated game observer, incomplete name-to-slot binding, or unresolved responder acknowledgement is a seam. The fix is an owned, deterministic repository capability, not another manual instruction.

1. **Detect:** Existing Play routes emit automation_gaps.
2. **Classify:** scripts.seam_closure.identify creates a stable seam_id, capability, canonical_owner, resolution_state and effect_admission.
3. **Persist:** scripts.launch_receipt.write_result stores the current seam in launch.json and a deduplicated occurrence in the same run's private seam-events.json. Storage is bounded at 32 events and 32 KiB; no background scanner.
4. **Dispatch engineering:** scripts.continue_certification.build_handoff reads the latest private Play run, includes a sanitized summary in the *existing* Codex handoff, and makes the missing owner explicit. An agent may repair and test source, but it receives no new host permission from this receipt.
5. **Validate:** Source tests prove deterministic classification, idempotence and safety. Actual game actions still require exact-build, current process, scene, save, roster, human-control and independent outcome proof.
6. **Register and resume:** Repair the canonical owner, add regression tests, then replay only after all existing admission checks. Reconcile in-flight purchases/acknowledgements rather than repeating effects.

## Checkout seam

When a user explicitly launches the updated Start-BetterInstincts.cmd --upgrade-parts, its owned bootstrap path runs scripts.certification_checkout, fetches the official origin/main, and prepares or reuses a verified, clean detached worktree within the normal user development worktrees directory. It dispatches the existing guarded scripts.play with the exact observed HEAD. Original branches, dirty changes, evidence, saves and ongoing game session are preserved. Unofficial origin, dirty candidate, failed fetch or mismatched Git identity hold without reset, clean or stash.

This is **not** an agent Shell permission workaround. OPERATOR_DESKTOP_BOUNDARY still denies the agent Shell tool. For an older launcher that lacks this code, distribution of the updated product launcher is a separate gate.

## Native observer seam

The private startup context needs a process-bound complete MAIN_MENU save catalog, authorized disposable registry, calibrated selected-slot navigation, and exact-build native bridge. Neither disk existence nor a claimed save name proves the title→slot→roster relation. Missing host evidence remains HOST_BINDING_REQUIRED or HOST_OBSERVATION_REQUIRED; the protected Slot_00000007 must never be opened. The bridge's live adapter gate remains under BetterInstincts issue #171.

## Receipt contract

The private app-owned play-receipts/<run-id>/launch.json and seam-events.json bind each event to an existing run. The separate event record omits raw exception text, private context paths, save titles, Sim names, images and game file contents. The latest-run handoff uses only the most recent owned run; it cannot revive an older blocked run after a newer success. Unknown stages classify as UNREGISTERED_SEAM, denied desktop tools as POLICY_HOLD; every event states effect_admission=NOT_GRANTED.

A seam closes only after code repair, regression proof and a runtime outcome appropriate to that gate. Committed code, green CI or a Play return alone cannot certify portrait switches or a native responder decision.

## Targeted source verification

python -m unittest tests.test_seam_closure tests.test_certification_checkout -v

Mandatory branch ontology consultation and semantic preflight still apply. The current named-save restock needs a fresh catalog-bound save identity and three separately observed portrait switches. Windows runtime and live-game certification are not asserted by these source changes.

## Passive native-runtime notice port (source-ready, installation unverified)

The existing InstalledPlayerRuntime may additionally emit a bounded, sanitized
missing-capability notice during an already registered game callback. This is
opt-in: only an ownership manifest with installed_runtime_seam_port=true and
an exact-build adapter implementing report_runtime_seam(notice) changes the
callback to cycle_with_seam. Existing installations retain the original
cycle callback. Normal YIELD_TO_PLAYER, queued/waiting actions and transient
portrait reobservation do not emit gap reports. Known unqualified native
frames, session rebinds, missing portrait evidence and invalid proposal
identities can emit at most 16 notifications per installed runtime instance,
deduplicated across consecutive repeats. Sink errors leave the original
game callback result unchanged. The native callback itself does no file I/O.

The Windows adapter's report_runtime_seam port must independently match the
selected private Play launch, current PID + creation time + executable +
game version and game-run session before calling the repository-owned
scripts.seam_closure.record_native_notice. A matching advisory event appends
to the original private seam-events.json and appears in the existing Codex
certification handoff as HISTORICAL_NATIVE_NOTICES_REOBSERVE. It does not mean
the condition remains active; the host must reobserve before retry. Unknown
or unbound processes or session tags deny recording. No raw household, Sim
names, save titles or local paths are written to these events.

**Proof ceiling:** Native port contract, passive callback and host-side receipt
intake are source-tested, not installed on the Windows Sims build. The actual
EA-backed adapter and game execution remain owned by #171. A connected SCL
notice alone cannot satisfy the three portrait switches or a responder
decision; both require independently correlated game evidence.
