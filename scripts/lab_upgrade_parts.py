"""Windows launch continuation for the opted-in disposable household restock."""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import re
import subprocess
from types import SimpleNamespace
from uuid import uuid4

from betterinstincts.activity_chain import ActivityChainError, SCHEMA, compile_activity_chain
from betterinstincts.budget_eval import household_reserve
from betterinstincts.computer_upgrade_parts import (
    menu_catalog, plan_computer_restock_batch, verify_computer_batch_purchase,
)
from betterinstincts.player_learning import ACTOR
from betterinstincts.portrait_handoff import choose_selection
from scripts.launch_save_route import CAPTURE
from scripts.smart_start import require_same_game_process

PROTOCOL = "betterinstincts.lab-upgrade-parts-native/v1"
PLANNING = "betterinstincts.lab-upgrade-parts-planning/v1"
RESPONDER_HANDOFF = "betterinstincts.lab-restock-responder-handoff/v1"
TARGET = 99
MAX_ROSTER = 16
MAX_REPLY = 32_768
NOT_AVAILABLE = ("AT_WORK", "AT_SCHOOL", "AWAY", "UNAVAILABLE")
OPERATIONS = frozenset(("observe", "claim_restock_control", "open_active_lot", "play_active_lot",
                        "pause_live", "select_portrait", "open_upgrade_parts",
                        "buy_upgrade_parts", "handoff_to_responder"))


class RestockBlocked(ValueError):
    """An unproved boundary. The controller never repeats a dispatched effect."""


def _opaque(value):
    return isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9_.:-]{3,128}", value)


def _natural(value):
    return type(value) is int and value >= 0


@contextmanager
def save_navigation_listener(session_id="lab-upgrade-parts-launch", *, note="Opt-in lab upgrade-parts launch"):
    """Scope the existing save-menu lease to one explicit launch."""
    from betterinstincts.host_listener import activate, deactivate

    if activate(session_id, note=note).get("state") != "ACTIVATED":
        reason = ("LAB_RESTOCK_STARTUP_LISTENER_ALREADY_ACTIVE" if session_id == "lab-upgrade-parts-launch"
                  else "STARTUP_LISTENER_ALREADY_ACTIVE")
        raise RestockBlocked(reason)
    try:
        yield session_id
    finally:
        deactivate(session_id)


class PinnedNativeBridge:
    """Transport for a private, exact-build Windows binding."""

    def __init__(self, context_path, binding, process, scope, *, protocol, label):
        self.protocol = protocol
        self.label = label
        if not isinstance(binding, dict) or not _opaque(binding.get("binding_ref")):
            raise RestockBlocked(f"EXACT_BUILD_NATIVE_{label}_BINDING_REQUIRED")
        name, digest = binding.get("bridge"), binding.get("sha256")
        if (not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,70}\.exe", name)
                or not isinstance(digest, str) or not re.fullmatch(r"[a-f0-9]{64}", digest)):
            raise RestockBlocked(f"NATIVE_{label}_BRIDGE_IDENTITY_INVALID")
        if not process.game_version or binding.get("game_version") != process.game_version:
            raise RestockBlocked(f"NATIVE_{label}_BINDING_BUILD_MISMATCH")
        self.path = Path(context_path).absolute().parent / name
        self.digest = digest
        self.process = process
        self.scope = {"process": asdict(process), **scope}
        self._verify()

    def _verify(self):
        if (any(p.is_symlink() for p in (self.path, *self.path.parents))
                or not self.path.is_file() or not 0 < self.path.stat().st_size <= 32 * 1024 * 1024):
            raise RestockBlocked(f"NATIVE_{self.label}_BRIDGE_UNAVAILABLE")
        with self.path.open("rb") as binary:
            if hashlib.file_digest(binary, "sha256").hexdigest() != self.digest:
                raise RestockBlocked(f"NATIVE_{self.label}_BRIDGE_HASH_MISMATCH")

    def exchange(self, operation, **payload):
        require_same_game_process(self.process)
        self._verify()
        request = {"protocol": self.protocol, "scope": self.scope, "operation": operation, **payload}
        try:
            run = subprocess.run([str(self.path)], input=json.dumps(request), cwd=self.path.parent,
                                 encoding="utf-8", capture_output=True, timeout=35, check=True)
            if len(run.stdout) > MAX_REPLY:
                raise RestockBlocked(f"NATIVE_{self.label}_REPLY_TOO_LARGE")
            result = json.loads(run.stdout)
        except (OSError, subprocess.SubprocessError, UnicodeError, json.JSONDecodeError) as exc:
            raise RestockBlocked(f"NATIVE_{self.label}_REPLY_UNAVAILABLE") from exc
        require_same_game_process(self.process)
        if (not isinstance(result, dict) or result.get("protocol") != self.protocol
                or result.get("scope") != self.scope):
            raise RestockBlocked(f"NATIVE_{self.label}_REPLY_SCOPE_MISMATCH")
        return result


