"""P82 measured offline Servo/Bills microsystem falsifiers and host integration."""
import copy
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from betterinstincts.household_upkeep import (
    HouseholdUpkeepError, evaluate_household_upkeep, load_contract,
)
from betterinstincts.host_stack import HostStackError, evaluate_turn
from betterinstincts.host_listener import HostListenerError, activate, tick
from betterinstincts.player_presence import PresenceProbe

CAP = "capture:upkeep"
NEEDS = dict(hunger=.92, bladder=.92, energy=.92, hygiene=.92, fun=.92, social=.92)


def servo(ref="servo:a", durability=.8, charge=.8, fun=.8, social=.8, **kwargs):
    row = {"sim_ref":ref, "needs_verified":True, "broken":False,
           "water_exposure":"NONE",
           "needs":{"durability":durability,"charge":charge,"fun":fun,"social":social}}
    row.update(kwargs)
    return row


def actor(ref="sim:helper", kind="HUMAN", **kwargs):
    row = {"sim_ref":ref, "kind":kind, "queue_verified":True, "available":True,
           "player_reserved":False, "urgent_needs":False, "multitasking":False,
           "queue":[]}
    row.update(kwargs)
    return row


def action(action_id, actor_ref="sim:helper", target_ref="servo:a", **kwargs):
    row = {"action_id":action_id,"actor_ref":actor_ref,"target_ref":target_ref,
           "capture_ref":CAP,"available":True}
    row.update(kwargs)
    return row


def bill(**kwargs):
    row = {"bill_ref":"bill:1","state":"UNPAID","bill_verified":True,
           "amount":450,"household_funds":2000,"due_in_sim_hours":12,
           "attempt":"NONE"}
    row.update(kwargs)
    return row


def obs(**kwargs):
    row = {"schema":"betterinstincts.household-upkeep/v1",
           "capture_ref":CAP,"observed_at_unix":time.time(),
           "household_verified":True,"queue_verified":True,
           "scene_verified":True,"servos":[servo(durability=.1)],
           "actors":[actor()],"observed_actions":[action("TUNE_UP_SERVO")],
           "bill":None,"bill_payment_authorized":False}
    row.update(kwargs)
    return row


def evaluate(o, **kwargs):
    return evaluate_household_upkeep(o, capture_ref=CAP, **kwargs)


