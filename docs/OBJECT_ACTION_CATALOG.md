# Object-action utility catalog — portable learned interactions

Owner: [object_action_catalog.py](../betterinstincts/object_action_catalog.py)
Machine contract: [object-action-catalog.v1.json](../contracts/object-action-catalog.v1.json)
Existing event lifecycle: [host_listener.py](../betterinstincts/host_listener.py)
Current product gate: **BI-002 hunger live A/B and rollback remains active**.

## Intent

An active BetterInstincts listener may receive a semantic observation when the
player or host opens an object menu, selects one listed action, or observes its
outcome. Each event contributes to a bounded class-level catalog. The stable
key is **exact game patch + object class + action identity**. Transient object
references bind individual observations to a menu; they are **not** generic
model keys. No Sim name, household, world or save file is hard-coded.

The catalog distinguishes:

1. **Discovered availability:** the action appeared in the visible menu.
2. **Observed selection:** player/host selected an action *from that menu*.
3. **Observed outcome:** a later capture relates to that interaction.
4. **Reviewed utility:** an operator reviewed independently supplied evidence
   that the outcome helped or harmed one or more goal domains.

Supported domains are the six needs, money, skills and career. A visible
interaction alone can never establish utility. Unknown or unreviewed outcomes
remain catalog evidence, not positive labels.

## Call stack

A calibrated game sensor or explicitly supplied observation invokes:

