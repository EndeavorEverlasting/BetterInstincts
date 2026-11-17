"""Game-embedded policy port. The exact-build EA adapter owns registration and effects."""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import sqlite3
from time import monotonic
from typing import Mapping

from betterinstincts import judgment_learning, player_learning

IDLE_SECONDS = 5
MAX_PROBE_AGE_SECONDS = 1
MANIFEST = "BetterInstincts_Ecology.ownership.json"
MAX_ATTEMPTS_PER_RUN = 256
MAX_FAME_ACTORS = 32


@dataclass(frozen=True)
class Frame:
    """One frame from the installed adapter, on the game's callback thread."""
    game_build: str
    run: str
    household: str
    actor: str
    live: bool
    save_admitted: bool
    playing: bool
    player_active: bool
    player_queue: bool
    activity_trusted: bool
    input_generation: int
    observed_at: float
    idle_seconds: float
    capture: str
    modal_open: bool = False
    modal_ref: str | None = None
    save_ref: str | None = None
    restock_has_control: bool = False

    def scope(self):
        return self.game_build, self.run, self.household, self.actor


class InstalledPlayerRuntime:
    """One permitted game session. No thread, timer, Git, socket or desktop input."""

    def __init__(self, adapter, *, build: str, owned_dir: Path, clock=monotonic,
                 trait_response=None, fairy_dust=None, fame=None, portraits=None,
                 activity_chain=None):
        self.adapter = adapter
        self.build = build
        self.path = owned_dir / "player-learning.sqlite3"
        self.pending = None
        self.ticks = 0
        self.registered = False
        self.run = None
        self.attempts = set()
        self.unresolved = None
        self.clock = clock
        self.trait_response = trait_response
        self.fairy_dust = fairy_dust
        self.dust_attempts = {}
        self.dust_recheck = None
        self.fame = fame
        self.fame_tracks = {}
        self.fame_attempts = {}
        self.fame_streams = {}
        self.fame_training = {}
        self.fame_receipt = None
        self.portraits = portraits
        self.portrait_pending = None
        self.portrait_readback = None
        self.activity_chain = activity_chain
        self.activity_plan = None
        self.activity_admission = None
        self.activity_attempts = set()

    def _select_portrait(self, first):
        try:
            state, selection = self.portraits.choose_selection(
                first, self.adapter.read_portrait_handoff(first))
        except Exception:
            return "PORTRAIT_EVIDENCE_UNQUALIFIED"
        if selection is None:
            return None if state in ("NO_PORTRAIT_GOAL", "NO_ELIGIBLE_PORTRAIT",
                                     "PORTRAIT_ALREADY_SELECTED") else state
        fresh = self.adapter.frame()
        if (not self._fresh_idle_after(first, fresh) or fresh.modal_open is not False
                or fresh.playing is not first.playing):
            return "YIELD_TO_PLAYER"
        try:
            planned, _, _ = self.adapter.analyze(fresh)
            if not isinstance(planned, Mapping) or planned:
                return "PORTRAIT_SELECTION_REOBSERVE"
            _, current = self.portraits.choose_selection(
                fresh, self.adapter.read_portrait_handoff(fresh))
        except Exception:
            return "PORTRAIT_EVIDENCE_UNQUALIFIED"
        if current != selection or not self._idle(fresh):
            return "PORTRAIT_SELECTION_REOBSERVE"

        identity = (fresh.run, fresh.household, selection.save, "PORTRAIT",
                    selection.purpose, selection.goal, selection.target)
        if identity in self.attempts:
            return "DUPLICATE_PORTRAIT_PROPOSAL"
        if len(self.attempts) >= MAX_ATTEMPTS_PER_RUN:
            return "NATIVE_SESSION_ATTEMPT_LIMIT"
        attempt = self.portraits.Attempt(selection, fresh.run, fresh.household,
                                         fresh.input_generation, first.capture, fresh.capture,
                                         fresh.observed_at)
        # Retain the attempt before the native call. An exception can occur
        # after EA accepts the request, so no return value clears the latch.
        self.portrait_pending = attempt
        self.attempts.add(identity)
        try:
            self.adapter.submit_portrait_if_current(attempt, fresh)
        except Exception:
            return "PORTRAIT_SWITCH_RECONCILE"
        return "PORTRAIT_SWITCH_AWAITING_READBACK"

    def _reconcile_portrait(self, frame):
        attempt = self.portrait_pending
        try:
            outcome = self.adapter.read_portrait_outcome(attempt, frame)
            state = self.portraits.outcome_state(frame, attempt, outcome)
        except Exception:
            return "PORTRAIT_SWITCH_RECONCILE"
        if state != "PORTRAIT_SWITCH_RECONCILE":
            self.portrait_pending = None
            self.portrait_readback = frame
        return state

    def _fresh_live(self, frame):
        return (isinstance(frame, Frame) and frame.game_build == self.build
                and frame.live is True and frame.save_admitted is True
                and isinstance(frame.run, str) and player_learning.TOKEN.fullmatch(frame.run)
                and isinstance(frame.household, str) and player_learning.TOKEN.fullmatch(frame.household)
                and isinstance(frame.actor, str) and player_learning.ACTOR.fullmatch(frame.actor)
                and isinstance(frame.capture, str) and player_learning.CAPTURE.fullmatch(frame.capture)
                and type(frame.observed_at) in (int, float)
                and 0 <= self.clock() - frame.observed_at <= MAX_PROBE_AGE_SECONDS)

    def _idle(self, frame):
        return (self._fresh_live(frame) and frame.activity_trusted is True
                and frame.restock_has_control is False
                and frame.player_active is False and frame.player_queue is False
                and type(frame.input_generation) is int and frame.input_generation >= 0
                and type(frame.idle_seconds) in (int, float)
                and IDLE_SECONDS <= frame.idle_seconds < float("inf"))

    def observe(self, frame, event, needs):
        """Use the same semantic learner as the host listener while the player plays."""
        if not self.registered or not self._fresh_live(frame):
            self.pending = None
            return player_learning.receipt("ABSTAIN", reason="NATIVE_FRAME_UNQUALIFIED")
        self.ticks += 1
        if (not isinstance(event, Mapping) or event.get("run") != frame.run
                or event.get("household") != frame.household or event.get("platform") != "windows"
                or (self.run is not None and self.run != frame.run)):
            self.pending = None
            return player_learning.receipt("ABSTAIN", reason="NATIVE_EVIDENCE_SCOPE_MISMATCH")
        self.run = frame.run
        try:
            self.pending, result = player_learning.observe(
                self.path, event, pending=self.pending, tick=self.ticks, exact_patch=self.build,
                actor=frame.actor, capture=frame.capture, process_id=0, needs=needs,
                player_active=frame.player_active is True or frame.player_queue is True,
                queue_busy=not self._idle(frame) or frame.playing is not True or frame.modal_open is not False,
            )
            return result
        except (TypeError, KeyError, AttributeError, player_learning.PlayerLearningError,
                judgment_learning.JudgmentLearningError):
            self.pending = None
            return player_learning.receipt("ABSTAIN", reason="NATIVE_EVIDENCE_INVALID")
        except (OSError, sqlite3.Error):
            return player_learning.receipt("ABSTAIN", reason="PLAYER_LEARNING_STORE_UNAVAILABLE")

    def _fresh_idle_after(self, first, fresh):
        return (self._idle(fresh) and fresh.scope() == first.scope()
                and fresh.input_generation == first.input_generation
                and fresh.capture != first.capture and fresh.observed_at >= first.observed_at)

    def _respond_to_modal(self, first):
        if self.trait_response is None:
            return "NATIVE_MODAL_BINDING_REQUIRED"
        if (not self._idle(first) or type(first.playing) is not bool
                or not isinstance(first.modal_ref, str) or not first.modal_ref):
            return "YIELD_TO_PLAYER"
        fresh = self.adapter.frame()
        if (not self._fresh_idle_after(first, fresh) or fresh.modal_open is not True
                or fresh.modal_ref != first.modal_ref or fresh.playing is not first.playing):
            return "YIELD_TO_PLAYER"
        result = self.trait_response.respond(enabled=True, installed_scope={
            "game_build": fresh.game_build, "game_run": fresh.run,
            "input_generation": fresh.input_generation, "paused": not fresh.playing,
            "dialog_ref": fresh.modal_ref,
        })
        return result["state"]

    def reconcile_modal(self, dialog_ref, response, effect):
        if not self.registered or self.trait_response is None:
            return {"state": "NATIVE_MODAL_BINDING_REQUIRED"}
        return self.trait_response.reconcile(dialog_ref, response, effect)

    def _dispatch(self, identity, submit, *, scoped_attempts=None, attempted=None, attempt_key=None):
        if identity in self.attempts or attempt_key in self.activity_attempts:
            return "DUPLICATE_NATIVE_PROPOSAL"
        if len(self.attempts) >= MAX_ATTEMPTS_PER_RUN:
            return "NATIVE_SESSION_ATTEMPT_LIMIT"
        if scoped_attempts is None:
            self.unresolved = identity
        else:
            scoped_attempts[identity[0]] = attempted
        self.attempts.add(identity)
        if attempt_key is not None:
            self.activity_attempts.add(attempt_key)
        try:
            result = submit()
        except Exception:
            return "NATIVE_DISPATCH_RECONCILIATION"
        if result not in ("QUEUED", "NO_EFFECT"):
            return "NATIVE_DISPATCH_RECONCILIATION"
        if result == "NO_EFFECT":
            if scoped_attempts is None:
                self.unresolved = None
            else:
                del scoped_attempts[identity[0]]
        return result

    def _cycle_fairy_dust(self, first):
        scope = first.scope()
        spent = {key[2] for key in self.attempts
                 if len(key) == 3 and key[:2] == (scope, "FAIRY_DUST")}
        try:
            result = self.fairy_dust.plan_fairy_dust(first, self.adapter.read_fairy_dust(first),
                                                     attempted_opportunities=spent)
        except Exception:
            return "REOBSERVE_DUST_SCOPE"
        if result["state"] == "WAIT_FOR_HOME_RECHECK":
            self.dust_recheck = {**result, "scope": first.scope(), "capture": first.capture}
        if result["state"] != "DUST_PROPOSAL":
            return result["state"]
        fresh = self.adapter.frame()
        if (not self._fresh_idle_after(first, fresh)
                or fresh.playing is not True or fresh.modal_open is not False):
            return "YIELD_TO_PLAYER"
        try:
            current = self.fairy_dust.plan_fairy_dust(fresh, self.adapter.read_fairy_dust(fresh),
                                                      attempted_opportunities=spent)
        except Exception:
            return "REOBSERVE_DUST_SCOPE"
        if current != result:
            return "REOBSERVE_DUST_SCOPE"
        if not self._idle(fresh):
            return "REOBSERVE_DUST_SCOPE"
        proposal = current["proposal"]
        attempted = dict(current, proposal=dict(proposal), scope=scope,
                         admission_captures=(first.capture, fresh.capture), observed_at=fresh.observed_at)
        identity = (scope, "FAIRY_DUST", proposal["opportunity"])
        # The adapter must atomically verify the exact target, input generation,
        # queue and current EA interaction test before one native submission.
        return self._dispatch(identity, lambda: self.adapter.submit_fairy_dust(proposal, fresh),
                              scoped_attempts=self.dust_attempts, attempted=attempted)

    def _reconcile_fairy_dust(self, frame, attempted):
        try:
            outcome = self.adapter.read_fairy_dust_outcome(dict(attempted["proposal"]), frame)
        except Exception:
            return "NATIVE_DISPATCH_RECONCILIATION"
        result = self.fairy_dust.fairy_dust_outcome(frame, attempted, outcome)
        if result != "NATIVE_DISPATCH_RECONCILIATION":
            del self.dust_attempts[attempted["scope"]]
        return result

    def _read_fame(self, frame):
        scope = frame.scope()
        previous = self.fame_tracks.get(scope)
        if previous is None and len(self.fame_tracks) >= MAX_FAME_ACTORS:
            return None, None
        try:
            observation = self.adapter.read_fame(frame, previous["id"] if previous else None)
            track = self.fame.observe_drone(frame, observation, previous)
        except Exception:
            return None, previous
        if track is not None:
            self.fame_tracks[scope] = track
        return observation, track

    def _record_fame_sample(self, scope, sample):
        if sample:
            context, action, outcome = sample
            counts = self.fame_training.setdefault(scope, {}).setdefault((context, action), [0, 0, 0])
            counts[self.fame.OUTCOMES.index(outcome)] += 1

    def _reconcile_fame(self, frame, *, active_stream=False):
        scope = frame.scope()
        attempts = self.fame_streams if active_stream else self.fame_attempts
        attempted = attempts.get(scope)
        if attempted is None:
            return None
        try:
            outcome = self.adapter.read_fame_outcome(dict(attempted["proposal"]), frame)
            result, sample = self.fame.read_outcome(frame, attempted, outcome)
        except Exception:
            return "NATIVE_DISPATCH_RECONCILIATION"
        if result == "NATIVE_DISPATCH_RECONCILIATION":
            return result
        if result == "FAME_STREAM_OBSERVED":
            if active_stream:
                return "NATIVE_DISPATCH_RECONCILIATION"
            self.fame_streams[scope] = {**attempted, "stream_seen_capture": frame.capture}
        del attempts[scope]
        self._record_fame_sample(scope, sample)
        return result

    def _observe_active_fame_stream(self, frame, observation, track):
        result = self._reconcile_fame(frame, active_stream=True)
        if result != "NATIVE_DISPATCH_RECONCILIATION":
            return
        scope = frame.scope()
        active = self.fame_streams[scope]
        if (frame.capture != active["stream_seen_capture"]
                and self.fame.current_stream_stopped(
                    frame, observation, track, active["proposal"]["target"])):
            # The original submission and start were confirmed. A current stop
            # can clear the stream slot while the training outcome stays unknown.
            del self.fame_streams[scope]

    def _cycle_fame(self, first, observation, track, *, recovery_only=False):
        scope = first.scope()
        spent = {key[2] for key in self.attempts if len(key) == 3 and key[:2] == (scope, "FAME")}
        history = self.fame_training.get(scope, {})
        state, proposal = self.fame.plan_fame(first, observation, track, spent, history)
        if proposal and proposal["action"] == "BEGIN_STREAM" and scope in self.fame_streams:
            state, proposal = "WAIT_FOR_STREAM_TRAINING_OUTCOME", None
        if recovery_only and not self.fame.protects_drone(first, observation, track, proposal):
            return None
        self.fame_receipt = {"scope": scope, "state": state, "track": track}
        if proposal is None:
            return state
        fresh = self.adapter.frame()
        if (not self._fresh_idle_after(first, fresh)
                or fresh.playing is not True or fresh.modal_open is not False):
            return "YIELD_TO_PLAYER"
        current_observation, current_track = self._read_fame(fresh)
        _, current = self.fame.plan_fame(fresh, current_observation, current_track, spent, history)
        if current != proposal or not self._idle(fresh):
            return "REOBSERVE_NATIVE_FAME_SCOPE"
        if recovery_only and not self.fame.protects_drone(fresh, current_observation, current_track, current):
            return "REOBSERVE_NATIVE_FAME_SCOPE"
        identity = (scope, "FAME", proposal["opportunity"])
        attempted = {"proposal": dict(proposal), "captures": (first.capture, fresh.capture),
                     "observed_at": fresh.observed_at, "input_generation": fresh.input_generation}
        # The adapter owns the atomic EA check, including ownership, player input,
        # scene, route, perk eligibility and the exact native affordance.
        return self._dispatch(identity, lambda: self.adapter.submit_fame(dict(proposal), fresh),
                              scoped_attempts=self.fame_attempts, attempted=attempted)

    def _read_activity_chain(self, frame):
        mode = "PLAY" if frame.playing else "PLANNING"
        try:
            packet = self.adapter.read_activity_chain(frame)
            if packet is None:
                return "NO_ACTIVITY_GOAL", None, None
            snapshot = packet["snapshot"]
            save = packet["save_ref"]
            goal = packet["goal_ref"]
            if (packet["game_build"] != frame.game_build or packet["run"] != frame.run
                    or snapshot["sim_ref"] != frame.actor
                    or snapshot["household_ref"] != frame.household or snapshot["mode"] != mode
                    or save != frame.save_ref
                    or not all(isinstance(ref, str) and player_learning.TOKEN.fullmatch(ref)
                               for ref in (save, goal))):
                return "ACTIVITY_SCOPE_UNQUALIFIED", None, None
            plan = self.activity_chain.compile_activity_chain(
                snapshot, packet["steps"], packet.get("routes", ()), capture_ref=frame.capture,
            )
            if plan["gate"] != "EFFECT_ADMISSION_REQUIRED":
                return plan["gate"], plan, None

            head = plan["steps"][0]
            if head["kind"] == "TRAVEL":
                destination = plan["steps"][1]
                action = ("TRAVEL", destination["step_id"], head["method"], head["from"], head["to"])
                binding_key = action
            else:
                action = ("ACTIVITY", head["step_id"], head["domain"], head["activity_kind"],
                          snapshot["location"])
                binding_key = action[:2]
            binding = packet["proposals"].get(binding_key)
            if not isinstance(binding, Mapping) or binding.get("evidence_ref") != head["evidence_ref"]:
                return "ACTIVITY_ACTION_UNBOUND", plan, None
            proposal = binding.get("proposal_ref")
            if not isinstance(proposal, str) or not player_learning.TOKEN.fullmatch(proposal):
                return "ACTIVITY_ACTION_UNBOUND", plan, None
            return plan["gate"], plan, (save, goal, action, proposal)
        except Exception:
            # A missing or malformed native observation is never work to execute.
            return "ACTIVITY_EVIDENCE_UNQUALIFIED", None, None

    def _cycle_activity_chain(self, first):
        state, self.activity_plan, candidate = self._read_activity_chain(first)
        if state == "NO_ACTIVITY_GOAL":
            return None
        if candidate is None:
            return state
        fresh = self.adapter.frame()
        if (not self._fresh_idle_after(first, fresh)
                or fresh.playing is not True or fresh.modal_open is not False):
            return "YIELD_TO_PLAYER"
        planned, _, _ = self.adapter.analyze(fresh)
        if not isinstance(planned, Mapping) or planned:
            return "ACTIVITY_REOBSERVE_DOMAIN_PRIORITY"
        _, self.activity_plan, current = self._read_activity_chain(fresh)
        if current != candidate or not self._idle(fresh):
            return "ACTIVITY_REOBSERVE_FIRST_ACTION"
        save, goal, action, proposal = current
        identity = (fresh.scope(), proposal)
        self.activity_admission = (first.capture, fresh)
        result = self._dispatch(
            identity, lambda: self.adapter.submit(proposal, fresh),
            attempt_key=(fresh.scope(), save, goal, action[:2]),
        )
        if self.unresolved != identity:
            self.activity_admission = None
        return result

    def _can_reconcile_native(self, frame):
        if self.activity_admission is None:
            return True
        first_capture, dispatch = self.activity_admission
        # A new selected portrait may observe the original, identity-bound
        # outcome through the adapter's household queue reader.
        return (frame.scope()[:3] == dispatch.scope()[:3] and frame.save_ref == dispatch.save_ref
                and frame.observed_at >= dispatch.observed_at
                and frame.capture not in (first_capture, dispatch.capture))

    def cycle(self):
        """Analyze on any eligible turn. Submit at most one fresh, ranked proposal."""
        self.dust_recheck = None
        self.fame_receipt = None
        self.activity_plan = None
        if not self.registered:
            return "LISTENER_NOT_REGISTERED"
        first = self.adapter.frame()
        if not self._fresh_live(first):
            self.pending = None
            return "NATIVE_FRAME_UNQUALIFIED"
        if first.restock_has_control is not False:
            return "RESTOCK_CONTROL_HELD_OR_UNVERIFIED"
        if self.run is None:
            self.run = first.run
        elif first.run != self.run:
            self.pending = None
            return "NATIVE_SESSION_REBIND_REQUIRED"
        if self.portrait_pending is not None:
            return self._reconcile_portrait(first)
        readback = self.portrait_readback
        if readback is not None:
            if (type(first.input_generation) is not int or first.capture == readback.capture
                    or first.observed_at <= readback.observed_at
                    or first.input_generation < readback.input_generation
                    or (first.scope() != readback.scope()
                        and first.input_generation == readback.input_generation)):
                return "PORTRAIT_SELECTION_REOBSERVE"
            self.portrait_readback = None
        if (self.unresolved is not None and self._can_reconcile_native(first)
                and self.adapter.reconcile(self.unresolved, first) is True):
            self.unresolved = None
            self.activity_admission = None
        if first.modal_open is True:
            return self._respond_to_modal(first)
        if first.modal_open is not False:
            return "NATIVE_FRAME_UNQUALIFIED"
        fame_observation = fame_track = fame_result = None
        if self.fame is not None:
            fame_observation, fame_track = self._read_fame(first)
            if fame_track:
                self.fame_receipt = {"scope": first.scope(), "state": "DRONE_TRACKED",
                                     "track": fame_track}
            self._observe_active_fame_stream(first, fame_observation, fame_track)
            fame_result = self._reconcile_fame(first)
        planned, query, needs = self.adapter.analyze(first)
        dust_attempt = self.dust_attempts.get(first.scope())
        if dust_attempt is not None:
            dust_result = self._reconcile_fairy_dust(first, dust_attempt)
            if dust_result != "NATIVE_DISPATCH_RECONCILIATION" or not planned:
                return dust_result
        if self.unresolved is not None:
            return "NATIVE_DISPATCH_RECONCILIATION"
        if not self._idle(first):
            return "YIELD_TO_PLAYER"
        if (self.portraits is not None and isinstance(planned, Mapping) and not planned
                and type(first.playing) is bool and not self.dust_attempts and not self.fame_attempts):
            result = self._select_portrait(first)
            if result is not None:
                return result
        if first.playing is not True:
            if (first.playing is False and self.activity_chain is not None
                    and isinstance(planned, Mapping) and not planned):
                result = self._cycle_activity_chain(first)
                if result is not None:
                    return result
            return "YIELD_TO_PLAYER"
        if self.fame is not None and isinstance(planned, Mapping) and planned:
            if fame_result == "NATIVE_DISPATCH_RECONCILIATION":
                return fame_result
            if fame_result is None:
                protection = self._cycle_fame(first, fame_observation, fame_track, recovery_only=True)
                if protection is not None:
                    return protection
        if not isinstance(planned, Mapping) or not planned:
            dust_hold = "NO_DUST_GOAL"
            if self.fairy_dust is not None and isinstance(planned, Mapping):
                result = self._cycle_fairy_dust(first)
                dust_hold = result
                # A wait-for-charge or empty-home observation can coexist with
                # Fame. A possible Fairy dispatch still owns this callback.
                if result not in ("NO_DUST_GOAL", "WAIT_FOR_HOME_RECHECK", "REOBSERVE_HOME_OR_FIND_FAIRY",
                                  "DUST_GOAL_MET"):
                    return result
            if self.fame is not None and isinstance(planned, Mapping):
                if fame_result is not None:
                    return fame_result
                result = self._cycle_fame(first, fame_observation, fame_track)
                if result != "NO_FAME_GOAL":
                    return result
            if (self.activity_chain is not None and isinstance(planned, Mapping)
                    and not self.dust_attempts and not self.fame_attempts):
                result = self._cycle_activity_chain(first)
                if result is not None:
                    return result
            return dust_hold if dust_hold != "NO_DUST_GOAL" else "NO_NATIVE_PROPOSAL"
        hint = {}
        if isinstance(query, Mapping) and query.get("kind") == "query":
            hint = self.observe(first, query, needs)
        action = hint.get("suggested_action")
        if action not in planned:
            # Mapping order is the verified adapter's normal policy precedence.
            action = next(iter(planned))
        proposal = planned[action]
        if not isinstance(proposal, str) or not player_learning.TOKEN.fullmatch(proposal):
            return "NATIVE_PROPOSAL_ID_UNVERIFIED"

        fresh = self.adapter.frame()
        if (not self._fresh_idle_after(first, fresh)
                or fresh.playing is not True or fresh.modal_open is not False):
            return "YIELD_TO_PLAYER"
        identity = (fresh.scope(), proposal)
        # The verified adapter's atomic submit revalidates the queue, candidate
        # availability, input generation and exact target under the current frame.
        return self._dispatch(identity, lambda: self.adapter.submit(proposal, fresh))