class UpkeepMicrosystemTests(unittest.TestCase):
    def test_policy_is_separate_from_needs_and_budget_owners(self):
        cfg=load_contract()
        self.assertEqual(cfg["queue_owner"],"betterinstincts/queue_capacity.py")
        self.assertEqual(cfg["budget_owner"],"betterinstincts/budget_eval.py")
        self.assertEqual(cfg["bounds"]["max_new_queue_actions"],1)

    def test_low_durability_tuneup_uses_other_human(self):
        o=obs()
        original=copy.deepcopy(o)
        result=evaluate(o)
        self.assertEqual(result["gate"],"UPKEEP_ACTION_READY")
        self.assertEqual(result["next_actions"][0]["action_id"],"TUNE_UP_SERVO")
        self.assertEqual(result["next_actions"][0]["actor_ref"],"sim:helper")
        self.assertEqual(result["next_actions"][0]["target_ref"],"servo:a")
        self.assertFalse(result["dispatch_authorized"])
        self.assertEqual(result["servo_health"][0]["health"],"CRITICAL")
        self.assertEqual(result["next_monitor_seconds"],30)
        self.assertEqual(o,original)

    def test_servo_four_motives_without_fake_human_needs(self):
        o=obs(servos=[servo(durability=.8,charge=.8,fun=.1,social=.1)],
              observed_actions=[
                  action("SOCIALIZE_SERVO"),
                  action("SERVO_FUN_ACTIVITY","servo:a","servo:a")
              ],actors=[actor(),actor("servo:a","SERVO")])
        out=evaluate(o)
        self.assertEqual(out["next_actions"][0]["action_id"],"SOCIALIZE_SERVO")
        self.assertEqual(out["servo_health"][0]["health"],"WATCH")
        self.assertEqual(set(out["servo_health"][0]["needs"]),
                         {"durability","charge","fun","social"})

    def test_unknown_servo_has_no_fabricated_motives(self):
        o=obs(servos=[servo(needs=None, needs_verified=False)])
        out=evaluate(o)
        self.assertEqual(out["servo_health"][0]["health"],"UNVERIFIED")
        self.assertEqual(out["gate"],"UPKEEP_MONITOR")
        self.assertFalse(out["next_actions"])
        with self.assertRaisesRegex(HouseholdUpkeepError,"MUST_BE_NULL"):
            evaluate(obs(servos=[servo(needs_verified=False)]))

    def test_critical_charge_is_self_recharge_not_helper_tuneup(self):
        out=evaluate(obs(servos=[servo(durability=.8,charge=.05)],
             actors=[actor(),actor("servo:a","SERVO")],
             observed_actions=[action("RECHARGE_SERVO","servo:a","servo:a")]))
        self.assertEqual(out["next_actions"][0]["action_id"],"RECHARGE_SERVO")
        self.assertEqual(out["next_actions"][0]["actor_ref"],"servo:a")

    def test_broken_servo_requires_observed_repair_not_tuneup(self):
        out=evaluate(obs(servos=[servo(broken=True,durability=0)],
            observed_actions=[action("REPAIR_SERVO")]))
        self.assertEqual(out["next_actions"][0]["action_id"],"REPAIR_SERVO")
        self.assertEqual(out["servo_health"][0]["health"],"BROKEN")

    def test_water_risk_blocks_unverified_servo_action(self):
        out=evaluate(obs(servos=[servo(water_exposure="WET",durability=.1)]))
        self.assertEqual(out["servo_health"][0]["water_exposure"],"WET")
        self.assertEqual(out["gate"],"UPKEEP_MONITOR")

    def test_monitor_multiple_servos_one_queue_action(self):
        out=evaluate(obs(servos=[servo("servo:b",durability=.15),
                                 servo("servo:a",durability=.15)],
             observed_actions=[action("TUNE_UP_SERVO",target_ref="servo:a"),
                               action("TUNE_UP_SERVO",target_ref="servo:b")]))
        self.assertEqual(len(out["servo_health"]),2)
        self.assertEqual(out["candidate_count"],2)
        self.assertEqual(len(out["next_actions"]),1)
        self.assertEqual(out["next_actions"][0]["target_ref"],"servo:a")

    def test_player_queued_or_dispatched_tuneup_is_not_duplicated(self):
        for attempt in ("QUEUED","DISPATCHED"):
            with self.subTest(attempt=attempt):
                o=obs(servos=[servo(durability=.1,maintenance_attempt=attempt)])
                out=evaluate(o)
                self.assertFalse(out["next_actions"])
        queued=actor(queue=[{"action_id":"TUNE_UP_SERVO","target_ref":"servo:a",
                             "origin":"HOST"}])
        out=evaluate(obs(actors=[queued]))
        self.assertFalse(out["next_actions"])

    def test_human_helpers_have_queue_and_needs_protection(self):
        for changes in ({"player_reserved":True},{"urgent_needs":True},
                        {"available":False},{"multitasking":None},
                        {"queue":[{"action_id":"A","origin":"HOST"} for _ in range(6)]}):
            with self.subTest(changes=changes):
                out=evaluate(obs(actors=[actor(**changes)]))
                self.assertFalse(out["next_actions"])

    def test_player_unknown_or_unverified_queue_origin_holds(self):
        for origin in ("PLAYER","UNKNOWN"):
            with self.subTest(origin=origin):
                a=actor(queue=[{"action_id":"CHAT", "origin":origin}])
                out=evaluate(obs(actors=[a]))
                self.assertEqual(out["gate"],"UPKEEP_QUEUE_ORIGIN_HOLD")
        self.assertEqual(evaluate(obs(actors=[actor(queue_verified=False)]))["gate"],
                         "UPKEEP_REOBSERVE")

    def test_bill_due_affordable_queues_once_with_exact_actor(self):
        o=obs(servos=[],bill=bill(),bill_payment_authorized=True,
              observed_actions=[action("PAY_BILLS",target_ref="bill:1")])
        out=evaluate(o)
        self.assertEqual(out["next_actions"][0]["action_id"],"PAY_BILLS")
        self.assertEqual(out["next_actions"][0]["observed_bill_amount"],450)
        self.assertEqual(out["bill_health"]["state"],"UNPAID")
        self.assertFalse(out["dispatch_authorized"])

    def test_bill_payment_requires_explicit_enrollment(self):
        o=obs(servos=[],bill=bill(),bill_payment_authorized=False,
              observed_actions=[action("PAY_BILLS",target_ref="bill:1")])
        self.assertEqual(evaluate(o)["gate"],"UPKEEP_MONITOR")

    def test_bill_paid_not_due_unknown_and_unaffordable_never_pay(self):
        variants=[
            bill(state="PAID"),
            bill(state="NOT_DUE"),
            bill(state="UNKNOWN"),
            bill(household_funds=449),
            bill(due_in_sim_hours=80),
            bill(amount=None),
            bill(household_funds=None),
        ]
        for entry in variants:
            with self.subTest(entry=entry):
                out=evaluate(obs(servos=[],bill=entry,bill_payment_authorized=True,
                      observed_actions=[action("PAY_BILLS",target_ref="bill:1")]))
                self.assertEqual(out["next_actions"],[])
        self.assertEqual(evaluate(obs(servos=[],bill=bill(state="PAID"),
             bill_payment_authorized=True))["bill_health"]["state"],"PAID_UNVERIFIED")
        self.assertEqual(evaluate(obs(servos=[],bill=bill(
            state="PAID",payment_proof_ref="receipt:1",outcome_capture_ref="capture:proof"),
            bill_payment_authorized=True))["bill_health"]["state"],"VERIFIED_PAID")

    def test_bill_queued_dispatched_or_current_queue_deduped(self):
        for attempt in ("QUEUED","DISPATCHED"):
            with self.subTest(attempt=attempt):
                out=evaluate(obs(servos=[],bill=bill(attempt=attempt),
                    bill_payment_authorized=True,
                    observed_actions=[action("PAY_BILLS",target_ref="bill:1")]))
                self.assertFalse(out["next_actions"])
        out=evaluate(obs(servos=[],bill=bill(),bill_payment_authorized=True,
            actors=[actor(queue=[{"action_id":"PAY_BILLS","target_ref":"bill:1","origin":"HOST"}])],
            observed_actions=[action("PAY_BILLS",target_ref="bill:1")]))
        self.assertFalse(out["next_actions"])

    def test_urgent_bill_and_critical_servo_rank_before_ordinary_tasks(self):
        o=obs(servos=[servo(durability=.25)],bill=bill(due_in_sim_hours=-30),
              bill_payment_authorized=True,
              observed_actions=[action("TUNE_UP_SERVO"),
                                action("PAY_BILLS",target_ref="bill:1")])
        out=evaluate(o)
        self.assertEqual(out["next_actions"][0]["action_id"],"PAY_BILLS")
        self.assertEqual(out["next_actions"][0]["priority"],0)

    def test_stale_capture_wrong_affordance_and_mode_no_action(self):
        for changes in ({"observed_at_unix":time.time()-190},
                        {"capture_ref":"capture:past"},{"scene_verified":False},
                        {"household_verified":False},{"queue_verified":False}):
            self.assertEqual(evaluate(obs(**changes))["gate"],"UPKEEP_REOBSERVE")
        self.assertEqual(evaluate(obs(observed_actions=[
            action("TUNE_UP_SERVO",capture_ref="capture:past")]))["next_actions"],[])
        for flag in ("player_directed","already_busy","build_or_buy_mode",
                     "human_survival_hold"):
            with self.subTest(flag=flag):
                self.assertEqual(evaluate(obs(),**{flag:True})["next_actions"],[])

    def test_bounds_and_malformed_motives_fail_closed(self):
        bad=[{"servos":[servo()]*17},
             {"servos":[servo("servo:a"),servo("servo:a")]},
             {"servos":[servo(needs={"hunger":1,"bladder":1})]},
             {"servos":[servo(durability=1.1)]},
             {"actors":[actor(),actor()]},
             {"bill":bill(amount=-10)},
             {"observed_actions":[action("TUNE_UP_SERVO")]*65}]
        for x in bad:
            with self.subTest(change=list(x)),self.assertRaises(HouseholdUpkeepError):
                evaluate(obs(**x))


