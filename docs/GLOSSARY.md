# BetterInstincts glossary

Canonical vocabulary for host listeners, evaluators, and autonomy.
**Machine authority:** [`contracts/glossary.v1.json`](../contracts/glossary.v1.json)
**Program design (P95):** [HOST_AUTONOMY.md](HOST_AUTONOMY.md)

Do not invent synonyms in contracts or agent chat. Add terms to the JSON contract first, then document here. The open-domain semantic terms (GOAL_THREAD, CONTINGENCY, RESUME_CONDITION, etc.) have single short definitions in `contracts/glossary.v1.json` and graph owners in `contracts/ontology.v1.json`; do not duplicate rules in this table.

| Term | Meaning |
| --- | --- |
| **PLAYER_FIRST** | Explicit player direction outranks autonomy and host optimization. |
| **PLAYER_PRESENT_ON_CANVAS** | Foreground Sims window and cursor inside the client rect. |
| **PLAYER_PLAYING** | On-canvas, recent input grace, declared playing, or player-directed queue → host yields. |
| **HOST_MAY_AUTOMATE** | Opt-in session active and not `PLAYER_PLAYING`; evaluate / optional execute. |
| **YIELD_TO_PLAYER** | Refuse SendInput; do not rewrite the queue. |
| **HOST_LISTENER** | Opt-in bounded session that ticks observations into evaluators (not a daemon). |
| **HOST_AUTOMATE** | Presence-gated orchestrator over behavior + needs-force plans. |
| **HOST_EVALUATOR** | Read-only scorer (`host_eval`, `behavior_eval`, etc.). |
| **PROGRESSION_EVALUATOR** | P67/P62 CI honesty + product-rate scorer (`progression_eval`). Separates scaffolding from GAME_CERTIFIED trajectory progress. |
| **OUTDOOR_SOCIAL_DEFAULT** | Event/venue anti-pattern: social interactions route outdoors (sidewalk/umbrella) despite free indoor capacity. |
| **EVENT_INDOOR_ROUTING** | Host gate: cancel outdoor social; prefer Sit and Chat Here before weaker Go Here / greet. |
| **SIT_AND_CHAT_HERE** / **SIT_AND_CHAT_HERE_INDOOR** | Seat-grounded indoor chat; primary fix for outdoor-social default. |
| **EVENT_BALANCE_STACK** | Priority stack: player → viewport → survival needs → indoor routing → event goals → Fun-via-goals → homework hold → other needs. |
| **EVENT_GOAL_ACTION** / **EVENT_GOAL_PLAN** | Catalogued pie-menu actions that satisfy HUD event goals; host plan over incomplete goals. |
| **FUN_SERVICE** / **FUN_LANE** / **FUN_CONTENTION** | Parallel Fun activity services; free-lane pick when guests occupy shared objects. |
| **NEED_SERVICES_TANDEM** / **NEED_SERVICE_BASE** / **NEED_LANES** | Six-need tandem registry + P124 shared helpers; Fun nested, other motives use need-lanes. |
| **NEED_SERVICE_HEALTH** / **NEED_SERVICE_DETACH** / **ASSUMPTION_WINDOW** / **NEED_LOAD_BALANCE** | LB health probe, detach dead stacks, reweighted exploration windows; see `docs/NEED_LOAD_BALANCE.md`. |
| **DOMAIN_CASCADE** | Ordered poll receipts across needs→budget→career→skills/whims→relationships; respects LB detach; see `docs/DOMAIN_CASCADE.md`. |
| **CAREER_SERVICES_TANDEM** / **CAREER_OBLIGATION_HELD** / **CAREER_READY_AFTER_NEEDS** | Async career microsystem beside needs; sticky teen homework obligation; resume after survival; see `docs/CAREER_SERVICE.md`. |
| **ASPIRATION_SERVICES_TANDEM** / **ASPIRATION_PROMPT_HELD** / **ASPIRATION_COMPLETION_ENABLED** / **ASPIRATION_COMPLETION_DISABLED** | Async aspirations microsystem beside needs/career; sticky OK/Cancel dialog judgment; lab fails closed on occult life-state; see `docs/ASPIRATION_SERVICE.md`. |
| **BALANCE_SERVICES_TANDEM** / **BALANCE_CONDITION_HELD** / **BALANCE_READY_AFTER_NEEDS** | Async Balance/Imbalance microsystem beside needs; sticky Imbalanced/Very Imbalanced + ailment; Naturopath/Holistic Cure/nature recovery; see `docs/BALANCE_SERVICE.md`. |
| **NAVIGATING_NEEDS_TANDEM** | Discovery Quest panel goals in tandem with host; uncovered urgent falls to need_services. |
| **MOODLET_STRIP** | Bottom-left emotion + moodlet icons; must be supplied to host evals (not inventable from screenshots). |
| **MOODLET_AWARE_ROUTING** | Gate: tense moodlets + outdoor social + indoor capacity reinforce indoor retarget; uncomfortable aligns with survival relief. |
| **SIM_PROFILE_INSPECT** | Read-only host gate: supplied skills/preferences/traits/whims + moodlets; never `practice_skill` / BI-005. |
| **SIMOLOGY_PANEL** | Live Sim Info traits/aspiration surface (not Load Game picker; not patch compatibility profiles). |
| **PLAYER_DISCOVERY_MAP** | Where players look: moodlets, whims, Simology, Skills, Likes & Dislikes, needs. |
| **GOOD_BEHAVIOR** / **BAD_BEHAVIOR** | Matrix verdicts over queue × critical needs. |
| **EMULATE** | Keep the same intent class as a good queue. |
| **OPTIMIZE** | Replace bad/suboptimal queue; never override player direction. |
| **EMULATE_THEN_OPTIMIZE** | Keep good intent; improve routing (e.g. map travel). |
| **MAP_TRAVEL** | Manage Worlds / phone travel to the lot with required objects. |
| **IN_FRAME_WALK_THRASH** | Forbidden: making the Sim pathfind across the current frame instead of traveling. |
| **CRITICAL_NEED** | Motive below `needs.v1.json` urgency threshold. |
| **HOUSEHOLD_FUNDS** | Observed/operator Simoleon balance for the disposable household. |
| **FEDERAL_SUBSIDY_PROMPT** | Funds under 100 → Sims-styled notice; Yes runs durable funds inject. |
| **FUNDS_INJECT** | Ctrl+Shift+C → `testingcheats enabled true` → Money/motherlode in any mode (not BI-004 income). |
| **TESTINGCHEATS_ENABLED_TRUE** | Required before Money; skipping it fails live inject. |
| **CHEAT_CONSOLE_CHORD** | Ctrl+Shift+C opens the cheat console in Live/Build/Buy; required before testingcheats/Money. |
| **MODE_AGNOSTIC_FUNDS_INJECT** | Inject preserves operator mode — never force F1 / Esc-spam while building. |
| **EARN_INCOME_CRITICAL** | Broke money-stat; earn never blocked by purchase lockdown. |
| **HOST_CRISIS_ANTI_PATTERN** | School Join under critical needs/funds — prefer Send Alone. |
| **PROOF_CEILING** / **LOCAL_OBSERVED** / **GAME_CERTIFIED** | Evidence claim limits — see VALIDATION / LIVE_CERT. |
| **LOT_ENVIRONMENT_GAIN** | Wall/Buy décor stat → room Environment Score / Decorated Happy moodlets; stacks per panel. |
| **ECO_FOOTPRINT_GREEN** / **ECO_FOOTPRINT_INDUSTRIAL** | Eco Lifestyle neighborhood Clean Air vs Gross Air contributions; maximize objectives are mutually exclusive. |
| **BILL_POWER** / **BILL_WATER** | Catalog utility axes; lower is better for household bills; null = axis not declared. |
| **BUILD_YIELD_MICROSYSTEM** / **CATEGORY_BEST_POOL** / **CATEGORY_ITEM_HIERARCHY** | Per-category best-value pools and ordered Env/yield hierarchies; yield over aesthetics. |
| **COUNTERTOP_PLACEMENT** / **ISLAND_COUNTER** / **STANDARD_COUNTER** / **BARSTOOL_SEATING_SNAP** | Counter kinds, Auto-Counters shapes, Env cap 2, barstool-only island snap — see `docs/BUILD_OPTIMIZE.md`. |
| **BUILD_OPTIMIZE_PLAN** | Evaluate-only ranked catalog receipt (`build_optimize`); no live paint until P08 disposable Build proof. |
| **LOT_ENVIRONMENT_MODEL** / **RECURSIVE_LOT_MODEL** | Durable revisioned lot understanding that accumulates as we observe and move; see `docs/HOUSE_STATE.md`. |
| **BLANK_SLATE_REASSESS** | Forbidden: discard understanding after an action and reassess the lot from scratch. |
| **HOUSE_STATE_MUTATION_LEASE** | One Build/Buy mutation admitted against the current model revision + targets; outcome merges back into the same model. |
| **BUILD_INTEGRITY** / **STRUCTURE_FIRST_SPATIAL_ADMISSION** | Floor before furniture; indoor≠outdoor; no nesting; protect kitchen/bed/dining — see `docs/BUILD_INTEGRITY.md`. |
| **OUTDOOR_AS_INDOOR** / **PLACE_WITHOUT_FLOOR** | Forbidden: grass-as-interior; indoor place with no attested floor. |
| **BUILD_SPATIAL** / **ENCLOSURE_AND_STORY_AXES** | Inside vs outside + FLOOR_1 vs FLOOR_2 builder axes; see `docs/BUILD_SPATIAL.md`. |
| **BUILD_LIBRARY_CHECKPOINT** / **LIBRARY_SAVE_BEFORE_ROOM_MUTATE** | Sims My Library building save required before room/structure mutation; Save As is not a substitute; see `docs/BUILD_LIBRARY_CHECKPOINT.md`. |
| **FLOOR_1** / **FLOOR_2** | First vs second story; F2 indoor work requires F1 indoor floor first. |
| **BUILD_FLOOR_ACTIVITY** / **FLOOR_ACTIVITY_CENSUS** | Listener peer: which story is active, single vs multi-floor span, theme from attested items. |
| **FLOOR_THEME** | Majority theme on a story (kitchen, bedroom, outdoor_garden, …) from item categories. |
| **CAMERA_SAFE_TRAVERSE** | Host-owned bounded camera plan; never park the mouse in the edge pan band. |
| **SAFE_CURSOR_REST** | Mandatory interior cursor park after any camera step so the viewport stops drifting. |
| **EDGE_MOUSE_PARK** / **CONTINUOUS_EDGE_HOLD** | Forbidden: leave/hold cursor on screen edge while scanning or coding. |
| **CAPTURE_BEFORE_EDGE_SCAN** | Prefer PrintWindow + lot-model observe before any pan. |
| **CAMERA_SAFE_REST** | Host gate that parks to SAFE_CURSOR_REST when edge-park is detected. |
| **CURIOUS_CATALOG** | Opt-in hidden Buy shelves for rare/money gardening; never on startup; never touch game speed. |
| **SHOW_HIDDEN_OBJECTS** | Console line `bb.showhiddenobjects` only — never type `buydebug` or slash-join. Elementary unlock for household useful-item catalog/hidden rows. |
| **HOUSEHOLD_OBJECT_FORCE** | Durable useful-item catalog + planner to force named objects into any household; career promote and catalog paths; no hallucinated hex spawn. |
| **ELEMENTARY_HIDDEN_UNLOCK** | Required `testingcheats true` then `bb.showhiddenobjects` before catalog/hidden force rows; BBB never substitutes. |
| **USEFUL_ITEM_CATALOG** | Machine-owned list of forceable household objects (Desktop, Meat Wall, UFO Bed, Sigma, Smog Vacuum, Hydroponic, optional Positronic Pro). |
| **UI_CHROME** / **HOST_UI_MAP** | Named mode chrome as normalized click targets + recipes; see `docs/UI_CHROME.md`. |
| **HOTKEY_GLOSSARY** | Per-mode chords (F1/F2/F3, Backspace→inventory); intent only, never mode proof. |
| **CATALOG_TO_HOUSEHOLD_INVENTORY** | Search→select→Backspace deposit recipe; forbids lot placement. |
| **AOK_BLOOMER_SEARCH** | Preferred catalog keyword `AOK` for A-OK-Bloomer Vertical Garden. |

Related matrices: `contracts/behavior-matrix.v1.json`, `contracts/player-presence.v1.json`, `contracts/needs-force.v1.json`, `contracts/host-listener.v1.json`, `contracts/host-funds.v1.json`, `contracts/build-optimize.v1.json`, `contracts/household-object-force.v1.json`, `contracts/ui-chrome.v1.json`.