def start_installed(adapter, *, exact_build: str, owned_dir: Path,
                    learning_opt_in: bool, clock=monotonic, trait_binding=None):
    """Called at native import by an independently inspected EA entry module."""
    if learning_opt_in is not True:
        return None
    root = Path(owned_dir)
    manifest = root / MANIFEST
    if (root.name != "BetterInstincts" or root.parent.name != "Mods"
            or any(parent.is_symlink() for parent in (root, *root.parents))
            or manifest.is_symlink() or not manifest.is_file() or manifest.stat().st_size > 8192):
        raise ValueError("NATIVE_OWNERSHIP_REQUIRED")
    installed = json.loads(manifest.read_text(encoding="utf-8"))
    if (not isinstance(installed, Mapping)
            or not isinstance(exact_build, str) or not judgment_learning.PATCH_RE.fullmatch(exact_build)
            or installed.get("schema") != "betterinstincts.native-ecology-ownership/v1"
            or installed.get("game_build") != exact_build
            or installed.get("installed_player_runtime") is not True
            or getattr(adapter, "game_build", None) != exact_build):
        raise ValueError("NATIVE_EXACT_BUILD_BINDING_REQUIRED")
    trait_response = None
    trait_installed = installed.get("installed_trait_responder") is True
    if trait_installed or trait_binding is not None:
        if (not trait_installed or not isinstance(trait_binding, Mapping)
                or trait_binding.get("game_build") != exact_build
                or not all(callable(getattr(adapter, name, None))
                           for name in ("read_offer", "submit_if_current", "register_modal_readback"))):
            raise ValueError("NATIVE_TRAIT_BINDING_OR_PORTS_REQUIRED")
        from betterinstincts.preference_response_port import PreferenceResponsePort

        trait_response = PreferenceResponsePort(adapter, trait_binding=trait_binding)
    fairy_dust = None
    if installed.get("installed_fairy_dust") is True:
        if not all(callable(getattr(adapter, name, None)) for name in (
                "read_fairy_dust", "submit_fairy_dust", "read_fairy_dust_outcome")):
            raise ValueError("NATIVE_FAIRY_DUST_PORTS_REQUIRED")
        from betterinstincts import fairy_dust
    fame = None
    if installed.get("installed_fame") is True:
        if not all(callable(getattr(adapter, name, None)) for name in (
                "read_fame", "submit_fame", "read_fame_outcome")):
            raise ValueError("NATIVE_FAME_PORTS_REQUIRED")
        from betterinstincts import fame
    portraits = None
    if installed.get("installed_portrait_handoff") is True:
        from betterinstincts import portrait_handoff as portraits

        if not all(callable(getattr(adapter, name, None)) for name in portraits.PORTS):
            raise ValueError("NATIVE_PORTRAIT_HANDOFF_PORTS_REQUIRED")
    activity_chain = None
    if installed.get("installed_activity_chain") is True:
        if not callable(getattr(adapter, "read_activity_chain", None)):
            raise ValueError("NATIVE_ACTIVITY_CHAIN_PORT_REQUIRED")
        from betterinstincts import activity_chain
    runtime = InstalledPlayerRuntime(adapter, build=exact_build, owned_dir=root, clock=clock,
                                     trait_response=trait_response, fairy_dust=fairy_dust, fame=fame,
                                     portraits=portraits, activity_chain=activity_chain)
    if not all(callable(getattr(adapter, name, None))
               for name in ("register", "frame", "analyze", "submit", "reconcile")):
        raise ValueError("NATIVE_CALLBACK_PORTS_REQUIRED")
    if trait_response is not None and adapter.register_modal_readback(runtime.reconcile_modal) is not True:
        raise ValueError("NATIVE_MODAL_READBACK_REGISTRATION_UNVERIFIED")
    if adapter.register(observe=runtime.observe, cycle=runtime.cycle) is not True:
        raise ValueError("NATIVE_CALLBACK_REGISTRATION_UNVERIFIED")
    runtime.registered = True
    return runtime
