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


def utilibot(ref="bot:gardener", kind="GARDENER_BOT", durability=.8, charge=.8, **kwargs):
    row = {"bot_ref": ref, "kind": kind, "needs_verified": True,
           "broken": False, "water_exposure": "NONE",
           "needs": {"durability": durability, "charge": charge},
           "maintenance_attempt": "NONE", "charge_attempt": "NONE"}
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
        self.assertEqual(result["next_actions"][0]["helper_kind"],"HUMAN")
        self.assertFalse(result["dispatch_authorized"])
        self.assertEqual(result["servo_health"][0]["health"],"CRITICAL")
        self.assertEqual(result["next_monitor_seconds"],30)
        self.assertEqual(o,original)

    def test_servo_peer_helper_with_verified_robotics(self):
        helper=actor("servo:helper","SERVO",
                     skills={"robotics":{"level":10,"verified":True}})
        out=evaluate(obs(
            servos=[servo("servo:a",durability=.1),servo("servo:helper")],
            actors=[helper],
            observed_actions=[action("TUNE_UP_SERVO","servo:helper","servo:a")]))
        self.assertEqual(out["gate"],"UPKEEP_ACTION_READY")
        self.assertEqual(out["next_actions"][0]["actor_ref"],"servo:helper")
        self.assertEqual(out["next_actions"][0]["helper_kind"],"SERVO_PEER")
        self.assertEqual(out["next_actions"][0]["helper_robotics_level"],10.0)

    def test_verified_servo_peer_preferred_when_human_and_servo_both_available(self):
        human=actor("sim:helper","HUMAN")
        servo_helper=actor("servo:helper","SERVO",
                           skills={"robotics":{"level":10,"verified":True}})
        out=evaluate(obs(
            servos=[servo("servo:a",durability=.1),servo("servo:helper")],
            actors=[servo_helper, human],
            observed_actions=[
                action("TUNE_UP_SERVO","servo:helper","servo:a"),
                action("TUNE_UP_SERVO","sim:helper","servo:a"),
            ]))
        self.assertEqual(out["next_actions"][0]["actor_ref"],"servo:helper")
        self.assertEqual(out["next_actions"][0]["helper_kind"],"SERVO_PEER")

    def test_servo_without_robotics_yields_skill_gap(self):
        helper=actor("servo:helper","SERVO")
        out=evaluate(obs(
            servos=[servo("servo:a",durability=.1),servo("servo:helper")],
            actors=[helper],
            observed_actions=[action("TUNE_UP_SERVO","servo:helper","servo:a")]))
        self.assertEqual(out["gate"],"UPKEEP_HELPER_SKILL_GAP")
        self.assertEqual(out["skill_force_hint"]["bundle"],"servo_core")
        self.assertIn("robotics", out["skill_force_hint"]["skills"])
        self.assertFalse(out["next_actions"])

    def test_servo_cannot_self_tune_on_peer_path(self):
        self_helper=actor("servo:a","SERVO",
                          skills={"robotics":{"level":10,"verified":True}})
        out=evaluate(obs(
            actors=[self_helper],
            observed_actions=[action("TUNE_UP_SERVO","servo:a","servo:a")]))
        self.assertIn(out["gate"],
                      {"UPKEEP_HELPER_SKILL_GAP","UPKEEP_NO_SAFE_ACTOR_OR_AFFORDANCE",
                       "UPKEEP_HELPER_NEEDS_UNVERIFIED_OR_LOW"})
        self.assertFalse(out["next_actions"])

    def test_peer_social_is_allowed_only_if_observed_and_bills_remain_human_only(self):
        servo_helper=actor("servo:helper","SERVO",
                           skills={"robotics":{"level":10,"verified":True}})
        out=evaluate(obs(
            servos=[servo("servo:a",durability=.8,social=.1),servo("servo:helper")],
            actors=[servo_helper],
            observed_actions=[action("SOCIALIZE_SERVO","servo:helper","servo:a")]))
        self.assertEqual(out["next_actions"][0]["action_id"], "SOCIALIZE_SERVO")
        self.assertEqual(out["next_actions"][0]["actor_ref"], "servo:helper")
        out_bill=evaluate(obs(
            servos=[], bill=bill(), bill_payment_authorized=True,
            actors=[servo_helper],
            observed_actions=[action("PAY_BILLS","servo:helper","bill:1")]))
        self.assertFalse(out_bill["next_actions"])

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



