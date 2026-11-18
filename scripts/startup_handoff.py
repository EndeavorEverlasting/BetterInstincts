"""Continue an authorized Play launch with exact-build native observations."""
from __future__ import annotations

from uuid import uuid4

from betterinstincts.player_learning import ACTOR
from betterinstincts.save_policy import RUN_ID_RE
from scripts.lab_upgrade_parts import PinnedNativeBridge, _natural, _opaque
from scripts.launch_save_route import CAPTURE

PROTOCOL = "betterinstincts.native-startup/v1"
MAP_SCENES = ("WORLD_MAP", "NEIGHBORHOOD_MAP", "LOT_DETAILS")
OPERATIONS = {"read_save_catalog", "observe", "open_active_lot", "play_active_lot"}


class StartupBlocked(ValueError):
    """Current startup evidence did not admit the next transition."""


class StartupBridge(PinnedNativeBridge):
    def __init__(self, context_path, context, process):
        run = context.get("run_id")
        if not isinstance(run, str) or not RUN_ID_RE.fullmatch(run):
            raise StartupBlocked("NATIVE_STARTUP_RUN_REQUIRED")
        super().__init__(context_path, context.get("native_startup"), process,
                         {"run_id": run, "startup_id": uuid4().hex},
                         protocol=PROTOCOL, label="STARTUP")

    def read_save_catalog(self):
        capabilities = self.exchange("capabilities")
        operations = capabilities.get("operations")
        if (capabilities.get("state") != "NATIVE_BINDING_READY"
                or not isinstance(operations, list)
                or not all(isinstance(op, str) for op in operations)
                or not OPERATIONS.issubset(operations)):
            raise StartupBlocked("NATIVE_STARTUP_CAPABILITIES_INCOMPLETE")
        query = uuid4().hex
        response = self.exchange("read_save_catalog", observation_id=query)
        if response.get("observation_id") != query:
            raise StartupBlocked("NATIVE_STARTUP_CATALOG_NOT_CURRENT")
        if response.get("state") == "EXISTING_SESSION_IN_PROGRESS":
            raise StartupBlocked("EXISTING_SESSION_PRESERVED")
        catalog = response.get("catalog")
        if response.get("state") != "MAIN_MENU_OBSERVED" or not isinstance(catalog, dict):
            raise StartupBlocked("NATIVE_STARTUP_CATALOG_UNAVAILABLE")
        return catalog