class NativeBridge(PinnedNativeBridge):
    def __init__(self, context_path, context, process, route):
        self.spend_cap = context.get("approved_spend_cap")
        if not _natural(self.spend_cap):
            raise RestockBlocked("LAB_RESTOCK_APPROVED_SPEND_CAP_REQUIRED")
        scope = {"run_id": route["successor_run_id"], "save_id": route["candidate_save_id"],
                 "household_id": route["household_id"]}
        super().__init__(context_path, context.get("native_upgrade_parts"), process, scope,
                         protocol=PROTOCOL, label="RESTOCK")

    def require_capabilities(self):
        response = self.exchange("capabilities")
        operations = response.get("operations")
        if (response.get("state") != "NATIVE_BINDING_READY" or not isinstance(operations, list)
                or not all(isinstance(op, str) for op in operations)
                or not OPERATIONS.issubset(operations)):
            raise RestockBlocked("NATIVE_RESTOCK_CAPABILITIES_INCOMPLETE")
        if response.get("restock_planning") != PLANNING:
            raise RestockBlocked("NATIVE_RESTOCK_PLANNING_EVIDENCE_CAPABILITY_REQUIRED")
        if response.get("responder_handoff") != RESPONDER_HANDOFF:
            raise RestockBlocked("NATIVE_RESPONDER_HANDOFF_CAPABILITY_REQUIRED")


def _plan_portrait(frame, row, *, picker_open, cost=0, budget=0):
    """Compile the remaining restock chain using the actor's current deadlines."""
    observed_capture = frame["capture"]
    timing = row.get("restock_timing")
    if not isinstance(timing, dict) or timing.get("capture") != observed_capture:
        return {"gate": "CURRENT_RESTOCK_TIMING_REQUIRED"}

    capture = hashlib.sha256(observed_capture.encode()).hexdigest()
    household = hashlib.sha256(frame["household_id"].encode()).hexdigest()
    actor = row["actor"]
    actions = []
    if actor != frame["selected"]:
        actions.append(("select_portrait", "switch_upper_minutes"))
    if not picker_open:
        actions.append(("open_upgrade_parts", "picker_upper_minutes"))
    actions.append(("buy_upgrade_parts", "buy_upper_minutes"))
    steps = []
    for action, duration in actions:
        steps.append({"id": action, "domain": "restock", "kind": "NATIVE_ACTION",
                      "location": "active-lot", "evidence_ref": capture,
                      "after": [steps[-1]["id"]] if steps else [],
                      "upper_minutes": timing.get(duration),
                      "cost": cost if action == "buy_upgrade_parts" else 0})
    snapshot = {"schema": SCHEMA, "mode": "PLANNING", "capture_ref": capture,
                "sim_ref": actor, "household_ref": household, "location": "active-lot",
                "scene_verified": True, "queue_verified": timing.get("queue_verified"),
                "player_directed": timing.get("player_directed"), "needs_safe": timing.get("needs_safe"),
                "minutes_until_work": timing.get("minutes_until_work"),
                "minutes_until_need_floor": timing.get("minutes_until_need_floor"),
                "reserve_minutes": timing.get("reserve_minutes"), "available_funds": budget}
    try:
        plan = compile_activity_chain(snapshot, steps, capture_ref=capture)
    except ActivityChainError:
        return {"gate": "RESTOCK_TIMING_UNQUALIFIED"}
    if plan["gate"] != "PLAN_STAGED":
        return {"gate": plan["gate"]}
    if plan["deferred"]:
        return {"gate": "RESTOCK_CHAIN_EXCEEDS_SAFE_WINDOW"}
    return {"gate": "PLAN_STAGED", "upper_minutes": plan["total_upper_minutes"],
            "available_minutes": plan["available_minutes"],
            "slack_minutes": plan["available_minutes"] - plan["total_upper_minutes"]}


