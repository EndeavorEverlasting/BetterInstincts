# Household navigation — deterministic region routing and anti-oscillation

Status: P00 ontology + P01 harness + Moonwake Fifth Gear P95 → P82 → P08 → P07 → P124. Offline source candidate, not a Sims 4 runtime agent or playable mod.

## Separate authorities

The Sims walking route is NOT a camera pan. The existing lot_floor_map stores object landmarks, relative directions and camera coordinates; relative ADJACENT, PAN_HINT and CORNER_OF edges never certify walkability. The existing camera_traverse owns camera framing; world_traversal_learning owns highlight and post-click evidence. This contract adds a pure region-graph planner only, without second desktop control arbiter or new UI effect.

## Scope and decision

Input is scoped to an opaque save, household, lot, actor, exact game-build label and scene/graph revisions. Regions require independently verified on-lot status and an observed floor. Passages must be verified WALKABLE_PASSAGE edges bound to the current graph revision, same lot and GAME_ROUTE_PROBE or OPERATOR_VERIFIED_TRAVERSAL provenance. No EA-file or protected save reads are performed.

GOAL_ROUTING retains the named objective and uses the lowest cost verified route. DISCOVERY chooses an already observed, verified but unvisited and reachable region, or proposes observation of the current region. A shortest-path plan uses Dijkstra (A* with zero admissible heuristic), with deterministic cost, hop and lexicographic path tie-breakers. Capacity is 128 regions, 512 edges, 32 history events and 32 planned steps maximum.

## Anti-oscillation

Movement or a fresh camera frame alone is NOT progress. Only evidenced REGION_DISCOVERED, OBJECT_DISCOVERED or GOAL_OUTCOME with a source reference may count as novelty. A no-progress A-B-A-B sequence, or three stationary no-progress observations, triggers STALL. The current reversal is excluded from the proposed graph, and the next route uses another verified edge or abstains. Two graph-revision-bound failures on a directed edge temporarily exclude that edge; changes in graph revision require fresh history. Never auto-repeat a click or ignore a failed step.

Arriving at a target is not an action outcome. Route proposals always return execute_allowed false and control_permit null; independent save, scene, lot, exact patch, operator presence and per-effect screen admission must be satisfied by a separately authorized game executor. Never switch portrait, modify OS settings, change keyboard/peripheral state, mutate saves or leave the active lot from this planner. Human input or unknown presence yields.

## Offline acceptance and P08 ceiling

Run: python -m scripts.check_household_navigation ; python -m unittest tests.test_household_navigation -v ; python -m scripts.check_ontology ; python -m unittest discover -s tests -v.

The synthetic suite exercises stable weighted routes, frontier choice, A-B-A-B alternate/dead-end outcomes, blocked edges, camera-hint and off-lot denial, actor/save separation, stale scene, human takeover and arrival evidence. Offline checks cannot certify local Sims movement. P08 requires operator-approved disposable game save, exact build, independently observed walkability/scene/actor, permitted game-side route and fresh objective outcome; protected saves and BI-002 remain unchanged.