def continue_startup(bridge, route, catalog_capture, checkpoint):
    """Enter one scoped household and independently observe the installed responder."""
    save = route["candidate_save_id"]
    target = {"save_id": save, "slot": route["candidate_slot"],
              "household_id": route.get("household_id")}
    expected_roster = set(route.get("household_member_ids", ()))
    admitted_households = ({target["household_id"]} if target["household_id"] is not None
                           else set(route.get("candidate_household_ids", ())))
    captures = {catalog_capture}
    report = {"state": "WAITING_FOR_SAVE_READBACK", "target": target, "pending": None}
    checkpoint(report)

    def observe(scenes):
        query = uuid4().hex
        reply = bridge.exchange("observe", observation_id=query, target=target, expect=list(scenes))
        frame = reply.get("frame")
        if reply.get("observation_id") != query or not isinstance(frame, dict):
            raise StartupBlocked("NATIVE_STARTUP_OBSERVATION_NOT_CURRENT")
        capture = frame.get("capture")
        if (not isinstance(capture, str) or not CAPTURE.fullmatch(capture) or capture in captures
                or frame.get("save_id") != save or frame.get("slot") != target["slot"]
                or frame.get("scene") not in scenes):
            raise StartupBlocked("NATIVE_STARTUP_SAVE_OR_SCENE_UNVERIFIED")
        captures.add(capture)
        return frame

    def identity(current):
        if current["scene"] == "LIVE":
            household, lot = current.get("household_id"), current.get("lot_id")
        else:
            active = current.get("active_households")
            if not isinstance(active, list) or len(active) != 1 or not isinstance(active[0], dict):
                raise StartupBlocked("STARTUP_ACTIVE_MAP_HOUSEHOLD_AMBIGUOUS")
            household, lot = active[0].get("household_id"), active[0].get("lot_id")
        if not isinstance(household, str) or household not in admitted_households or not _opaque(lot):
            raise StartupBlocked("STARTUP_ACTIVE_HOUSEHOLD_OR_LOT_MISMATCH")
        return household, lot

    def idle(frame):
        if frame.get("player_idle_verified") is not True or not _natural(frame.get("input_generation")):
            raise StartupBlocked("STARTUP_YIELD_TO_PLAYER")
        return frame["input_generation"]

    frame = observe((*MAP_SCENES, "LIVE"))
    report.update(state="SAVE_OBSERVED", save_readback=frame["capture"])
    checkpoint(report)
    household, lot = identity(frame)
    generation = idle(frame)

    def effect(operation, before, scene):
        command = uuid4().hex
        effect_target = {**target, "household_id": household, "lot_id": lot}
        report["pending"] = {"operation": operation, "command_id": command, "capture": before["capture"],
                             "target": effect_target}
        checkpoint(report)
        ack = bridge.exchange(operation, command_id=command, capture=before["capture"],
                              target=effect_target, input_generation=generation)
        if ack.get("command_id") != command or ack.get("status") != "APPLIED":
            raise StartupBlocked("STARTUP_EFFECT_RECONCILIATION_REQUIRED")
        after = observe((scene,))
        if after.get("applied_command_id") != command:
            raise StartupBlocked("STARTUP_EFFECT_RECONCILIATION_REQUIRED")
        if idle(after) != generation or identity(after) != (household, lot):
            raise StartupBlocked("STARTUP_CONTROL_OR_TARGET_CHANGED")
        return after

    if frame["scene"] in MAP_SCENES:
        if frame["scene"] != "LOT_DETAILS":
            frame = effect("open_active_lot", frame, "LOT_DETAILS")
        if frame.get("selected_lot_id") != lot:
            raise StartupBlocked("STARTUP_LOT_CARD_UNVERIFIED")
        report.update(state="LOT_CARD_OBSERVED", lot_capture=frame["capture"], pending=None)
        checkpoint(report)
        frame = effect("play_active_lot", frame, "LIVE")

    def live_roster(current):
        roster = current.get("roster")
        if (not isinstance(roster, list) or not 1 <= len(roster) <= 16
                or not all(isinstance(sim, str) and ACTOR.fullmatch(sim) for sim in roster)
                or len(set(roster)) != len(roster) or current.get("selected") not in roster
                or not expected_roster.issubset(roster)):
            raise StartupBlocked("STARTUP_LIVE_ROSTER_UNVERIFIED")
        return tuple(roster)

    roster = live_roster(frame)
    entry_command = report["pending"]["command_id"] if report["pending"] else None
    report.update(state="LIVE_HOUSEHOLD_OBSERVED", household_id=household, lot_id=lot,
                  household_readback=frame["capture"], entry_command_id=entry_command, pending=None)
    checkpoint(report)
    for _ in range(4):
        current = observe(("LIVE",))
        if idle(current) != generation or identity(current) != (household, lot) or live_roster(current) != roster:
            raise StartupBlocked("STARTUP_CONTROL_OR_TARGET_CHANGED")
        responder = current.get("responder")
        if (current.get("behavior_owner") != "NATIVE_RESPONDER" or current.get("playing") is not True
                or not isinstance(responder, dict) or responder.get("registered") is not True
                or responder.get("startup_id") != bridge.scope["startup_id"]
                or "entry_command_id" not in responder or responder["entry_command_id"] != entry_command):
            if "responder_control_capture" in report:
                raise StartupBlocked("STARTUP_RESPONDER_CONTROL_CHANGED")
            continue
        if "responder_control_capture" not in report:
            report.update(state="RESPONDER_CONTROL_OBSERVED", responder_control_capture=current["capture"])
            checkpoint(report)
            continue
        if (responder.get("decision_state") == "DECISION_OBSERVED"
                and _opaque(responder.get("decision_ref"))
                and responder.get("decision_capture") == current["capture"]):
            report.update(state="NATIVE_RESPONDER_DECISION_OBSERVED", decision_ref=responder["decision_ref"],
                          decision_capture=current["capture"])
            checkpoint(report)
            return report
    raise StartupBlocked("NATIVE_STARTUP_RESPONDER_DECISION_NOT_OBSERVED")