def run_restock(bridge, checkpoint):
    """Drive only the selected lab scope, one verified native effect at a time."""
    parts = menu_catalog()["part_ids"]
    targets = dict.fromkeys(parts, TARGET)
    scope = bridge.scope
    captures = set()
    report = {"target_per_part": TARGET, "household_id": scope["household_id"],
              "spent": 0, "purchases": [], "pending": None,
              "planning": {"schema": PLANNING, "decisions": []}}

    def observe(expected):
        observation_id = uuid4().hex
        response = bridge.exchange("observe", expect=expected, observation_id=observation_id)
        frame = response.get("frame")
        if response.get("observation_id") != observation_id:
            raise RestockBlocked("NATIVE_RESTOCK_OBSERVATION_NOT_CURRENT")
        if not isinstance(frame, dict):
            raise RestockBlocked("NATIVE_RESTOCK_FRAME_MISSING")
        capture = frame.get("capture")
        if (not isinstance(capture, str) or not CAPTURE.fullmatch(capture) or capture in captures
                or frame.get("save_id") != scope["save_id"] or frame.get("scene") not in expected):
            raise RestockBlocked("FRESH_SAVE_AND_SCENE_READBACK_REQUIRED")
        captures.add(capture)
        return frame

    def effect(operation, frame, expected, **payload):
        if (frame.get("player_idle_verified") is not True
                or not _natural(frame.get("input_generation"))):
            raise RestockBlocked("YIELD_TO_PLAYER_OR_UNVERIFIED_INPUT")
        if operation != "claim_restock_control" and frame.get("behavior_owner") != "RESTOCK":
            raise RestockBlocked("NATIVE_RESTOCK_CONTROL_NOT_HELD")
        command = uuid4().hex
        report["pending"] = {"action": operation, "command_id": command,
                             "before_capture": frame["capture"], **payload}
        checkpoint(report)
        ack = bridge.exchange(operation, command_id=command, capture=frame["capture"],
                              input_generation=frame["input_generation"], **payload)
        if ack.get("command_id") != command or ack.get("status") != "APPLIED":
            raise RestockBlocked("NATIVE_RESTOCK_EFFECT_RECONCILIATION_REQUIRED")
        after = observe(expected)
        if after.get("applied_command_id") != command:
            raise RestockBlocked("NATIVE_RESTOCK_EFFECT_RECONCILIATION_REQUIRED")
        if (after.get("player_idle_verified") is not True
                or type(after.get("input_generation")) is not int
                or after["input_generation"] != frame["input_generation"]):
            raise RestockBlocked("PLAYER_RECLAIMED_RECONCILE_LAST_EFFECT")
        if operation != "handoff_to_responder" and after.get("behavior_owner") != "RESTOCK":
            raise RestockBlocked("NATIVE_RESTOCK_CONTROL_NOT_HELD")
        return after

    def clear_effect():
        report["pending"] = None
        checkpoint(report)

    def map_lot(frame):
        active = frame.get("active_households")
        if (not isinstance(active, list) or len(active) != 1 or not isinstance(active[0], dict)
                or active[0].get("household_id") != scope["household_id"]
                or not _opaque(active[0].get("lot_id"))):
            raise RestockBlocked("ACTIVE_MAP_HOUSEHOLD_NOT_UNIQUE_OR_NOT_BOUND_TO_SAVE")
        return active[0]["lot_id"]

    def live_roster(frame, lot):
        rows = frame.get("portraits")
        if (frame.get("household_id") != scope["household_id"] or frame.get("lot_id") != lot
                or frame.get("paused") is not True or not isinstance(rows, list)
                or not 1 <= len(rows) <= MAX_ROSTER):
            raise RestockBlocked("PAUSED_LIVE_HOUSEHOLD_READBACK_REQUIRED")
        roster = {}
        for row in rows:
            actor = row.get("actor") if isinstance(row, dict) else None
            if (not isinstance(actor, str) or not ACTOR.fullmatch(actor) or actor in roster
                    or (row.get("status") != "AVAILABLE" and row.get("status") not in NOT_AVAILABLE)):
                raise RestockBlocked("LIVE_PORTRAIT_ROSTER_UNVERIFIED")
            roster[actor] = row
        if frame.get("selected") not in roster:
            raise RestockBlocked("ACTIVE_PORTRAIT_NOT_VERIFIED")
        return roster

    frame = observe(["WORLD_MAP", "NEIGHBORHOOD_MAP", "LOT_DETAILS"])
    report["save_readback"] = frame["capture"]
    lot = map_lot(frame)
    frame = effect("claim_restock_control", frame, [frame["scene"]], lot_id=lot)
    if map_lot(frame) != lot:
        raise RestockBlocked("ACTIVE_MAP_LOT_CHANGED")
    report["restock_control_capture"] = frame["capture"]
    clear_effect()
    if frame["scene"] != "LOT_DETAILS":
        frame = effect("open_active_lot", frame, ["LOT_DETAILS"], lot_id=lot)
        if map_lot(frame) != lot:
            raise RestockBlocked("ACTIVE_MAP_LOT_CHANGED")
        clear_effect()
    if frame.get("selected_lot_id") != lot:
        raise RestockBlocked("ACTIVE_LOT_CARD_NOT_VERIFIED")
    frame = effect("play_active_lot", frame, ["LIVE"], lot_id=lot)
    if (frame.get("household_id") != scope["household_id"] or frame.get("lot_id") != lot
            or type(frame.get("paused")) is not bool):
        raise RestockBlocked("LIVE_HOUSEHOLD_READBACK_REQUIRED")
    clear_effect()
    if not frame["paused"]:
        frame = effect("pause_live", frame, ["LIVE"], lot_id=lot)
    roster = live_roster(frame, lot)
    roster_ids = tuple(roster)
    report["household_readback"] = frame["capture"]
    clear_effect()

    for _ in range(MAX_ROSTER + 1):
        roster = live_roster(frame, lot)
        if tuple(roster) != roster_ids:
            raise RestockBlocked("LIVE_PORTRAIT_ROSTER_CHANGED")
        available = {key: row for key, row in roster.items() if row["status"] == "AVAILABLE"}
        restocks = {key: plan_computer_restock_batch(stock_targets=targets,
                    pocket_counts=row.get("pocket_counts")) for key, row in available.items()}
        needed = {key: plan for key, plan in restocks.items() if plan["quantities"]}
        if any(purchase["actor"] in needed for purchase in report["purchases"]):
            raise RestockBlocked("COMPLETED_PORTRAIT_STOCK_CHANGED")
        if not needed:
            if "picker" not in frame or frame["picker"] is not None:
                raise RestockBlocked("CLOSED_PICKER_REQUIRED_FOR_NATIVE_HANDOFF")
            report.update(state="RESTOCK_VERIFIED" if available else "NO_AVAILABLE_PORTRAITS",
                          final_capture=frame["capture"],
                          verified_available=list(available),
                          final_inventory={key: {part: row["pocket_counts"][part] for part in parts}
                                           for key, row in available.items()},
                          skipped={key: row["status"] for key, row in roster.items()
                                   if key not in available})
            checkpoint(report)
            _handoff_to_responder(frame, lot, scope, report, effect, observe, clear_effect)
            return report
        selected = frame["selected"]
        picker_open = frame.get("picker") is not None
        candidates = {key: _plan_portrait(frame, available[key], picker_open=picker_open)
                      for key in needed if not picker_open or key == selected}
        ready = [key for key, plan in candidates.items() if plan["gate"] == "PLAN_STAGED"]
        actor = min(ready, key=lambda key: (candidates[key]["available_minutes"], key != selected,
                                           candidates[key]["slack_minutes"]), default=None)
        planning = report["planning"]
        if not planning["decisions"]:
            planning["initial_candidates"] = candidates
            planning["initial_selected"] = selected
        decision = {"capture": frame["capture"], "target": actor}
        planning["decisions"].append(decision)
        if actor is None:
            report["planning"]["hold"] = candidates
        checkpoint(report)
        if actor is None:
            raise RestockBlocked("NO_PORTRAIT_RESTOCK_CHAIN_FITS_CURRENT_EVIDENCE")
        if actor != selected:
            packet = {"capture": frame["capture"], "household": scope["household_id"],
                      "selected": selected, "save": hashlib.sha256(scope["save_id"].encode()).hexdigest(),
                      "goal": "upgrade-parts-restock", "purpose": "TARGET", "target": actor,
                      "roster": roster_ids, "safe_to_leave": frame.get("picker") is None,
                      "members": {key: "READY" if key in needed else
                                  "COVERED" if key in available else "UNAVAILABLE" for key in roster}}
            _, selection = choose_selection(SimpleNamespace(
                actor=selected, capture=frame["capture"], household=scope["household_id"]), packet)
            if selection is None:
                raise RestockBlocked("SHARED_PORTRAIT_HANDOFF_NOT_READY")
            actor = selection.target
            frame = effect("select_portrait", frame, ["LIVE"], actor=actor)
            if frame.get("selected") != actor or tuple(live_roster(frame, lot)) != roster_ids:
                raise RestockBlocked("PORTRAIT_CHANGE_NOT_OBSERVED")
            decision["selected_capture"] = frame["capture"]
            clear_effect()
        frame = _restock_selected(frame, actor, lot, roster_ids, parts, targets, effect,
                                  live_roster, clear_effect, report, bridge.spend_cap)
    raise RestockBlocked("RESTOCK_ROSTER_PASS_LIMIT")