class CooperativeRobotCareTests(unittest.TestCase):
    """P82: bot maintenance is targeted, bounded and protected by helper motives."""

    def test_gardener_bot_broken_repaired_by_verified_servo(self):
        helper=actor("servo:helper","SERVO",skills={"robotics":{"level":7,"verified":True}})
        o=obs(servos=[servo("servo:helper")],actors=[helper],
              utilibots=[utilibot(broken=True,durability=0)],
              observed_actions=[action("REPAIR_UTILIBOT","servo:helper","bot:gardener")])
        out=evaluate(o)
        self.assertEqual(out["gate"],"UPKEEP_ACTION_READY")
        self.assertEqual(out["next_actions"][0]["action_id"],"REPAIR_UTILIBOT")
        self.assertEqual(out["next_actions"][0]["target_kind"],"GARDENER_BOT")
        self.assertEqual(out["next_actions"][0]["helper_kind"],"SERVO_PEER")
        self.assertFalse(out["dispatch_authorized"])

    def test_gardener_bot_watch_tune_up_and_charge_are_distinct(self):
        helper=actor("sim:helper")
        o=obs(servos=[],utilibots=[utilibot(durability=.3,charge=.9)],
              actors=[helper],
              observed_actions=[action("TUNE_UP_UTILIBOT",target_ref="bot:gardener")])
        out=evaluate(o)
        self.assertEqual(out["next_actions"][0]["action_id"],"TUNE_UP_UTILIBOT")
        self.assertEqual(out["utilibot_health"][0]["health"],"WATCH")
        o["utilibots"][0]["needs"]={"durability":.9,"charge":.2}
        o["observed_actions"]=[action("RECHARGE_UTILIBOT",target_ref="bot:gardener")]
        self.assertEqual(evaluate(o)["next_actions"][0]["action_id"],"RECHARGE_UTILIBOT")

    def test_observed_fixomatic_module_can_repair_bot_without_verified_skill(self):
        fixer=actor("servo:fixer","SERVO",
                    modules={"fix_o_matic":{"enabled":True,"verified":True}})
        out=evaluate(obs(servos=[servo("servo:fixer")],actors=[fixer],
                         utilibots=[utilibot(broken=True,durability=0)],
                         observed_actions=[action("REPAIR_UTILIBOT","servo:fixer","bot:gardener")]))
        self.assertEqual(out["next_actions"][0]["helper_qualification"],"FIX_O_MATIC")
        broken=actor("servo:fixer","SERVO",
                     modules={"fix_o_matic":{"enabled":True,"verified":False}})
        denied=evaluate(obs(servos=[servo("servo:fixer")],actors=[broken],
                            utilibots=[utilibot(broken=True,durability=0)],
                            observed_actions=[
                                action("REPAIR_UTILIBOT","servo:fixer","bot:gardener")]))
        self.assertEqual(denied["gate"], "UPKEEP_HELPER_SKILL_GAP")
        self.assertFalse(denied["next_actions"])

    def test_fixomatic_can_tune_up_peer_servo_only_when_observed_and_verified(self):
        peer=actor("servo:helper","SERVO",
                   modules={"fix_o_matic":{"verified":True,"enabled":True}})
        out=evaluate(obs(servos=[servo("servo:a",durability=.3),
                                 servo("servo:helper")],
                         actors=[peer],
                         observed_actions=[action("TUNE_UP_SERVO","servo:helper","servo:a")]))
        self.assertEqual(out["next_actions"][0]["action_id"],"TUNE_UP_SERVO")
        self.assertEqual(out["next_actions"][0]["helper_qualification"],"FIX_O_MATIC")
        peer["modules"]["fix_o_matic"]["enabled"]=False
        denied=evaluate(obs(servos=[servo("servo:a",durability=.3),
                                    servo("servo:helper")],actors=[peer],
                            observed_actions=[action("TUNE_UP_SERVO","servo:helper","servo:a")]))
        self.assertFalse(denied["next_actions"])

    def test_servo_helper_reserve_must_be_verified_before_cooperation(self):
        helper=actor("servo:helper","SERVO",skills={"robotics":{"level":10,"verified":True}})
        for servos in ([servo("servo:a",durability=.1)],
                       [servo("servo:a",durability=.1),servo("servo:helper",charge=.25)],
                       [servo("servo:a",durability=.1),servo("servo:helper",durability=.2)],
                       [servo("servo:a",durability=.1),servo("servo:helper",water_exposure="WET")]):
            with self.subTest(c=[v["sim_ref"] for v in servos]):
                out=evaluate(obs(servos=servos,actors=[helper],
                                 observed_actions=[action("TUNE_UP_SERVO","servo:helper","servo:a")]))
                self.assertFalse(out["next_actions"])

    def test_low_charge_servo_chooses_its_own_recharge_before_helping(self):
        helper=actor("servo:helper","SERVO",skills={"robotics":{"level":10,"verified":True}})
        out=evaluate(obs(
            servos=[servo("servo:a",durability=.1),
                    servo("servo:helper",charge=.2)],
            actors=[helper], observed_actions=[
                action("TUNE_UP_SERVO","servo:helper","servo:a"),
                action("RECHARGE_SERVO","servo:helper","servo:helper")]))
        self.assertEqual(out["next_actions"][0]["action_id"],"RECHARGE_SERVO")
        self.assertEqual(out["next_actions"][0]["target_ref"],"servo:helper")

    def test_human_fallback_when_servo_helper_depleted(self):
        helper=actor("servo:helper","SERVO",skills={"robotics":{"level":10,"verified":True}})
        human=actor("sim:human","HUMAN")
        out=evaluate(obs(
            servos=[servo("servo:a",durability=.1),
                    servo("servo:helper",charge=.2)],
            actors=[helper,human], observed_actions=[
                action("TUNE_UP_SERVO","servo:helper","servo:a"),
                action("TUNE_UP_SERVO","sim:human","servo:a")]))
        self.assertEqual(out["next_actions"][0]["actor_ref"],"sim:human")

    def test_verified_self_tune_is_fallback_not_peer_path(self):
        self_actor=actor("servo:a","SERVO")
        base=obs(servos=[servo("servo:a",durability=.4,self_tune_verified=True)],
                 actors=[self_actor],observed_actions=[
                     action("SERVO_SELF_TUNE_UP","servo:a","servo:a")])
        self.assertEqual(evaluate(base)["next_actions"][0]["action_id"],"SERVO_SELF_TUNE_UP")
        base["servos"][0]["self_tune_verified"]=False
        self.assertFalse(evaluate(base)["next_actions"])
        base["servos"][0]["self_tune_verified"]=True
        base["servos"][0]["needs"]["charge"] = .2
        self.assertFalse(evaluate(base)["next_actions"])

    def test_bot_pending_attempt_cannot_repeat(self):
        for state in ("QUEUED","DISPATCHED"):
            for key,aid in (("maintenance_attempt","REPAIR_UTILIBOT"),
                            ("charge_attempt","RECHARGE_UTILIBOT")):
                bot=utilibot(broken=aid=="REPAIR_UTILIBOT",durability=0 if aid=="REPAIR_UTILIBOT" else .8,
                             charge=.1 if aid=="RECHARGE_UTILIBOT" else .8,
                             **{key:state})
                out=evaluate(obs(servos=[],utilibots=[bot],
                                 observed_actions=[action(aid,target_ref="bot:gardener")]))
                self.assertFalse(out["next_actions"])

    def test_water_exposed_bot_never_autorepaired(self):
        out=evaluate(obs(servos=[],utilibots=[
            utilibot(broken=True,durability=0,water_exposure="WET")],
            observed_actions=[action("REPAIR_UTILIBOT",target_ref="bot:gardener")]))
        self.assertEqual(out["utilibot_health"][0]["water_exposure"],"WET")
        self.assertFalse(out["next_actions"])

    def test_wrong_or_stale_bot_affordance_never_matches(self):
        o=obs(servos=[],utilibots=[utilibot(broken=True,durability=0)],
              observed_actions=[action("REPAIR_UTILIBOT",
                                       target_ref="bot:wrong")])
        self.assertFalse(evaluate(o)["next_actions"])
        o["observed_actions"]=[action("REPAIR_UTILIBOT",target_ref="bot:gardener",
                                      capture_ref="capture:old")]
        self.assertFalse(evaluate(o)["next_actions"])

    def test_all_four_utilibot_types_are_supported_and_no_fake_sims(self):
        kinds=("GARDENER_BOT","CLEANER_BOT","FIXER_BOT","PARTY_BOT")
        robots=[utilibot("bot:"+kind.lower(),kind=kind,durability=.8,charge=.8)
                for kind in kinds]
        out=evaluate(obs(servos=[],utilibots=robots,observed_actions=[]))
        self.assertEqual([x["kind"] for x in out["utilibot_health"]],list(kinds))
        self.assertEqual(out["servo_health"],[])
        self.assertEqual(out["gate"],"UPKEEP_MONITOR")

    def test_bot_validation_rejects_fake_values_and_id_overlap(self):
        invalid=(
            [utilibot(needs={"hunger":.8})],
            [utilibot(needs={"durability":float("nan"),"charge":.4})],
            [utilibot("servo:a")],
            [utilibot(needs_verified=False)],
            [utilibot(water_exposure="UNKNOWN")],
            [utilibot() for _ in range(17)],
        )
        for bots in invalid:
            with self.subTest(bots=len(bots)),self.assertRaises(HouseholdUpkeepError):
                evaluate(obs(utilibots=bots))

    def test_player_owns_screen_even_when_gardener_bot_broken(self):
        o=obs(servos=[],utilibots=[utilibot(broken=True,durability=0)],
              observed_actions=[action("REPAIR_UTILIBOT",target_ref="bot:gardener")])
        for flag in ("player_directed","already_busy","human_survival_hold","build_or_buy_mode"):
            with self.subTest(flag=flag):
                self.assertFalse(evaluate(o,**{flag:True})["next_actions"])
        o["actors"][0]["queue"]=[{"action_id":"OTHER",
                                  "origin":"PLAYER","target_ref":"other:task"}]
        self.assertFalse(evaluate(o)["next_actions"])

    def test_unverified_helper_module_does_not_prove_fixomatic(self):
        helper=actor("servo:helper","SERVO",
                     modules={"fix_o_matic":{"enabled":False,"verified":True}})
        out=evaluate(obs(servos=[servo("servo:helper")],actors=[helper],
                         utilibots=[utilibot(broken=True,durability=0)],
                         observed_actions=[action("REPAIR_UTILIBOT","servo:helper","bot:gardener")]))
        self.assertEqual(out["gate"],"UPKEEP_HELPER_SKILL_GAP")
        self.assertFalse(out["next_actions"])

    def test_no_bot_action_from_unverified_motives(self):
        out=evaluate(obs(servos=[],utilibots=[
            utilibot(needs_verified=False,needs=None,broken=False)]))
        self.assertEqual(out["utilibot_health"][0]["health"],"UNVERIFIED")
        self.assertFalse(out["next_actions"])



