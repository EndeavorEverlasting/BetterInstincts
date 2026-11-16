"""Fame lifecycle, level-up and outcome regressions with supplied native frames."""
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest
from unittest.mock import Mock

from betterinstincts.fame import NATIVE, PACK, PERK_PATHS, observe_drone, plan_fame, read_outcome
from betterinstincts.installed_player_runtime import Frame, MANIFEST, start_installed

BUILD = "1.121.361.1020"
FIRST = Frame(BUILD, "game-run", "house-one", "sim:actor", True, True, True, False,
              False, True, 3, 10, 5, "capture:one")
DRONE = "object:drone"


def offer(frame, action, target=DRONE, subject=None, **extra):
    return dict(capture=frame.capture, action=action, target=target, subject=subject,
                enabled=True, opportunity="opp-" + (subject or action), **extra)


def observation(frame, location="INVENTORY", mode="STOPPED", action=None, **drone_fields):
    item = dict(source=NATIVE, capture=frame.capture, id=DRONE, zone="zone-one",
                owner_household=frame.household, assigned_actor=frame.actor,
                model="GOTTA_STREAM_EM_ALL", lot="home-lot", location=location,
                mode=mode, battery="FULL", offers={action: offer(frame, action)} if action else {})
    return dict(source=NATIVE, scope=frame.scope(), capture=frame.capture, pack=PACK,
                goal="CREATOR", fame_enabled=True, actor_present=True, needs_safe=True,
                allow_perk_spending=True, actor_zone="zone-one", home_lot="home-lot",
                training_context="home-routine", departure_imminent=False,
                home_route=dict(capture=frame.capture, reachable=True, origin_zone="zone-one",
                                home_lot="home-lot", route_id="route-one"),
                drone={**item, **drone_fields})


def plan(frame, obs, track=None, *, history=None):
    track = observe_drone(frame, obs, track)
    return plan_fame(frame, obs, track, set(), history or {})