def _handoff_to_responder(frame, lot, scope, report, effect, observe, clear_effect):
    """Transfer control once, then wait for evidence of a separate native decision."""
    ready = effect("handoff_to_responder", frame, ["LIVE"], lot_id=lot)
    command_id = report["pending"]["command_id"]

    def responder_readback(current):
        responder = current.get("responder")
        if (current.get("household_id") != scope["household_id"] or current.get("lot_id") != lot
                or current.get("paused") is not False or current.get("behavior_owner") != "NATIVE_RESPONDER"
                or "picker" not in current or current["picker"] is not None
                or not isinstance(responder, dict) or responder.get("registered") is not True
                or responder.get("handoff_command_id") != command_id):
            raise RestockBlocked("NATIVE_RESPONDER_HANDOFF_READBACK_REQUIRED")
        return responder

    responder_readback(ready)
    report["handoff"] = {"state": "RESPONDER_CONTROL_OBSERVED", "capture": ready["capture"],
                         "command_id": command_id}
    clear_effect()
    for _ in range(4):
        current = observe(["LIVE"])
        responder = responder_readback(current)
        decision = responder.get("decision_ref")
        if (current.get("player_idle_verified") is True
                and responder.get("decision_state") == "DECISION_OBSERVED" and _opaque(decision)
                and responder.get("decision_capture") == current["capture"]):
            report["handoff"].update(state="NATIVE_RESPONDER_DECISION_OBSERVED",
                                     decision_ref=decision, decision_capture=current["capture"])
            clear_effect()
            return
    raise RestockBlocked("NATIVE_RESPONDER_FIRST_DECISION_NOT_OBSERVED")