class ServoFireLaundryPolicyTests(unittest.TestCase):
    """P62 regression: 2026-11-09 low-Durability Servo + laundry/dryer lint fires."""

    def policy(self, servos, laundry=None, **kwargs):
        extra = {} if laundry is None else {"laundry": laundry}
        out = evaluate_household_upkeep(
            obs(servos=servos, **extra), capture_ref=CAP, **kwargs)
        return out["laundry_policy"]

    def test_critical_durability_blocks_laundry_until_repair_or_tune(self):
        pol = self.policy([servo(durability=.1)],
                          {"supervised": True, "clothesline_available": True,
                           "lint_less": "INSTALLED", "dryer_lint_state": "CLEAN"})
        self.assertEqual(pol["state"], "BLOCKED_REPAIR_FIRST")
        self.assertEqual(pol["laundry_autonomy"], "BLOCKED")
        self.assertEqual(pol["prerequisite_action"], "TUNE_UP_SERVO")
        self.assertEqual(pol["blocking_servos"], ["servo:a"])
        self.assertFalse(pol["dispatch_authorized"])

    def test_broken_servo_blocks_laundry_with_repair_prerequisite(self):
        pol = self.policy([servo(durability=.9, broken=True)],
                          {"supervised": True})
        self.assertEqual(pol["state"], "BLOCKED_REPAIR_FIRST")
        self.assertEqual(pol["prerequisite_action"], "REPAIR_SERVO")

    def test_unverified_durability_holds_laundry(self):
        unverified = {"sim_ref": "servo:a", "needs_verified": False, "needs": None,
                      "broken": False}
        pol = self.policy([unverified], {"supervised": True})
        self.assertEqual(pol["state"], "HOLD_DURABILITY_UNVERIFIED")
        self.assertEqual(pol["laundry_autonomy"], "HOLD")

    def test_stale_capture_holds_laundry_even_when_healthy(self):
        out = evaluate_household_upkeep(
            obs(servos=[servo()], observed_at_unix=time.time() - 3600),
            capture_ref=CAP)
        self.assertEqual(out["laundry_policy"]["state"], "HOLD_REOBSERVE_STALE")

    def test_clothesline_preferred_when_unsupervised(self):
        pol = self.policy([servo()], {"supervised": False, "clothesline_available": True,
                                      "lint_less": "NOT_INSTALLED"})
        self.assertEqual(pol["state"], "USE_CLOTHESLINE")
        self.assertEqual(pol["preference_order"][0], "CLOTHESLINE")

    def test_unsupervised_dryer_needs_lint_less_else_hold(self):
        held = self.policy([servo()], {"supervised": False, "clothesline_available": False,
                                       "lint_less": "NOT_INSTALLED"})
        self.assertEqual(held["state"], "HOLD_UNSUPERVISED_NO_LINT_LESS")
        self.assertEqual(held["laundry_autonomy"], "HOLD")
        unknown = self.policy([servo()])  # no laundry observation: unsupervised + unknown
        self.assertEqual(unknown["state"], "HOLD_UNSUPERVISED_NO_LINT_LESS")
        ok = self.policy([servo()], {"supervised": False, "clothesline_available": False,
                                     "lint_less": "INSTALLED"})
        self.assertEqual(ok["state"], "DRYER_ALLOWED_LINT_LESS")

    def test_supervised_dryer_requires_clean_lint_trap(self):
        dirty = self.policy([servo()], {"supervised": True, "dryer_lint_state": "DIRTY",
                                        "lint_less": "NOT_INSTALLED"})
        self.assertEqual(dirty["state"], "CLEAN_LINT_THEN_DRYER_SUPERVISED")
        clean = self.policy([servo()], {"supervised": True, "dryer_lint_state": "CLEAN",
                                        "lint_less": "NOT_INSTALLED"})
        self.assertEqual(clean["state"], "DRYER_ALLOWED_SUPERVISED_LINT_CLEAN")

    def test_no_servos_not_applicable_and_bad_laundry_fails_closed(self):
        self.assertEqual(self.policy([])["state"], "NOT_APPLICABLE_NO_SERVOS")
        with self.assertRaisesRegex(HouseholdUpkeepError, "UPKEEP_LAUNDRY_LINT_STATE_INVALID"):
            self.policy([servo()], {"dryer_lint_state": "SPARKLING"})
        with self.assertRaisesRegex(HouseholdUpkeepError, "UPKEEP_LAUNDRY_INVALID"):
            self.policy([servo()], "dryer")

    def test_contract_pins_fire_policy(self):
        fire = load_contract()["servo_fire_risk"]
        self.assertTrue(fire["clothesline_preferred_when_unsupervised"])
        self.assertTrue(fire["dryer_policy"]["clean_lint_trap_before_each_dryer_run"])
        self.assertEqual(fire["dryer_policy"]["unsupervised_dryer"],
                         "FORBIDDEN_UNLESS_LINT_LESS_INSTALLED")
        self.assertIn("Lint-Less", fire["dryer_policy"]["lint_less_upgrade"])