class HostUpkeepIntegrationTests(unittest.TestCase):
    def test_host_stack_attaches_upkeep_without_displacing_legacy(self):
        o=obs()
        kwargs=dict(capture_ref=CAP, location_kind="home",queue=[],
                    viewport={"state":"VIEWPORT_OK"})
        out=evaluate_turn(NEEDS,household_upkeep=o,**kwargs)
        self.assertEqual(out["next_gate"],"UPKEEP_ACTION_READY")
        self.assertEqual(out["household_upkeep"]["next_actions"][0]["action_id"],
                         "TUNE_UP_SERVO")
        self.assertFalse(out["household_upkeep"]["dispatch_authorized"])
        legacy=evaluate_turn(NEEDS,**kwargs)
        self.assertIsNone(legacy["household_upkeep"])
        self.assertNotEqual(legacy["next_gate"],"UPKEEP_ACTION_READY")

    def test_viewport_player_and_urgent_human_needs_outrank_upkeep(self):
        kwargs=dict(capture_ref=CAP,location_kind="home",queue=[],
                    viewport={"state":"VIEWPORT_OK"},household_upkeep=obs())
        self.assertEqual(evaluate_turn(NEEDS,player_directed=True,**kwargs)["next_gate"],
                         "RESPECT_PLAYER_OR_BUSY_STATE")
        result=evaluate_turn(NEEDS,**{**kwargs,"viewport":{"state":"UNKNOWN"}})
        self.assertNotEqual(result["next_gate"],"UPKEEP_ACTION_READY")
        result=evaluate_turn({**NEEDS,"energy":.01},**kwargs)
        self.assertNotEqual(result["next_gate"],"UPKEEP_ACTION_READY")
        self.assertEqual(result["household_upkeep"]["gate"],"UPKEEP_HUMAN_NEEDS_FIRST")

    def test_upkeep_and_gardening_reports_coexist(self):
        garden={"capture_ref":CAP,"observed_at_unix":time.time(),
                "scene_verified":True,"queue_verified":True,
                "responsibilities_checked":True,"minutes_until_obligation":120,
                "observed_actions":[{"action_id":"WATER","capture_ref":CAP,
                     "target_ref":"plant:a","available":True,"label":"Water"}]}
        out=evaluate_turn(NEEDS,household_upkeep=obs(),
              gardening=garden,queue=[],capture_ref=CAP,
              location_kind="home",viewport={"state":"VIEWPORT_OK"})
        self.assertIsNotNone(out["gardening"])
        self.assertIsNotNone(out["household_upkeep"])
        self.assertIn(out["next_gate"],{"UPKEEP_ACTION_READY","GARDEN_ACTION_READY"})

    def test_listener_transports_upkeep_and_rejects_unbounded_payload(self):
        with tempfile.TemporaryDirectory() as root,patch(
            "betterinstincts.host_listener.ROOT",Path(root).resolve()
        ),patch("betterinstincts.host_listener.OUTPUT",
                Path(root).resolve()/"dist/host-listener"):
            activate("upkeep-test")
            raw={"schema":"betterinstincts.host-listener.observation/v1",
                 "needs":NEEDS,"queue":[],"location_kind":"home",
                 "capture_ref":CAP,"viewport":{"state":"VIEWPORT_OK"},
                 "household_upkeep":obs()}
            out=tick("upkeep-test",raw,presence_probe=PresenceProbe(
                False,False,last_input_age_ms=20000,probe_ok=True))
            self.assertEqual(out["host_stack"]["household_upkeep"]["gate"],
                             "UPKEEP_ACTION_READY")
            self.assertFalse(out["execute_clicks"])
            with self.assertRaisesRegex(HostListenerError,
                                        "OBSERVATION_HOUSEHOLD_UPKEEP_INVALID"):
                tick("upkeep-test",{**raw,"household_upkeep":{"x":"z"*9000}})


if __name__ == "__main__":
    unittest.main()
