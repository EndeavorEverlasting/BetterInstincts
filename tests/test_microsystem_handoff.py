import unittest
from dataclasses import replace

from betterinstincts.installed_player_runtime import Frame
from betterinstincts.microsystem_handoff import (
    NEEDS_MORE_EVIDENCE, NO_DATA, PRIORITY, SCHEMA, QueueDecision, decide,
)
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


def evidence(frame, actor, domain, work, *, minimum=1, seconds=0, samples=None):
    if samples is None:
        samples = [(frame.capture, 100)]
    return dict(game_build=frame.game_build, run=frame.run, save=frame.save_ref,
                household=frame.household, actor=actor, domain=domain, work=work,
                min_samples=minimum, min_active_seconds=seconds,
                samples=[dict(capture=capture, active_second=time) for capture, time in samples])


def packet(frame, members, **overrides):
    def qualify(actor, domain, assessment):
        return {"evidence": evidence(frame, actor, domain, assessment["work"]), **assessment}

    def bind(actor, domain, lane):
        if lane["state"] == "CLEAR":
            return {"review": qualify(actor, domain, {"work": "review-" + domain}), **lane}
        if lane["state"] == "READY":
            return {**lane, "options": [qualify(actor, domain, choice) for choice in lane["options"]]}
        return lane

    qualified = {}
    for actor, sim in members.items():
        qualified[actor] = {**sim, "lanes": {
            domain: bind(actor, domain, lane) for domain, lane in sim["lanes"].items()
        }}
    return dict({"schema": SCHEMA, "game_build": frame.game_build, "run": frame.run,
                 "save": frame.save_ref, "household": frame.household, "capture": frame.capture,
                 "selected": frame.actor, "roster": [SIM, OTHER], "members": qualified,
                 "safe_to_leave": True}, **overrides)


def queued(work, domain, *, slot=None, origin="BETTERINSTINCTS", state="PENDING"):
    return dict(work=work, domain=domain, slot=slot or ("slot-" + work), origin=origin,
                state=state)


class MicrosystemHandoffTests(unittest.TestCase):
    def test_evidence_holds_only_its_portrait_until_the_task_window_is_mature(self):
        for samples, held in (([], NO_DATA),
                              ([(FRAME.capture, 100)], NEEDS_MORE_EVIDENCE),
                              ([("capture:older", 90), (FRAME.capture, 100)], None)):
            with self.subTest(samples=samples):
                report = {"work": "career-report"} if held else option("career-report")
                report["evidence"] = evidence(
                    FRAME, SIM, "CAREER", report["work"], minimum=2, seconds=10, samples=samples,
                )
                local = member(FRAME, CAREER=lane(FRAME, report), SKILLS=lane(FRAME, option("piano")))
                remote = member(FRAME, SKILLS=lane(FRAME, option("guitar")))
                _, winner, dispositions = decide(FRAME, packet(FRAME, {SIM: local, OTHER: remote}))
                if held:
                    self.assertEqual(dispositions[SIM], held)
                    self.assertEqual((winner.actor, winner.work), (OTHER, "guitar"))
                else:
                    self.assertEqual((winner.actor, winner.work), (SIM, "career-report"))

    def test_sample_count_and_active_time_are_independent_requirements(self):
        for samples in (
            [("capture:older", 50), (FRAME.capture, 100)],
            [("capture:older", 97), ("capture:middle", 99), (FRAME.capture, 100)],
        ):
            with self.subTest(samples=samples):
                report = option("career-report")
                report["evidence"] = evidence(
                    FRAME, SIM, "CAREER", report["work"], minimum=3, seconds=10, samples=samples,
                )
                sim = member(FRAME, CAREER=lane(FRAME, report), SKILLS=lane(FRAME, option("piano")))
                _, winner, dispositions = decide(FRAME, packet(FRAME, {SIM: sim}))
                self.assertIsNone(winner)
                self.assertEqual(dispositions[SIM], NEEDS_MORE_EVIDENCE)

    def test_clearance_requires_evidence_to_release_the_next_tier(self):
        for samples, held in (([], NO_DATA), ([(FRAME.capture, 100)], NEEDS_MORE_EVIDENCE),
                              ([("capture:older", 90), (FRAME.capture, 100)], None)):
            with self.subTest(samples=samples):
                needs = lane(FRAME)
                needs["review"] = {"work": "review-needs", "evidence": evidence(
                    FRAME, SIM, "NEEDS", "review-needs", minimum=2, seconds=10, samples=samples,
                )}
                sim = member(FRAME, NEEDS=needs, CAREER=lane(FRAME, option("career-report")))
                _, winner, dispositions = decide(FRAME, packet(FRAME, {SIM: sim}))
                if held:
                    self.assertIsNone(winner)
                    self.assertEqual(dispositions[SIM], held)
                else:
                    self.assertEqual(winner.work, "career-report")

    def test_replay_scope_clock_and_legacy_packets_are_rejected(self):
        base_evidence = evidence(FRAME, SIM, "NEEDS", "food")
        incorrect = (
            None,
            {**base_evidence, "game_build": "other-build"},
            {**base_evidence, "run": "other-run"},
            {**base_evidence, "save": "other-save"},
            {**base_evidence, "household": "other-household"},
            {**base_evidence, "actor": OTHER},
            {**base_evidence, "domain": "SKILLS"},
            {**base_evidence, "work": "other-task"},
            {**base_evidence, "min_samples": True},
            {**base_evidence, "min_active_seconds": float("nan")},
            {**base_evidence, "min_active_seconds": 10},
            {**base_evidence, "samples": [{"capture": "capture:old", "active_second": 100}]},
            {**base_evidence, "samples": [
                {"capture": FRAME.capture, "active_second": 80}, *base_evidence["samples"],
            ]},
            {**base_evidence, "samples": [
                {"capture": "capture:old", "active_second": 100}, *base_evidence["samples"],
            ]},
            {**base_evidence, "samples": [
                {"capture": "capture:old", "active_second": 110}, *base_evidence["samples"],
            ]},
            {**base_evidence, "samples": base_evidence["samples"] * 17},
        )
        for witness in incorrect:
            with self.subTest(witness=witness):
                food = {**option("food"), "evidence": witness}
                sim = member(FRAME, NEEDS=lane(FRAME, food))
                _, winner, dispositions = decide(FRAME, packet(FRAME, {SIM: sim}))
                self.assertIsNone(winner)
                self.assertEqual(dispositions[SIM], "LANE_REOBSERVE")
        old = packet(FRAME, {SIM: member(FRAME)}, schema="betterinstincts.microsystem-handoff/v1")
        self.assertEqual(decide(FRAME, old), ("MICROSYSTEM_SCOPE_UNQUALIFIED", None, {}))

    def test_qualified_option_can_win_before_another_option_in_its_tier(self):
        waiting = {**option("urgent", urgency=1, minutes=1), "evidence": evidence(
            FRAME, SIM, "NEEDS", "urgent", minimum=2, samples=[(FRAME.capture, 100)],
        )}
        sim = member(FRAME, NEEDS=lane(FRAME, waiting, option("food")))
        _, winner, _ = decide(FRAME, packet(FRAME, {SIM: sim}))
        self.assertEqual(winner.work, "food")

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
