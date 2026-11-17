import unittest
from dataclasses import replace

from betterinstincts.installed_player_runtime import Frame
from betterinstincts.microsystem_handoff import PRIORITY, SCHEMA, QueueDecision, decide
from betterinstincts.portrait_handoff import Selection

SIM, OTHER = "sim:first", "sim:second"
FRAME = Frame("1.121.361.1020", "game-run", "house-one", SIM, True, True, True,
              False, False, True, 1, 10, 5, "capture:first", save_ref="lab-save")


def option(work, *, urgency=0.5, benefit=0.8, minutes=10):
    return dict(work=work, proposal="do-" + work, urgency=urgency, benefit=benefit,
                minutes=minutes)


def lane(frame, *options):
    return dict(capture=frame.capture, state="READY" if options else "CLEAR", options=options)


def member(frame, **lanes):
    return dict(capture=frame.capture, available=True, player_queue=False,
                queue_verified=True, queue_ref="queue-one", slots_free=3, queue=[],
                lanes={domain: lanes.get(domain, lane(frame)) for domain in PRIORITY})


def packet(frame, members, **overrides):
    return dict({"schema": SCHEMA, "game_build": frame.game_build, "run": frame.run,
                 "save": frame.save_ref, "household": frame.household, "capture": frame.capture,
                 "selected": frame.actor, "roster": [SIM, OTHER], "members": members,
                 "safe_to_leave": True}, **overrides)


def queued(work, domain, *, slot=None, origin="BETTERINSTINCTS", state="PENDING"):
    return dict(work=work, domain=domain, slot=slot or ("slot-" + work), origin=origin,
                state=state)


class MicrosystemHandoffTests(unittest.TestCase):
    def test_each_queued_goal_releases_to_next_tier_despite_smaller_scores(self):
        frame = FRAME
        actions = dict(zip(PRIORITY, ("food", "report", "bill", "piano")))
        sim = member(frame, **{
            domain: lane(frame, option(work, urgency=(index + 1) / 4))
            for index, (domain, work) in enumerate(actions.items())
        })
        for domain, work in actions.items():
            with self.subTest(domain=domain):
                _, result, _ = decide(frame, packet(frame, {SIM: sim}))
                self.assertEqual((result.domain, result.work), (domain, work))
                sim["queue"].append(queued(work, domain))
        self.assertEqual(decide(frame, packet(frame, {SIM: sim}))[0],
                         "MICROSYSTEM_NO_ADMISSIBLE_WORK")

    def test_higher_priority_other_portrait_and_rate_tiebreak_within_domain(self):
        frame = FRAME
        local = member(frame, SKILLS=lane(frame, option("piano", urgency=1, minutes=1)))
        remote = member(frame, CAREER=lane(
            frame, option("report-slow", urgency=1, minutes=15),
            option("report-fast", minutes=5),
        ))
        _, result, _ = decide(frame, packet(frame, {SIM: local, OTHER: remote}))
        self.assertIsInstance(result.selection, Selection)
        self.assertEqual((result.selection.target, result.work), (OTHER, "report-fast"))
        _, alternative, _ = decide(frame, packet(frame, {SIM: local, OTHER: remote}),
                                   attempted={result.selection.identity(frame)})
        self.assertEqual(alternative.work, "report-slow")
        chosen = replace(frame, actor=OTHER)
        remote = member(chosen, CAREER=lane(chosen, option("report-fast")))
        self.assertIsInstance(decide(chosen, packet(chosen, {OTHER: remote}))[1], QueueDecision)

    def test_incomplete_failed_or_full_portrait_cannot_starve_independent_actor(self):
        frame = FRAME
        waiting = member(frame, NEEDS=dict(capture=frame.capture, state="WAITING"),
                         SKILLS=lane(frame, option("piano")))
        busy = {**waiting, "slots_free": 0}
        failure = {**waiting, "lanes": {**waiting["lanes"], "NEEDS": {
            "capture": frame.capture, "state": "FAILED",
        }}}
        stale = {**waiting, "lanes": {**waiting["lanes"], "NEEDS": {
            "capture": "capture:old", "state": "CLEAR",
        }}}
        for local, status in ((waiting, "LANE_WAITING"), (busy, "QUEUE_FULL"),
                              (failure, "LANE_WAITING"), (stale, "LANE_REOBSERVE")):
            with self.subTest(status=status):
                remote = member(frame, CONTINGENCIES=lane(frame, option("pay-bill")))
                _, result, dispositions = decide(frame, packet(frame, {SIM: local, OTHER: remote}))
                self.assertEqual(dispositions[SIM], status)
                self.assertEqual((result.selection.target, result.work), (OTHER, "pay-bill"))
                _, unavailable, _ = decide(frame, packet(frame, {SIM: local, OTHER: remote},
                                                         safe_to_leave=False))
                self.assertIsNone(unavailable)

    def test_preserve_running_native_and_player_actions(self):
        frame = FRAME
        sim = member(frame, NEEDS=lane(frame, option("food")))
        sim["queue"] = [
            queued("work", "CAREER", state="RUNNING"),
            queued("native", None, origin="SIM_AUTONOMY"),
            queued("bill", "CONTINGENCIES"),
            queued("piano", "SKILLS"),
        ]
        _, winner, _ = decide(frame, packet(frame, {SIM: sim}))
        self.assertEqual(winner.before_slot, "slot-bill")
        sim["queue"][3]["origin"] = "PLAYER"
        _, blocked, why = decide(frame, packet(frame, {SIM: sim}))
        self.assertIsNone(blocked)
        self.assertEqual(why[SIM], "QUEUE_UNQUALIFIED")

    def test_bad_score_duplicate_work_and_cross_save_packet_fail_closed(self):
        frame = FRAME
        for options in ((option("food", urgency=float("nan")),),
                        (option("food"), option("food", minutes=15)),
                        (option("food", minutes=10 ** 500),)):
            sim = member(frame, NEEDS=lane(frame, *options),
                         SKILLS=lane(frame, option("piano")))
            self.assertIsNone(decide(frame, packet(frame, {SIM: sim}))[1])
        self.assertEqual(decide(frame, packet(frame, {}, save="other-save"))[0],
                         "MICROSYSTEM_SCOPE_UNQUALIFIED")
