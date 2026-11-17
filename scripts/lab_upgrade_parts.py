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

from betterinstincts.budget_eval import household_reserve
from betterinstincts.computer_upgrade_parts import (
    menu_catalog, plan_computer_restock_batch, verify_computer_batch_purchase,
)
from betterinstincts.player_learning import ACTOR
from betterinstincts.portrait_handoff import choose_selection
from scripts.launch_save_route import CAPTURE
from scripts.smart_start import require_same_game_process

PROTOCOL = "betterinstincts.lab-upgrade-parts-native/v1"
TARGET = 99
MAX_ROSTER = 16
MAX_REPLY = 32_768
NOT_AVAILABLE = ("AT_WORK", "AT_SCHOOL", "AWAY", "UNAVAILABLE")
OPERATIONS = frozenset(("observe", "open_active_lot", "play_active_lot", "pause_live",
                        "select_portrait", "open_upgrade_parts", "buy_upgrade_parts"))


class RestockBlocked(ValueError):
    """An unproved boundary. The controller never repeats a dispatched effect."""


def _opaque(value):
    return isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9_.:-]{3,128}", value)


def _natural(value):
    return type(value) is int and value >= 0


@contextmanager
def save_navigation_listener():
    """Scope the existing save-menu lease to this explicit restock launch."""
    from betterinstincts.host_listener import activate, deactivate

    session_id = "lab-upgrade-parts-launch"
    if activate(session_id, note="Opt-in lab upgrade-parts launch").get("state") != "ACTIVATED":
        raise RestockBlocked("LAB_RESTOCK_STARTUP_LISTENER_ALREADY_ACTIVE")
    try:
        yield session_id
    finally:
        deactivate(session_id)


class NativeBridge:
    """A private, pinned Windows binding for independently inspected EA APIs."""

    def __init__(self, context_path, context, process, route):
        binding = context.get("native_upgrade_parts")
        if not isinstance(binding, dict) or not _opaque(binding.get("binding_ref")):
            raise RestockBlocked("EXACT_BUILD_NATIVE_RESTOCK_BINDING_REQUIRED")
        name, digest = binding.get("bridge"), binding.get("sha256")
        if (not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,70}\.exe", name)
                or not isinstance(digest, str) or not re.fullmatch(r"[a-f0-9]{64}", digest)):
            raise RestockBlocked("NATIVE_RESTOCK_BRIDGE_IDENTITY_INVALID")
        if binding.get("game_version") != process.game_version:
            raise RestockBlocked("NATIVE_RESTOCK_BINDING_BUILD_MISMATCH")
        self.spend_cap = context.get("approved_spend_cap")
        if not _natural(self.spend_cap):
            raise RestockBlocked("LAB_RESTOCK_APPROVED_SPEND_CAP_REQUIRED")
        self.path = Path(context_path).absolute().parent / name
        self.digest = digest
        self.process = process
        self.scope = {"process": asdict(process), "run_id": route["successor_run_id"],
                      "save_id": route["candidate_save_id"], "household_id": route["household_id"]}
        self._verify()

    def _verify(self):
        if (any(p.is_symlink() for p in (self.path, *self.path.parents))
                or not self.path.is_file() or not 0 < self.path.stat().st_size <= 32 * 1024 * 1024):
            raise RestockBlocked("NATIVE_RESTOCK_BRIDGE_UNAVAILABLE")
        with self.path.open("rb") as binary:
            if hashlib.file_digest(binary, "sha256").hexdigest() != self.digest:
                raise RestockBlocked("NATIVE_RESTOCK_BRIDGE_HASH_MISMATCH")

    def exchange(self, operation, **payload):
        require_same_game_process(self.process)
        self._verify()
        request = {"protocol": PROTOCOL, "scope": self.scope, "operation": operation, **payload}
        try:
            run = subprocess.run([str(self.path)], input=json.dumps(request), cwd=self.path.parent,
                                 encoding="utf-8", capture_output=True, timeout=35, check=True)
            if len(run.stdout) > MAX_REPLY:
                raise RestockBlocked("NATIVE_RESTOCK_REPLY_TOO_LARGE")
            result = json.loads(run.stdout)
        except (OSError, subprocess.SubprocessError, UnicodeError, json.JSONDecodeError) as exc:
            raise RestockBlocked("NATIVE_RESTOCK_REPLY_UNAVAILABLE") from exc
        require_same_game_process(self.process)
        if (not isinstance(result, dict) or result.get("protocol") != PROTOCOL
                or result.get("scope") != self.scope):
            raise RestockBlocked("NATIVE_RESTOCK_REPLY_SCOPE_MISMATCH")
        return result

    def require_capabilities(self):
        response = self.exchange("capabilities")
        operations = response.get("operations")
        if (response.get("state") != "NATIVE_BINDING_READY" or not isinstance(operations, list)
                or not all(isinstance(op, str) for op in operations)
                or not OPERATIONS.issubset(operations)):
            raise RestockBlocked("NATIVE_RESTOCK_CAPABILITIES_INCOMPLETE")


def run_restock(bridge, checkpoint):
    """Drive only the selected lab scope, one verified native effect at a time."""
    parts = menu_catalog()["part_ids"]
    targets = dict.fromkeys(parts, TARGET)
    scope = bridge.scope
    captures = set()
    report = {"target_per_part": TARGET, "household_id": scope["household_id"],
              "spent": 0, "purchases": [], "pending": None}

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
            report.update(state="RESTOCK_VERIFIED" if available else "NO_AVAILABLE_PORTRAITS",
                          verified_available=list(available),
                          skipped={key: row["status"] for key, row in roster.items()
                                   if key not in available})
            checkpoint(report)
            return report
        actor = frame["selected"]
        if actor not in needed:
            packet = {"capture": frame["capture"], "household": scope["household_id"],
                      "selected": actor, "save": hashlib.sha256(scope["save_id"].encode()).hexdigest(),
                      "goal": "upgrade-parts-restock", "purpose": "UPGRADE_PARTS",
                      "roster": roster_ids, "safe_to_leave": frame.get("picker") is None,
                      "members": {key: "READY" if key in needed else
                                  "COVERED" if key in available else "UNAVAILABLE" for key in roster}}
            _, selection = choose_selection(SimpleNamespace(
                actor=actor, capture=frame["capture"], household=scope["household_id"]), packet)
            if selection is None:
                raise RestockBlocked("SHARED_PORTRAIT_HANDOFF_NOT_READY")
            actor = selection.target
            frame = effect("select_portrait", frame, ["LIVE"], actor=actor)
            if frame.get("selected") != actor or tuple(live_roster(frame, lot)) != roster_ids:
                raise RestockBlocked("PORTRAIT_CHANGE_NOT_OBSERVED")
            clear_effect()
        frame = _restock_selected(frame, actor, lot, roster_ids, parts, targets, effect,
                                  live_roster, clear_effect, report, bridge.spend_cap)
    raise RestockBlocked("RESTOCK_ROSTER_PASS_LIMIT")


def _restock_selected(frame, actor, lot, roster_ids, parts, targets, effect,
                      live_roster, clear_effect, report, spend_cap):
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
    after = effect("buy_upgrade_parts", frame, ["LIVE"], actor=actor, computer_id=computer,
                   revision=picker["revision"], quantities=quantities, total_cost=cost,
                   expected_funds=funds, unit_prices=prices)
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