class FamePolicyTests(unittest.TestCase):
    def test_public_drone_follows_home_and_is_stowed_one_effect_at_a_time(self):
        track = observe_drone(FIRST, observation(FIRST, "PUBLIC_GROUND", "STREAMING"))
        steps = [
            ("PUBLIC_GROUND", "STOPPED", None, {"battery": "EMPTY", "stop_cause": "BATTERY_DEPLETED"}),
            ("PUBLIC_GROUND", "STOPPED", "BEGIN_RECOVERY_STREAM", {}),
            ("PUBLIC_GROUND", "STREAMING", "RETURN_DRONE_HOME", {"follows_actor": True}),
            ("HOME_LOT", "STREAMING", "END_STREAM", {}),
            ("HOME_LOT", "STOPPED", "STOW_DRONE", {}),
            ("INVENTORY", "STOPPED", None, {}),
        ]
        for index, (location, mode, action, fields) in enumerate(steps):
            frame = replace(FIRST, capture=f"capture:replay-{index}")
            obs = observation(frame, location, mode, action, **fields)
            track = observe_drone(frame, obs, track)
            _, pick = plan(frame, obs, track)
            self.assertEqual(pick and pick["action"], action)
            if index == 0:
                self.assertEqual(track["last_stop"], dict(cause="BATTERY_DEPLETED",
                                                         location=location, capture=frame.capture))
        self.assertFalse(track["recovering"])
        self.assertEqual(track["id"], DRONE)

    def test_snapshot_vision_and_looks_like_another_drone_are_discovery_only(self):
        before = observation(FIRST, "PUBLIC_GROUND", "STREAMING")
        track = observe_drone(FIRST, before)
        frame = replace(FIRST, capture="capture:later")
        obs = observation(frame, "PUBLIC_GROUND", "STOPPED", "BEGIN_RECOVERY_STREAM",
                          battery="FULL", favorite=True, grounded=True)
        for invalid in (dict(obs, source="EA_FILE"), dict(obs, source="VISION"),
                        dict(obs, drone=dict(obs["drone"], source="VISION")),
                        dict(obs, drone=dict(obs["drone"], assigned_actor="sim:someone")),
                        dict(obs, drone=dict(obs["drone"], id="object:other")),
                        dict(obs, drone=dict(obs["drone"], location="UNLOADED"))):
            self.assertIs(observe_drone(frame, invalid, track), track)
            self.assertIsNone(plan(frame, invalid, track)[1])

    def test_no_fame_goal_preserves_existing_drone_activity(self):
        for mode, action in (("STREAMING", "END_STREAM"), ("STOPPED", "STOW_DRONE")):
            obs = observation(FIRST, "HOME_LOT", mode, action)
            obs.update(goal=None, departure_imminent=True)
            self.assertEqual(plan(FIRST, obs), ("NO_FAME_GOAL", None))

    def test_conflicting_same_capture_cannot_reuse_a_current_track(self):
        obs = observation(FIRST, "HOME_LOT", "STOPPED", "STOW_DRONE")
        track = observe_drone(FIRST, obs)
        self.assertEqual(plan_fame(FIRST, obs, track, set(), {})[1]["action"], "STOW_DRONE")
        for changes in ({"id": "object:other"}, {"assigned_actor": "sim:other"},
                        {"mode": "STREAMING"}, {"location": "PUBLIC_GROUND"},
                        {"battery": "EMPTY"}, {"lot": "other-lot"}):
            with self.subTest(changes=changes):
                current = {**obs, "drone": {**obs["drone"], **changes}}
                self.assertEqual(plan_fame(FIRST, current, track, set(), {}),
                                 ("LOCATE_LAST_KNOWN_DRONE", None))

    def test_departure_preserves_work_and_makes_home_stow_eligible(self):
        obs = observation(FIRST, "HOME_LOT", "STREAMING", "END_STREAM")
        self.assertIsNone(plan(FIRST, obs)[1])
        self.assertEqual(plan(FIRST, dict(obs, departure_imminent=True))[1]["action"], "END_STREAM")
        public = observation(FIRST, "PUBLIC_GROUND", "STOPPED", "BEGIN_RECOVERY_STREAM")
        for override in (dict(departure_imminent=True), dict(actor_present=False),
                         dict(fame_enabled=False), dict(home_route=None), dict(actor_zone="zone-two"),
                         dict(needs_safe=False), dict(goal=None)):
            self.assertIsNone(plan(FIRST, {**public, **override})[1])
        self.assertEqual(plan(FIRST, dict(public, home_route=None))[0], "PUBLIC_DRONE_ROUTE_UNVERIFIED")

    def test_career_and_creator_perk_paths_reserve_points_and_respect_opt_out(self):
        self.assertEqual(sum(map(len, PERK_PATHS.values())), 21)
        for goal, name in (("CAREER", "NOTICEABLE"), ("CREATOR", "CORPORATE_PARTNERSHIP"),
                           ("SOCIAL", "NETWORKING"), ("GOOD_REPUTATION", "GIVING_BACK"),
                           ("BAD_REPUTATION", "WHOS_BAD")):
            pick = offer(FIRST, "BUY_FAME_PERK", FIRST.actor, name, cost=1, native_prerequisites_met=True)
            panel = dict(capture=FIRST.capture, rank=3, points=1, owned=[], offers={name: pick},
                         verified_reputation_path=goal)
            obs = dict(observation(FIRST), goal=goal, perk_panel=panel)
            self.assertEqual(plan(FIRST, obs)[1]["subject"], name)
            for change in (dict(rank=0), dict(points=0), dict(offers={name: dict(pick, native_prerequisites_met=False)}),
                           dict(offers={name: dict(pick, target="sim:other")})):
                self.assertIsNone(plan(FIRST, dict(obs, perk_panel={**panel, **change}))[1])
            self.assertIsNone(plan(FIRST, dict(obs, fame_enabled=False))[1])
            self.assertIsNone(plan(FIRST, dict(obs, allow_perk_spending=False))[1])
        missing_earlier = offer(FIRST, "BUY_FAME_PERK", FIRST.actor, "EASY_STREET", cost=1,
                                native_prerequisites_met=True)
        career = dict(observation(FIRST), goal="CAREER", perk_panel=dict(
            capture=FIRST.capture, rank=5, points=1, owned=["NOTICEABLE"], offers={"EASY_STREET": missing_earlier}))
        self.assertIsNone(plan(FIRST, career)[1])

    def test_lithium_priority_and_creator_only_hd_camera(self):
        options = {name: offer(FIRST, "UPGRADE_DRONE", subject=name) for name in
                   ("LITHIUM_BATTERY", "RELIABLE_COMPONENTS", "HD_CAMERA")}
        obs = dict(observation(FIRST, offers=options, upgrades=[]), allow_drone_upgrades=True,
                   handiness=7, common_parts=6, electronic_parts=3)
        self.assertEqual(plan(FIRST, obs)[1]["subject"], "LITHIUM_BATTERY")
        self.assertIsNone(plan(FIRST, dict(obs, common_parts=1))[1])
        obs["drone"]["upgrades"] = ["LITHIUM_BATTERY", "RELIABLE_COMPONENTS"]
        self.assertEqual(plan(FIRST, obs)[1]["subject"], "HD_CAMERA")
        self.assertIsNone(plan(FIRST, dict(obs, goal="CAREER"))[1])

    def test_categorical_evidence_can_displace_default_and_penalize_downside(self):
        stream = offer(FIRST, "BEGIN_STREAM", active_minutes=10, fits_current_schedule=True)
        media = offer(FIRST, "PUBLISH_MEDIA", FIRST.actor, active_minutes=10, fits_current_schedule=True)
        obs = dict(observation(FIRST, offers={"BEGIN_STREAM": stream}), stream_route_safe=True,
                   training_offers={"PUBLISH_MEDIA": media})
        self.assertEqual(plan(FIRST, obs)[1]["action"], "PUBLISH_MEDIA")
        counts = {("home-routine", "PUBLISH_MEDIA"): (0, 0, 3)}
        self.assertEqual(plan(FIRST, obs, history=counts)[1]["action"], "BEGIN_STREAM")
        self.assertIsNone(plan(FIRST, dict(obs, training_offers={}, stream_route_safe=False))[1])
        counts = {("another-context", "PUBLISH_MEDIA"): (0, 0, 3)}
        self.assertEqual(plan(FIRST, obs, history=counts)[1]["action"], "PUBLISH_MEDIA")

    def test_effect_requires_fresh_correlation_and_exact_destination(self):
        pick = plan(FIRST, observation(FIRST, "HOME_LOT", "STOPPED", "STOW_DRONE"))[1]
        attempted = dict(proposal=pick, captures=(FIRST.capture, "capture:second"), observed_at=10)
        fresh = replace(FIRST, capture="capture:third")
        outcome = dict(source=NATIVE, scope=fresh.scope(), capture=fresh.capture, proposal=pick,
                       acknowledged=True, completed=True,
                       effect=dict(target=DRONE, location="INVENTORY", inventory_actor=FIRST.actor))
        self.assertEqual(read_outcome(fresh, attempted, outcome)[0], "FAME_EFFECT_OBSERVED")
        for altered in (dict(capture=FIRST.capture), dict(acknowledged=False),
                        dict(source="VISION"), dict(effect={**outcome["effect"], "inventory_actor": "sim:wrong"})):
            self.assertEqual(read_outcome(fresh, attempted, {**outcome, **altered})[0],
                             "NATIVE_DISPATCH_RECONCILIATION")