def laundry_appliance(ref="washer:1", **changes):
    row = {
        "ref": ref, "kind": "WASHER", "lot_ref": "lot:1", "capture_ref": CAP,
        "state": "EMPTY_IDLE", "access": "REACHABLE", "wash_affordance": "DISABLED",
        "registration": "UNKNOWN", "unreserved": True,
    }
    return {**row, **changes}


def laundry_observation(*appliances, **changes):
    return {"availability": {
        "actor_ref": "sim:helper", "load_ref": "pile:1", "lot_ref": "lot:1",
        "capture_ref": CAP, "lot_verified": True, "load_state": "NEEDS_WASH",
        "resolver": "NO_AVAILABLE_WASHER", "census_complete": True,
        "outcome_pending": False, "refresh_attempted": False,
        "appliances": list(appliances),
        **changes,
    }}


class LaundryAvailabilityTests(unittest.TestCase):
    def recovery(self, *appliances, options=None, visit=None, **gates):
        snapshot = obs(servos=[], laundry=laundry_observation(*appliances, **(options or {})))
        snapshot.update(visit or {})
        result = evaluate(snapshot, **gates)["laundry_policy"]["availability"]
        self.assertFalse(result["dispatch_authorized"])
        return result

    def test_two_washers_two_dryers_and_tooltip_alone_are_inconclusive(self):
        result = self.recovery(
            laundry_appliance(), laundry_appliance("washer:2"),
            laundry_appliance("dryer:1", kind="DRYER"),
            laundry_appliance("dryer:2", kind="DRYER"),
        )
        self.assertEqual(result["state"], "WASHER_UNAVAILABILITY_UNEXPLAINED")
        self.assertNotIn("action", result)

    def test_uses_working_second_washer_before_washtub_or_refresh(self):
        stale = laundry_appliance(registration="STALE_VERIFIED", registration_evidence_ref="ea:trace")
        washer = laundry_appliance("washer:2", wash_affordance="ENABLED")
        tub = laundry_appliance("tub:1", kind="WASHTUB", wash_affordance="ENABLED")
        for rows in ((stale, washer, tub), (tub, stale, washer)):
            with self.subTest(rows=rows):
                result = self.recovery(*rows)
                self.assertEqual((result["action"], result["target_ref"]),
                                 ("ADD_TO_WASHER", "washer:2"))
        self.assertEqual(self.recovery(stale, tub)["action"], "WASH_IN_WASHTUB")

    def test_only_corroborated_reachable_empty_idle_washer_can_be_refreshed(self):
        stale = laundry_appliance(registration="STALE_VERIFIED", registration_evidence_ref="ea:trace")
        result = self.recovery(stale)
        self.assertEqual(result["action"], "REFRESH_WASHER_REGISTRATION")
        self.assertEqual(result["target_ref"], stale["ref"])
        for changes, state in [
            ({"access": "BLOCKED"}, "WASHER_ACCESS_BLOCKED"),
            ({"state": "RUNNING"}, "WAIT_FOR_WASHER"),
            ({"state": "OCCUPIED"}, "WAIT_FOR_WASHER"),
            ({"unreserved": False}, "WAIT_FOR_WASHER"),
            ({"state": "BROKEN"}, "WASHERS_NEED_REPAIR"),
            ({"access": "UNKNOWN"}, "WASHER_UNAVAILABILITY_UNEXPLAINED"),
            ({"state": "UNKNOWN"}, "WASHER_UNAVAILABILITY_UNEXPLAINED"),
            ({"lot_ref": "lot:other"}, "REOBSERVE_APPLIANCE_SCOPE"),
            ({"capture_ref": "capture:old"}, "REOBSERVE_APPLIANCE_SCOPE"),
        ]:
            with self.subTest(changes=changes):
                result = self.recovery({**stale, **changes})
                self.assertEqual(result["state"], state)
                self.assertNotIn("action", result)
        with self.assertRaisesRegex(HouseholdUpkeepError, "REGISTRATION_EVIDENCE_REQUIRED"):
            self.recovery({**stale, "registration_evidence_ref": CAP})

    def test_hold_and_reconcile_preserve_the_current_load(self):
        stale = laundry_appliance(registration="STALE_VERIFIED", registration_evidence_ref="ea:trace")
        for options, state in [
            ({"outcome_pending": True}, "RECONCILE_PENDING_OUTCOME"),
            ({"refresh_attempted": True}, "NATIVE_REFRESH_ALREADY_ATTEMPTED"),
            ({"census_complete": False}, "REOBSERVE_INCOMPLETE_CENSUS"),
            ({"resolver": "UNKNOWN"}, "WASHER_UNAVAILABILITY_UNEXPLAINED"),
            ({"load_state": "OTHER"}, "WASH_NOT_ESTABLISHED"),
            ({"capture_ref": "capture:old"}, "REOBSERVE_STALE"),
            ({"lot_verified": False}, "REOBSERVE_STALE"),
        ]:
            with self.subTest(options=options):
                result = self.recovery(stale, options=options)
                self.assertEqual(result["state"], state)
                self.assertNotIn("action", result)
        eligible = laundry_appliance(wash_affordance="ENABLED")
        self.assertEqual(self.recovery(eligible, options={"refresh_attempted": True})["action"],
                         "ADD_TO_WASHER")

    def test_player_ownership_and_in_flight_laundry_win(self):
        washer = laundry_appliance(wash_affordance="ENABLED")
        for gate in ("player_directed", "already_busy", "build_or_buy_mode", "human_survival_hold"):
            with self.subTest(gate=gate):
                self.assertEqual(self.recovery(washer, **{gate: True})["state"],
                                 "YIELD_TO_PLAYER_OR_HOUSEHOLD_WORK")
        queued = {"action_id": "ADD_TO_WASHER", "origin": "SIM_AUTONOMY", "target_ref": "washer:2"}
        result = self.recovery(washer, visit={"actors": [actor(queue=[queued])]})
        self.assertEqual(result["state"], "WASH_ALREADY_QUEUED")
        queued["origin"] = "PLAYER"
        result = self.recovery(washer, visit={"actors": [actor(queue=[queued])]})
        self.assertEqual(result["state"], "YIELD_TO_PLAYER_OR_HOUSEHOLD_WORK")

    def test_servo_fire_and_water_guards_still_apply(self):
        washer = laundry_appliance(wash_affordance="ENABLED")
        tub = laundry_appliance("tub:1", kind="WASHTUB", wash_affordance="ENABLED")
        helper = actor(kind="SERVO")
        for robot, state in [
            (servo("sim:helper", durability=.1), "BLOCKED_REPAIR_FIRST"),
            (servo("sim:helper", charge=.08), "HOLD_SERVO_READINESS"),
            (servo("sim:helper", water_exposure="WET"), "HOLD_SERVO_READINESS"),
        ]:
            with self.subTest(state=state):
                result = self.recovery(washer, visit={"actors": [helper], "servos": [robot]})
                self.assertEqual(result["state"], state)
        result = self.recovery(tub, visit={"actors": [helper], "servos": [servo("sim:helper")]})
        self.assertEqual(result["state"], "NO_WASHER_PRESENT")

    def test_host_turn_exposes_policy_without_a_game_effect(self):
        laundry = laundry_observation(laundry_appliance(wash_affordance="ENABLED"))
        turn = evaluate_turn(
            NEEDS, household_upkeep=obs(servos=[], laundry=laundry), capture_ref=CAP,
            location_kind="home", queue=[], viewport={"state": "VIEWPORT_OK"},
        )
        report = turn["household_upkeep"]
        self.assertEqual(report["laundry_policy"]["availability"]["action"], "ADD_TO_WASHER")
        self.assertFalse(report["next_actions"])
        self.assertFalse(report["laundry_policy"]["availability"]["dispatch_authorized"])