\`scripts.host_listener object-event\` → \`host_listener.observe_object_action\`
→ \`object_action_catalog.record_event\` → \`ingest\` → atomic local index at
\`dist/host-listener/object-action-catalog.v1.json\`.

The existing listener requires explicit \`activate\` and explicit opt-in for
each object-event entrypoint. **This implementation does not install a global
mouse/keyboard hook, autonomously read Sims menus, intercept other Windows
applications, or send game input.** A local calibrated sensor must invoke this
port for every real user/host interaction it observes. Consequently this
repository code does not yet establish 100% runtime interaction coverage.

At each normal \`tick\`, an optional \`object_catalog_query\` attached to the
same snapshot is resolved by the *existing* passive opportunity survey. The
query must have the active game version and capture reference, matching the
menu/target/class/current action list, with a fresh Live-mode scene. The
listener overrides proposed player-state flags using actual handoff state.
Player activity wins; no learned action can cancel a player-directed queue.
A matching read-only candidate is surfaced at
\`tick.opportunity_survey.object_action_hint\`. It never dispatches an action.

## Example event sequence

All identifiers below are sanitized semantic tokens, **not** user names or
opaque raw tooltip strings. Use unique 1-based \`seq\` per explicit session.
The sequence is monotonic. An old sequence is a no-op; a missing sequence
is an error. Each outcome must refer to an earlier selection and use an
independent later capture. Reuse the same patch even across different saves
to build portable class knowledge.

\`\`\`json
{"schema":"betterinstincts.object-action-event/v1","kind":"menu","seq":1,"at_ms":100000,"capture_ref":"capture:open_menu","source":"PLAYER","object_ref":"object:bed_a","class_ref":"object_class:bed","game_version":"1.121.361.1020","actions":["action:sleep","action:nap"]}
\`\`\`

\`\`\`json
{"schema":"betterinstincts.object-action-event/v1","kind":"selection","seq":2,"at_ms":100100,"capture_ref":"capture:open_menu","source":"PLAYER","object_ref":"object:bed_a","class_ref":"object_class:bed","game_version":"1.121.361.1020","action_ref":"action:sleep","interaction_ref":"interaction:sleep_01"}
\`\`\`

\`\`\`json
{"schema":"betterinstincts.object-action-event/v1","kind":"outcome","seq":3,"at_ms":100200,"capture_ref":"capture:after_sleep","source":"SENSOR","interaction_ref":"interaction:sleep_01","operator_reviewed":true,"effects":[{"domain":"energy","result":"helpful","evidence_ref":"evidence:energy_delta_01"}]}
\`\`\`

For each event, save the exact JSON as a small local file and run:

\`\`\`sh
python -m scripts.host_listener activate --session-id sample_observer
python -m scripts.host_listener object-event --session-id sample_observer --event PATH_TO_EVENT_JSON --explicit-opt-in
\`\`\`

Invoke each of the three events in order. The CLI is a bounded, *supplied
evidence* port, not an automatic observer. Repeating a menu observation with
a new sequence strengthens availability only, not usefulness. To obtain a
useful recommendation the same class/action/domain needs at least **three
operator-reviewed helpful outcomes** and a helpful rate of at least 75%.
Unreviewed or inconsistent observations force abstention.

After learning, provide a current menu query:

\`\`\`json
{"game_version":"1.121.361.1020","object_ref":"object:bed_a","class_ref":"object_class:bed","capture_ref":"capture:open_menu","now_ms":100220,"available_actions":["action:sleep","action:nap"],"desired_domains":["energy"],"player_active":false,"player_queue_present":false}
\`\`\`

\`\`\`sh
python -m scripts.host_listener object-recommend --session-id sample_observer --query PATH_TO_QUERY_JSON
python -m scripts.host_listener deactivate --session-id sample_observer
\`\`\`

This example's single reviewed outcome is **insufficient** for promotion.
A real sensor must submit *fresh* independent menu/current-context evidence
for the query. For listener tick integration the query also belongs in the
active tick observation as \`object_catalog_query\`, with the same
\`capture_ref\` and \`game_version\`; Live scene evidence must already pass.

## Determinism and safe boundaries

- Event fields are exact and bounded; no unknown fields, screenshots, free
  text, raw input streams, telemetry or game user-data paths enter the index.
- Current session/patch/object/capture/menu must agree; a menu is fresh for
  at most 30 seconds and an outcome must follow a selection within 10 minutes.
- Outcomes are context-qualified, but their usefulness labels are still
  human-reviewed **advisory evidence**, not a proof that a specific future
  Sim can perform the action or will achieve the same result.
- Index storage is local under the explicit host listener's \`dist\` root,
  atomic and locked; capacity limits fail closed instead of creating logs,
  daemons or uncontrolled growth.
- Recommendations must pass the established current actor/target/scene,
  screen admission, lot-boundary, queue capacity, effects authority and
  cooperative human-control gates **before** a separate live executor may
  schedule or click anything. The catalog itself does not grant these permits.
- No automatic global polling, OS service/settings changes, peripheral
  repairs, save edits, purchases, player queue cancellation or gameplay
  certification are implied.

## P95/P82/P08/P07/P124 verification route

P95: the complete menu → selection → outcome → reviewed utility → fresh
advisory path is a testable function seam, with owners explicit.

P82: unit tests measure evidence promotion, portability across object
instances, opt-in lifecycle, idempotence, stale/patch/capture rejection,
negative/harmful observations and player precedence. Refine any failed test
before promotion.

P08: a **local Sims 4 host is required** to certify a game sensor, menu
identities, real effects, player takeover and whether queue candidates are
actually useful under differing packs/households. A GitHub connector or
offline test cannot supply that proof. Restrict to a disposable game/save and
the existing host safety requirements.

P07: commit scoped code/contracts/tests/docs, verify provider revision and
CI, then merge when green and authorized; do not conflate PR with main.

P124: retain separate owners for game observations, learned class utility,
queue planning and final input authority. Do not bury event parsing inside
\`host_listener.tick\` or fork the existing hover/affordance memory.

## Remaining runtime dependency

A calibrated Sims-side semantic event adapter must observe **every relevant
real object menu/selection/outcome** and call this event port while the
listener is explicitly active. That sensor does not exist merely because
the API is committed. The live queue executor likewise needs independent
P08 admission, not a shortcut through the learning index. These are
explicitly unproven local-game gates, not BI-002 completion.