class InstalledFameTests(unittest.TestCase):
    def setUp(self):
        temp = TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name) / "Mods" / "BetterInstincts"
        self.root.mkdir(parents=True)
        (self.root / MANIFEST).write_text(json.dumps({
            "schema": "betterinstincts.native-ecology-ownership/v1", "game_build": BUILD,
            "installed_player_runtime": True, "installed_fame": True,
        }))
        self.adapter = Mock(game_build=BUILD)
        self.adapter.register.return_value = True
        self.adapter.analyze.return_value = ({}, {}, {})
        self.adapter.submit_fame.return_value = "QUEUED"
        self.adapter.read_fame_outcome.return_value = None

    def start(self):
        return start_installed(self.adapter, exact_build=BUILD, owned_dir=self.root,
                               learning_opt_in=True, clock=lambda: 10)

    def deploy(self, runtime, initial, read_fame):
        fresh = replace(initial, capture="capture:second")
        self.adapter.frame.side_effect = [initial, fresh]
        self.adapter.read_fame.side_effect = read_fame
        return runtime.cycle()

    def test_requires_exact_game_adapter_ports(self):
        self.adapter.submit_fame = None
        with self.assertRaisesRegex(ValueError, "NATIVE_FAME_PORTS_REQUIRED"):
            self.start()

    def test_passive_tracking_continues_during_human_input_without_effect(self):
        runtime = self.start()
        user = replace(FIRST, player_active=True)
        self.adapter.frame.return_value = user
        self.adapter.read_fame.side_effect = lambda frame, *args: observation(
            frame, "HOME_LOT", "STOPPED", "STOW_DRONE")
        self.assertEqual(runtime.cycle(), "YIELD_TO_PLAYER")
        self.assertEqual(runtime.fame_receipt["track"]["id"], DRONE)
        self.adapter.submit_fame.assert_not_called()

    def test_second_probe_disarms_changed_target_or_player(self):
        for changed in (replace(FIRST, capture="capture:second", player_active=True),
                        replace(FIRST, capture="capture:second")):
            runtime = self.start()
            self.adapter.frame.side_effect = [FIRST, changed]
            self.adapter.read_fame.side_effect = [
                observation(FIRST, "HOME_LOT", "STOPPED", "STOW_DRONE"),
                observation(changed, "HOME_LOT", "STOPPED", "STOW_DRONE", id="object:different"),
            ]
            self.assertIn(runtime.cycle(), ("YIELD_TO_PLAYER", "REOBSERVE_NATIVE_FAME_SCOPE"))
        self.adapter.submit_fame.assert_not_called()

    def test_lost_ack_and_other_sim_cannot_replay_or_close_attempt(self):
        runtime = self.start()
        self.adapter.submit_fame.side_effect = OSError("ack lost")
        self.assertEqual(self.deploy(runtime, FIRST, lambda frame, *args: observation(
            frame, "HOME_LOT", "STOPPED", "STOW_DRONE")), "NATIVE_DISPATCH_RECONCILIATION")
        proposal = self.adapter.submit_fame.call_args.args[0]
        other = replace(FIRST, actor="sim:other", capture="capture:other")
        fresh = replace(FIRST, capture="capture:third")
        self.adapter.frame.side_effect = [other, fresh, fresh]
        self.adapter.read_fame.side_effect = None
        self.adapter.read_fame.return_value = None
        self.assertEqual(runtime.cycle(), "NO_NATIVE_PROPOSAL")
        self.adapter.read_fame_outcome.return_value = dict(
            source=NATIVE, scope=fresh.scope(), capture=fresh.capture, acknowledged=True,
            proposal=proposal, completed=True,
            effect=dict(target=DRONE, inventory_actor=other.actor, location="INVENTORY"))
        self.assertEqual(runtime.cycle(), "NATIVE_DISPATCH_RECONCILIATION")
        self.adapter.read_fame_outcome.return_value["effect"]["inventory_actor"] = FIRST.actor
        self.assertEqual(runtime.cycle(), "FAME_EFFECT_OBSERVED")
        self.adapter.submit_fame.assert_called_once()

    def test_routine_stow_yields_to_normal_native_action(self):
        runtime = self.start()
        self.adapter.analyze.return_value = ({"need": "needs-action"}, {}, {})
        self.adapter.submit.return_value = "QUEUED"
        self.assertEqual(self.deploy(runtime, FIRST, lambda frame, *args: observation(
            frame, "HOME_LOT", "STOPPED", "STOW_DRONE")), "QUEUED")
        self.adapter.submit.assert_called_once()
        self.adapter.submit_fame.assert_not_called()

    def test_missing_stream_outcome_releases_only_after_new_same_drone_stop(self):
        runtime = self.start()

        def stream_offer(frame, *args):
            offer_id = ("old-stream" if frame.capture in (FIRST.capture, "capture:second")
                        else "new-stream")
            options = {"BEGIN_STREAM": {**offer(frame, "BEGIN_STREAM", active_minutes=5,
                                               fits_current_schedule=True), "opportunity": offer_id}}
            return dict(observation(frame, offers=options), stream_route_safe=True)

        self.assertEqual(self.deploy(runtime, FIRST, stream_offer), "QUEUED")
        proposal = self.adapter.submit_fame.call_args.args[0]
        started = replace(FIRST, capture="capture:streaming")
        conflict = replace(FIRST, capture="capture:conflict")
        stopped = replace(FIRST, capture="capture:stopped")
        fresh = replace(FIRST, capture="capture:stopped-fresh")
        self.adapter.frame.side_effect = [started, conflict, stopped, fresh]
        self.adapter.read_fame.side_effect = [
            observation(started, "HOME_LOT", "STREAMING"),
            observation(conflict, id="object:different"),
            stream_offer(stopped), stream_offer(fresh),
        ]
        self.adapter.read_fame_outcome.side_effect = [
            dict(source=NATIVE, scope=started.scope(), capture=started.capture,
                 acknowledged=True, completed=True, proposal=proposal,
                 effect=dict(target=DRONE, mode="STREAMING")),
            None, None,
        ]
        self.assertEqual(runtime.cycle(), "FAME_STREAM_OBSERVED")
        self.assertEqual(runtime.cycle(), "LOCATE_LAST_KNOWN_DRONE")
        self.assertEqual(runtime.cycle(), "QUEUED")
        self.assertEqual(self.adapter.submit_fame.call_count, 2)
        self.assertEqual(self.adapter.submit_fame.call_args.args[0]["opportunity"], "new-stream")
        self.assertEqual(runtime.fame_training, {})

    def test_active_stream_releases_action_gate_and_later_trains_once(self):
        runtime = self.start()

        def start_stream(frame, *args):
            options = {"BEGIN_STREAM": offer(frame, "BEGIN_STREAM", active_minutes=5,
                                             fits_current_schedule=True)}
            return dict(observation(frame, offers=options), stream_route_safe=True)

        self.assertEqual(self.deploy(runtime, FIRST, start_stream), "QUEUED")
        stream = self.adapter.submit_fame.call_args.args[0]
        started = replace(FIRST, capture="capture:started")
        end_first = replace(FIRST, capture="capture:end-first")
        end_fresh = replace(FIRST, capture="capture:end-fresh")
        done = replace(FIRST, capture="capture:finished")
        self.adapter.frame.side_effect = [started, end_first, end_fresh, done, done]
        self.adapter.read_fame.side_effect = lambda frame, *args: dict(
            observation(frame, "HOME_LOT", "STREAMING", "END_STREAM", battery="LOW"),
            departure_imminent=True)

        def outcome(proposal, frame):
            if proposal != stream:
                return None
            effect = dict(target=DRONE, mode="STREAMING")
            if frame is done:
                effect.update(training_finished=True, training_outcome="GAIN")
            return dict(source=NATIVE, scope=frame.scope(), capture=frame.capture, proposal=proposal,
                        acknowledged=True, completed=True, effect=effect, player_interrupted=False)

        self.adapter.read_fame_outcome.side_effect = outcome
        self.assertEqual(runtime.cycle(), "FAME_STREAM_OBSERVED")
        self.assertEqual(runtime.cycle(), "QUEUED")
        self.assertEqual(self.adapter.submit_fame.call_args.args[0]["action"], "END_STREAM")
        runtime.cycle()
        runtime.cycle()
        self.assertEqual(runtime.fame_training[FIRST.scope()][("home-routine", "BEGIN_STREAM")], [1, 0, 0])