class LaundryProcurementTests(unittest.TestCase):
    def report(self, funds, *, appliance=None, lot_model=None, **updates):
        request = {
            "capture_ref": CAP, "lot_ref": "lot:1", "load_ref": "pile:1",
            "household_ref": "household:test", "exhaustion_evidence_ref": "owned:proof",
            "owned_routes_exhausted": True, "outcome_pending": False,
            "purchase_attempted": False, "funding_state": "NOT_STARTED",
            "earn_available": False, "funds_observed": funds, "funds_capture_ref": CAP,
            "funds_evidence_ref": "funds:proof",
            "washer": {"capture_ref": CAP, "catalog_ref": "sku:washer", "price": 500,
                       "placement_ref": "position:washer", "placement_verified": True,
                       "compatible": True},
            **updates,
        }
        laundry = laundry_observation(*([appliance] if appliance else []))
        observation = obs(servos=[], laundry={**laundry, "procurement": request},
                          household_ref="household:test")
        report = evaluate(observation, lot_model=lot_model)["laundry_policy"]["procurement"]
        self.assertFalse(report["dispatch_authorized"])
        return report

    @patch("betterinstincts.household_upkeep.admit_live_structure_effect",
           return_value={"state": "LIBRARY_ADMIT"})
    def test_funding_and_purchase_reserve_boundaries(self, checkpoint):
        lot = {"lot_id": "lot:1"}
        get = lambda funds, **kwargs: self.report(funds, lot_model=lot, **kwargs)
        funded = get(999_900)
        self.assertEqual((funded["state"], funded["target_funds"], funded["subsidy_amount"]),
                         ("LAUNDRY_FUND_LAST_RESORT", 1_000_500, 600))
        self.assertEqual(funded["funding_source"], "CHEAT_SUBSIDY")
        self.assertEqual(get(1_000_499)["target_funds"], 1_000_500)
        self.assertEqual(get(1_000_500)["expected_funds_after"], 1_000_000)
        self.assertEqual(get(1_012_000)["expected_funds_after"], 1_011_500)
        self.assertEqual(get(999_900, earn_available=True)["state"],
                         "LAUNDRY_EARN_REQUIRED_BEFORE_PURCHASE")
        self.assertEqual(get(999_900, funding_state="NO_EFFECT")["state"],
                         "LAUNDRY_EARN_REQUIRED_BEFORE_PURCHASE")
        checkpoint.assert_called_with(lot, "PURCHASE_BUILD_OBJECT")

    @patch("betterinstincts.household_upkeep.admit_live_structure_effect",
           return_value={"state": "LIBRARY_ADMIT"})
    def test_fresh_readback_and_scope_after_console(self, _):
        lot = {"lot_id": "lot:1"}
        receipt = {
            "household_ref": "household:test", "lot_ref": "lot:1", "load_ref": "pile:1",
            "dispatch_ref": "dispatch:funds", "before_capture_ref": "capture:before",
            "after_capture_ref": "capture:after", "after_evidence_ref": "hud:independent",
            "funds_before": 999_000, "funds_after": 1_000_500, "target_funds": 1_000_500,
        }
        state = {"funding_state": "APPLIED", "lot_model": lot}
        self.assertEqual(self.report(1_000_499, funding_receipt=receipt, **state)["state"],
                         "LAUNDRY_EARN_REQUIRED_BEFORE_PURCHASE")
        self.assertEqual(self.report(1_000_500, funding_receipt=receipt, **state)["state"],
                         "LAUNDRY_PURCHASE_CANDIDATE")
        for key, value in (("lot_ref", "lot:foreign"), ("target_funds", 1_000_600),
                           ("after_capture_ref", "capture:before")):
            with self.subTest(key=key):
                result = self.report(1_010_000, funding_receipt={**receipt, key: value}, **state)
                self.assertEqual(result["state"], "LAUNDRY_RECONCILE_PROCUREMENT")

    def test_no_purchase_over_existing_routes_uncertain_effect_or_missing_checkpoint(self):
        washer = laundry_appliance(wash_affordance="ENABLED")
        self.assertEqual(self.report(1_005_000, appliance=washer)["state"],
                         "LAUNDRY_PROCUREMENT_NOT_ADMITTED")
        for updates, expected in [
            ({"outcome_pending": True}, "LAUNDRY_RECONCILE_PROCUREMENT"),
            ({"purchase_attempted": True}, "LAUNDRY_PURCHASE_ALREADY_ATTEMPTED"),
            ({"owned_routes_exhausted": False}, "LAUNDRY_USE_OR_RECOVER_OWNED_FIRST"),
            ({"funds_capture_ref": "capture:stale"}, "LAUNDRY_OBSERVE_CURRENT_FUNDS"),
            ({"household_ref": "household:foreign"}, "LAUNDRY_REOBSERVE_PROCUREMENT_SCOPE"),
            ({"washer": {"price": 500}}, "LAUNDRY_VERIFY_CATALOG_AND_PLACEMENT"),
            ({"lot_model": {"lot_id": "lot:1"}}, "LAUNDRY_VERIFY_WHOLE_LOT_CHECKPOINT"),
        ]:
            with self.subTest(updates=updates):
                self.assertEqual(self.report(1_005_000, **updates)["state"], expected)


class HostUpkeepIntegrationTests(unittest.TestCase):
    def test_threshold_routes_to_existing_funds_owner(self):
        upkeep = obs(
            servos=[], observed_actions=[], funds_observed=500_000, funds_capture_ref=CAP,
            funds_evidence_ref="hud:reserve", household_ref="household:test",
            save_ref="save:test", episode_ref="episode:reserve", bailout_enabled=True,
            bailout_attempted=False, funds_outcome_pending=False,
        )
        turn = evaluate_turn(NEEDS, household_upkeep=upkeep, location_kind="home",
                             capture_ref=CAP, queue=[], viewport={"state": "VIEWPORT_OK"})
        self.assertEqual(turn["next_gate"], "HOUSEHOLD_RESERVE_BAILOUT_READY")
        self.assertFalse(turn["household_upkeep"]["reserve_bailout"]["dispatch_authorized"])
        yield_turn = evaluate(upkeep, player_directed=True)
        self.assertEqual(yield_turn["reserve_bailout"]["state"], "BAILOUT_YIELD_TO_PLAYER_OR_PRIORITY")

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
