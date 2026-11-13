"""Pure, deterministic household-region navigation; never a Sims input adapter."""
from __future__ import annotations

from heapq import heappop, heappush
from typing import Any, Mapping

from betterinstincts.traversal_cost_learning import apply_learned_costs

MAX_REGIONS = 128
MAX_PASSAGES = 512
MAX_TRACE = 32
ALLOWED_SOURCES = frozenset({"GAME_ROUTE_PROBE", "OPERATOR_VERIFIED_TRAVERSAL"})
PROGRESS_KINDS = frozenset({"REGION_DISCOVERED", "OBJECT_DISCOVERED", "GOAL_OUTCOME"})


def _receipt(data: Mapping[str, Any], state: str, reason: str, **extra: Any) -> dict:
    row = {
        "schema": "betterinstincts.household-navigation.plan/v1",
        "state": state, "reason": reason, "mode": data.get("mode"),
        "objective_id": data.get("objective_id"), "scope_id": data.get("scope_id"),
        "actor_id": data.get("actor_id"), "scene_revision": data.get("scene_revision"),
        "graph_revision": data.get("graph_revision"), "route": [], "next_region": None,
        "execute_allowed": False, "control_permit": None,
        "effects_issued": 0, "goal_complete": False,
        "evidence_ceiling": "OFFLINE_ROUTE_PROPOSAL_NOT_SIM_MOVEMENT_OR_LIVE_CERT",
    }
    row.update(extra)
    return row


def _path(graph: dict[str, dict[str, int]], start: str, goal: str) -> tuple[str, ...]:
    """A* with a zero admissible heuristic: bounded Dijkstra, stable ties."""
    first = (0, 0, (start,))
    best = {start: first}
    todo = [(0, 0, (start,), start)]
    while todo:
        cost, hops, path, node = heappop(todo)
        if best[node] != (cost, hops, path):
            continue
        if node == goal:
            return path
        for nxt, weight in sorted(graph[node].items()):
            rank = (cost + weight, hops + 1, path + (nxt,))
            if nxt not in best or rank < best[nxt]:
                best[nxt] = rank
                heappush(todo, (*rank, nxt))
    return ()


def _graph(data: Mapping[str, Any]) -> tuple[dict[str, dict[str, int]], int] | None:
    regions, passages = data.get("regions"), data.get("passages")
    if (not isinstance(regions, dict) or not 1 <= len(regions) <= MAX_REGIONS
            or not isinstance(passages, list) or len(passages) > MAX_PASSAGES):
        return None
    valid: set[str] = set()
    for key, row in regions.items():
        if (isinstance(key, str) and 1 <= len(key) <= 96
                and isinstance(row, Mapping)
                and row.get("lot_id") == data["lot_id"]
                and row.get("lot_status") == "VERIFIED_ON_LOT"
                and row.get("observed") is True
                and type(row.get("floor")) is int):
            valid.add(key)
    graph = {name: {} for name in sorted(valid)}
    excluded = 0
    for row in passages:
        if not isinstance(row, Mapping):
            excluded += 1
            continue
        a, b, w = row.get("from"), row.get("to"), row.get("cost")
        if (not isinstance(a, str) or not isinstance(b, str)
                or a not in valid or b not in valid or a == b
                or row.get("kind") != "WALKABLE_PASSAGE"
                or row.get("verified") is not True
                or row.get("source") not in ALLOWED_SOURCES
                or row.get("graph_revision") != data["graph_revision"]
                or row.get("lot_id") != data["lot_id"]
                or type(w) is not int or not 1 <= w <= 1000
                or type(row.get("bidirectional")) is not bool):
            excluded += 1
            continue
        graph[a][b] = min(graph[a].get(b, w), w)
        if row["bidirectional"]:
            graph[b][a] = min(graph[b].get(a, w), w)
    return graph, excluded