def _restock_selected(frame, actor, lot, roster_ids, parts, targets, effect,
                      live_roster, clear_effect, report, spend_cap):
    row = live_roster(frame, lot)[actor]
    if row["status"] != "AVAILABLE":
        raise RestockBlocked("PLANNED_PORTRAIT_NO_LONGER_AVAILABLE")
    picker_open = frame.get("picker") is not None
    if _plan_portrait(frame, row, picker_open=picker_open)["gate"] != "PLAN_STAGED":
        raise RestockBlocked("REOBSERVE_SELECTED_PORTRAIT_RESTOCK_WINDOW")
    computer = frame.get("computer_id")
    if not _opaque(computer) or frame.get("computer_available_to_selected") is not True:
        raise RestockBlocked("OBSERVED_ON_LOT_COMPUTER_REQUIRED")
    if frame.get("picker") is None:
        frame = effect("open_upgrade_parts", frame, ["LIVE"], actor=actor, computer_id=computer)
    rows = live_roster(frame, lot)
    picker = frame.get("picker")
    if (tuple(rows) != roster_ids or frame.get("selected") != actor
            or rows[actor]["status"] != "AVAILABLE" or not isinstance(picker, dict)
            or picker.get("actor") != actor or picker.get("computer_id") != computer
            or not _opaque(picker.get("revision")) or picker.get("cart_empty") is not True):
        raise RestockBlocked("EXACT_EMPTY_COMPUTER_UPGRADE_PICKER_REQUIRED")
    clear_effect()
    stock = rows[actor]["pocket_counts"]
    plan = plan_computer_restock_batch(stock_targets=targets, pocket_counts=stock)
    quantities = plan["quantities"]
    if not quantities:
        raise RestockBlocked("RESTOCK_CHANGED_WITH_PICKER_OPEN")
    funds, prices = frame.get("funds"), picker.get("unit_prices")
    if (not _natural(funds) or not isinstance(prices, dict) or set(prices) != set(parts)
            or not all(_natural(price) for price in prices.values())):
        raise RestockBlocked("FIVE_VERIFIED_PRICES_AND_FUNDS_REQUIRED")
    cost = sum(count * prices[part] for part, count in quantities.items())
    budget = min(spend_cap - report["spent"], household_reserve(funds)["spend_max"])
    if cost > budget:
        raise RestockBlocked("RESTOCK_EXCEEDS_HOUSEHOLD_RESERVE_OR_APPROVED_CAP")
    quoted = _plan_portrait(frame, rows[actor], picker_open=True, cost=cost, budget=budget)
    report["planning"]["decisions"][-1]["quote"] = {
        "capture": frame["capture"], "cost": cost, "budget": budget, "gate": quoted["gate"],
    }
    clear_effect()
    if quoted["gate"] != "PLAN_STAGED":
        raise RestockBlocked("REOBSERVE_QUOTED_PORTRAIT_RESTOCK_WINDOW")
    after = effect("buy_upgrade_parts", frame, ["LIVE"], actor=actor, computer_id=computer,
                   revision=picker["revision"], quantities=quantities, total_cost=cost,
                   expected_funds=funds, expected_pocket_counts={part: stock[part] for part in parts},
                   unit_prices=prices)
    current = live_roster(after, lot)
    if (tuple(current) != roster_ids or after.get("selected") != actor
            or after.get("picker") is not None):
        raise RestockBlocked("PURCHASE_RECIPIENT_OR_PICKER_READBACK_MISMATCH")
    readback = verify_computer_batch_purchase(requests=quantities, inventory_before=stock,
                inventory_after=current[actor].get("pocket_counts"), funds_before=funds,
                funds_after=after.get("funds"), expected_total_cost=cost)
    if readback["state"] != "BATCH_PURCHASE_OBSERVED":
        raise RestockBlocked("PURCHASE_INVENTORY_AND_FUNDS_RECONCILIATION_REQUIRED")
    report["spent"] += cost
    report["purchases"].append({"actor": actor, "quantities": quantities, "spent": cost,
                                "outcome_capture": after["capture"]})
    clear_effect()
    return after
