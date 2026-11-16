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

    def scope(self):
        return self.game_build, self.run, self.household, self.actor


class InstalledPlayerRuntime:
    """One permitted game session. No thread, timer, Git, socket or desktop input."""

    def __init__(self, adapter, *, build: str, owned_dir: Path, clock=monotonic):
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
        return (self._fresh_live(frame) and frame.playing is True
                and frame.activity_trusted is True
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
                queue_busy=not self._idle(frame),
            )
            return result
        except (TypeError, KeyError, AttributeError, player_learning.PlayerLearningError,
                judgment_learning.JudgmentLearningError):
            self.pending = None
            return player_learning.receipt("ABSTAIN", reason="NATIVE_EVIDENCE_INVALID")
        except (OSError, sqlite3.Error):
            return player_learning.receipt("ABSTAIN", reason="PLAYER_LEARNING_STORE_UNAVAILABLE")

    def cycle(self):
        """Analyze on any eligible turn. Submit at most one fresh, ranked proposal."""
        if not self.registered:
            return "LISTENER_NOT_REGISTERED"
        first = self.adapter.frame()
        if not self._fresh_live(first):
            self.pending = None
            return "NATIVE_FRAME_UNQUALIFIED"
        if self.run is None:
            self.run = first.run
        elif first.run != self.run:
            self.pending = None
            return "NATIVE_SESSION_REBIND_REQUIRED"
        if self.unresolved is not None and self.adapter.reconcile(self.unresolved, first) is True:
            self.unresolved = None
        planned, query, needs = self.adapter.analyze(first)
        if self.unresolved is not None:
            return "NATIVE_DISPATCH_RECONCILIATION"
        if not self._idle(first):
            return "YIELD_TO_PLAYER"
        if not isinstance(planned, Mapping) or not planned:
            return "NO_NATIVE_PROPOSAL"
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
        if (not self._idle(fresh) or fresh.scope() != first.scope()
                or fresh.input_generation != first.input_generation
                or fresh.capture == first.capture or fresh.observed_at < first.observed_at):
            return "YIELD_TO_PLAYER"
        identity = (fresh.scope(), proposal)
        if identity in self.attempts:
            return "DUPLICATE_NATIVE_PROPOSAL"
        if len(self.attempts) >= MAX_ATTEMPTS_PER_RUN:
            return "NATIVE_SESSION_ATTEMPT_LIMIT"

        # The verified adapter's atomic submit revalidates the queue, candidate
        # availability, input generation and exact target under the current frame.
        self.unresolved = identity
        self.attempts.add(identity)
        try:
            result = self.adapter.submit(proposal, fresh)
        except Exception:
            return "NATIVE_DISPATCH_RECONCILIATION"
        if result not in ("QUEUED", "NO_EFFECT"):
            return "NATIVE_DISPATCH_RECONCILIATION"
        if result == "NO_EFFECT":
            self.unresolved = None
        return result


def start_installed(adapter, *, exact_build: str, owned_dir: Path,
                    learning_opt_in: bool, clock=monotonic):
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
    runtime = InstalledPlayerRuntime(adapter, build=exact_build, owned_dir=root, clock=clock)
    if not all(callable(getattr(adapter, name, None))
               for name in ("register", "frame", "analyze", "submit", "reconcile")):
        raise ValueError("NATIVE_CALLBACK_PORTS_REQUIRED")
    if adapter.register(observe=runtime.observe, cycle=runtime.cycle) is not True:
        raise ValueError("NATIVE_CALLBACK_REGISTRATION_UNVERIFIED")
    runtime.registered = True
    return runtime