def _trace(data: Mapping[str, Any], valid: set[str]) -> tuple[list[str], bool] | None:
    events = data.get("trace", [])
    if not isinstance(events, list) or len(events) > MAX_TRACE:
        return None
    positions, novelty = [], []
    for row in events:
        if (not isinstance(row, Mapping)
                or row.get("scope_id") != data["scope_id"]
                or row.get("actor_id") != data["actor_id"]
                or not isinstance(row.get("region_id"), str)
                or row["region_id"] not in valid
                or type(row.get("progress")) is not bool):
            return None
        if row["progress"] and (row.get("progress_kind") not in PROGRESS_KINDS
                                or not isinstance(row.get("evidence_ref"), str)
                                or not row["evidence_ref"].strip()):
            return None
        positions.append(row["region_id"])
        novelty.append(row["progress"])
    if positions and positions[-1] != data["current_region"]:
        return None
    abab = (len(positions) >= 4 and positions[-4] == positions[-2]
            and positions[-3] == positions[-1] and positions[-4] != positions[-3]
            and not any(novelty[-3:]))
    immobile = (len(positions) >= 3 and len(set(positions[-3:])) == 1
                and not any(novelty[-3:]))
    return positions, abab or immobile


def plan_household_navigation(snapshot: Mapping[str, Any]) -> dict:
    """Propose routes/frontiers; a separate game host must admit every effect."""
    if not isinstance(snapshot, Mapping):
        return _receipt({}, "NAVIGATION_ABSTAIN", "SNAPSHOT_INVALID")
    data = snapshot
    scope = ("scope_id", "save_scope_id", "household_id", "lot_id", "actor_id",
             "game_build", "scene_revision", "graph_revision", "objective_id")
    if any(not isinstance(data.get(k), str) or not data[k].strip() for k in scope):
        return _receipt(data, "NAVIGATION_ABSTAIN", "SCOPE_OR_REVISION_UNVERIFIED")
    if data.get("human_present") is not False:
        return _receipt(data, "NAVIGATION_PAUSED_FOR_HUMAN", "PRESENCE_ACTIVE_OR_UNKNOWN")
    if data.get("scene") != "LIVE_MODE" or data.get("observed_scene_revision") != data["scene_revision"]:
        return _receipt(data, "NAVIGATION_ABSTAIN", "SCENE_STALE_OR_UNVERIFIED")
    if data.get("position_source") not in {"GAME_STATE", "HOST_VERIFIED_OBSERVATION"}:
        return _receipt(data, "NAVIGATION_ABSTAIN", "ACTOR_POSITION_UNVERIFIED")
    mode = data.get("mode")
    if mode not in {"GOAL_ROUTING", "DISCOVERY"}:
        return _receipt(data, "NAVIGATION_ABSTAIN", "MODE_UNKNOWN")
    assembled = _graph(data)
    if assembled is None:
        return _receipt(data, "NAVIGATION_ABSTAIN", "GRAPH_INVALID_OR_UNBOUNDED")
    graph, excluded = assembled
    # Learning may rank only existing source-verified passages; it cannot add
    # new edges, claim movement or bypass the current actor/scene gates.
    graph, learning_status, learned_edges = apply_learned_costs(data, graph)
    current = data.get("current_region")
    if not isinstance(current, str) or current not in graph:
        return _receipt(data, "NAVIGATION_RELOCALIZE", "CURRENT_REGION_UNKNOWN_OR_OFF_LOT")
    observed = _trace(data, set(graph))
    if observed is None:
        return _receipt(data, "NAVIGATION_ABSTAIN", "TRACE_STALE_OR_CROSS_SCOPE")
    positions, stalled = observed
    if mode == "GOAL_ROUTING":
        target = data.get("goal_region")
        if not isinstance(target, str) or target not in graph:
            return _receipt(data, "NAVIGATION_ABSTAIN", "GOAL_UNKNOWN_OR_OFF_LOT")
        if current == target:
            return _receipt(data, "NAVIGATION_ARRIVED_AWAIT_OUTCOME", "AT_GOAL_NOT_INTERACTION_COMPLETE")
        targets = [target]
    else:
        visited = data.get("visited_regions")
        if not isinstance(visited, list) or any(not isinstance(x, str) or x not in graph for x in visited):
            return _receipt(data, "NAVIGATION_ABSTAIN", "VISIT_EVIDENCE_INVALID")
        if current not in visited:
            return _receipt(data, "NAVIGATION_OBSERVE_REGION", "CURRENT_UNVISITED_REGION",
                            next_region=current, excluded_unverified_passages=excluded)
        targets = sorted(set(graph) - set(visited))
        if not targets:
            return _receipt(data, "NAVIGATION_KNOWN_GRAPH_COVERED",
                            "NO_NEW_KNOWN_REGION_NOT_FULL_HOUSEHOLD_PROOF")
    limit = data.get("max_route_steps", 16)
    if type(limit) is not int or not 1 <= limit <= 32:
        return _receipt(data, "NAVIGATION_ABSTAIN", "ROUTE_BUDGET_INVALID")
    blocked = set()
    failed = data.get("failed_transitions", [])
    if not isinstance(failed, list) or len(failed) > MAX_PASSAGES:
        return _receipt(data, "NAVIGATION_ABSTAIN", "FAILED_EDGE_HISTORY_INVALID")
    for row in failed:
        if (not isinstance(row, Mapping) or row.get("scope_id") != data["scope_id"]
                or row.get("actor_id") != data["actor_id"]):
            return _receipt(data, "NAVIGATION_ABSTAIN", "FAILED_EDGE_CROSS_SCOPE")
        if row.get("graph_revision") != data["graph_revision"]:
            return _receipt(data, "NAVIGATION_ABSTAIN", "FAILED_EDGE_REVISION_STALE")
        if (not isinstance(row.get("from"), str) or not isinstance(row.get("to"), str)
                or row["from"] not in graph or row["to"] not in graph
                or type(row.get("failures")) is not int or row["failures"] < 0):
            return _receipt(data, "NAVIGATION_ABSTAIN", "FAILED_EDGE_INVALID")
        if row["failures"] >= 2:
            blocked.add((row["from"], row["to"]))
    if stalled and len(positions) >= 2:
        blocked.add((current, positions[-2]))
    for a, b in blocked:
        graph[a].pop(b, None)
    options = []
    for target in targets:
        path = _path(graph, current, target)
        if path:
            cost = sum(graph[a][b] for a, b in zip(path, path[1:]))
            options.append((cost, len(path), target, path))
    if not options:
        return _receipt(data, "NAVIGATION_STALL_ABSTAIN" if stalled else "NAVIGATION_NO_SAFE_ROUTE",
                        "NO_VERIFIED_ALTERNATIVE" if stalled else "TARGET_UNREACHABLE_IN_VERIFIED_GRAPH",
                        excluded_unverified_passages=excluded, blocked_transitions=len(blocked))
    _, _, target, path = min(options)
    if len(path) - 1 > limit:
        return _receipt(data, "NAVIGATION_ROUTE_BUDGET_HOLD", "ROUTE_EXCEEDS_STEP_BUDGET")
    result = _receipt(data, "NAVIGATION_RECOVERY_ROUTE" if stalled else "NAVIGATION_ROUTE_PROPOSED",
                      "REPLAN_AROUND_NO_PROGRESS" if stalled else "VERIFIED_STABLE_ROUTE",
                      route=list(path), next_region=path[1], target_region=target,
                      excluded_unverified_passages=excluded, blocked_transitions=len(blocked),
                      movement_channel="SIM_ROUTE_PROPOSAL_ONLY",
                      learning_status=learning_status,
                      learned_edge_count=learned_edges)
    # This opt-in model is a diagnostic only. Never use its score to create
    # edges, override verified Dijkstra weights, or grant movement.
    if "spatial_convolution" in data:
        row = data["spatial_convolution"]
        if not isinstance(row, Mapping) or row.get("from_region") != current or row.get("to_region") != path[1]:
            result["spatial_learning_advisory"] = {
                "status": "ABSTAIN_TARGET_MISMATCH", "blocked_probability": None, "execute_allowed": False,
            }
        else:
            from betterinstincts.spatial_convolution import advise
            result["spatial_learning_advisory"] = advise(
                data, row.get("model"), row.get("patch"),
                from_region=current, to_region=path[1],
            )
    return result


__all__ = ["plan_household_navigation", "MAX_REGIONS", "MAX_PASSAGES", "MAX_TRACE"]
