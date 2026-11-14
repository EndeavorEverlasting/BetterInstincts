import unittest
from betterinstincts.activity_chain import ActivityChainError, compile_activity_chain, gp_duration_forecast, SCHEMA


def row(sid, location, after=(), domain="ecology", cost=0, duration=4):
    return dict(id=sid, domain=domain, kind="ACTION", location=location,
                evidence_ref="e:"+sid, after=list(after), upper_minutes=duration,
                cost=cost)


def snapshot(**kw):
    x=dict(schema=SCHEMA, capture_ref="cap:1", sim_ref="sim:1", household_ref="hh:1",
           location="home", mode="PLANNING", scene_verified=True, queue_verified=True,
           player_directed=False, needs_safe=True, minutes_until_work=100,
           minutes_until_need_floor=80, reserve_minutes=10, available_funds=100,
           teleport_unlocked=True, teleport_evidence_ref="e:teleport",
           teleport_evidence_capture_ref="cap:1", completed=[])
    x.update(kw)
    return x


def route(a, b, method, minutes):
    return dict(**{"from":a, "to":b}, method=method,
                upper_minutes=minutes, admitted=True, evidence_ref="e:"+method,
                capture_ref="cap:1")


class ActivityChainTests(unittest.TestCase):
    def test_acquire_transfer_travel_craft_and_use(self):
        steps=[row("purchase", "home", domain="purchase", cost=15),
               row("transfer", "home", ["purchase"], domain="inventory"),
               row("craft", "garden", ["transfer"], domain="career"),
               row("apply", "garden", ["craft"], domain="ecology")]
        r=compile_activity_chain(snapshot(), steps,
                                 [route("home", "garden", "WALK", 15),
                                  route("home", "garden", "TELEPORT", 1)], capture_ref="cap:1")
        self.assertEqual(r["gate"], "PLAN_STAGED")
        self.assertEqual([a["step_id"] if a["kind"] == "ACTIVITY" else "TRAVEL:"+a["method"] for a in r["steps"]],
                         ["purchase", "transfer", "TRAVEL:TELEPORT", "craft", "apply"])
        self.assertEqual(r["projected_spend"], 15)
        self.assertFalse(r["execute_allowed"])

    def test_unlocked_only_teleport(self):
        s=[row("plant", "garden")]
        rr=[route("home", "garden", "WALK", 15), route("home", "garden", "TELEPORT", 1)]
        r=compile_activity_chain(snapshot(teleport_unlocked=False), s, rr, capture_ref="cap:1")
        self.assertEqual(r["steps"][0]["method"], "WALK")

    def test_stale_teleport_unlock_uses_walking(self):
        rr=[route("home", "garden", "WALK", 12), route("home", "garden", "TELEPORT", 1)]
        p=compile_activity_chain(snapshot(teleport_evidence_capture_ref="cap:old"),
                                 [row("a", "garden")],rr,capture_ref="cap:1")
        self.assertEqual(p["steps"][0]["method"],"WALK")

    def test_unfinished_dependent_purchase_is_not_started(self):
        steps=[row("buy", "home", cost=10, duration=3),
               row("craft", "home", ["buy"], domain="career", duration=25)]
        p=compile_activity_chain(snapshot(minutes_until_work=16), steps,capture_ref="cap:1")
        self.assertEqual(p["gate"],"DEFER_UNFINISHED_PURCHASE_CHAIN")
        self.assertEqual(p["steps"],[])
        self.assertEqual(p["deferred"],["buy","craft"])

    def test_work_and_need_budget_preserves_deferred(self):
        steps=[row("first", "home", duration=4), row("later", "home", ["first"], duration=25)]
        r=compile_activity_chain(snapshot(minutes_until_work=20), steps, capture_ref="cap:1")
        self.assertEqual([a["step_id"] for a in r["steps"]], ["first"])
        self.assertEqual(r["deferred"], ["later"])

    def test_inflight_never_replayed(self):
        r=compile_activity_chain(snapshot(inflight_step="pickup"), [row("pickup", "home")], capture_ref="cap:1")
        self.assertEqual(r["gate"], "RECONCILE_INFLIGHT_BEFORE_REPLAY")
        self.assertEqual(r["steps"], [])

    def test_completed_requires_provenance(self):
        r=compile_activity_chain(snapshot(completed=[dict(step_id="buy",outcome_ref="e:result",outcome_capture_ref="cap:1")]),
                                 [row("buy", "home"), row("use", "home", ["buy"])], capture_ref="cap:1")
        self.assertEqual([a["step_id"] for a in r["steps"]], ["use"])
        stale=compile_activity_chain(snapshot(completed=[dict(step_id="buy",outcome_ref="e:result",outcome_capture_ref="cap:old")]),
                                     [row("buy", "home")],capture_ref="cap:1")
        self.assertEqual(stale["gate"],"REVALIDATE_PREVIOUS_COMPLETIONS")
        resumed=compile_activity_chain(snapshot(completed=[dict(step_id="buy",outcome_ref="e:result",
                                   outcome_capture_ref="cap:old",revalidated_capture_ref="cap:1",still_valid=True)]),
                                     [row("buy", "home"),row("use","home",["buy"])],capture_ref="cap:1")
        self.assertEqual([a["step_id"] for a in resumed["steps"]],["use"])

    def test_player_and_stale_fail_closed(self):
        self.assertEqual(compile_activity_chain(snapshot(player_directed=True),[row("a","home")],capture_ref="cap:1")["gate"],"PLAYER_FIRST")
        self.assertEqual(compile_activity_chain(snapshot(capture_ref="cap:old"),[row("a","home")],capture_ref="cap:1")["gate"],"REOBSERVE_SCENE_AND_QUEUE")

    def test_cycle_and_unverified_route(self):
        with self.assertRaises(ActivityChainError):
            compile_activity_chain(snapshot(), [row("a","home",["b"]),row("b","home",["a"])],capture_ref="cap:1")
        r=compile_activity_chain(snapshot(),[row("a","garden")],capture_ref="cap:1")
        self.assertEqual(r["gate"], "INSUFFICIENT_EVIDENCE_OR_BUDGET")

    def test_purchase_denied_if_insufficient_funds(self):
        r=compile_activity_chain(snapshot(available_funds=3),[row("buy","home",cost=10)],capture_ref="cap:1")
        self.assertEqual(r["steps"], [])

    def test_gp_credible_interval_and_isolation(self):
        s=[dict(cohort="career:build1",x=i,minutes=10+i,observation_ref="o:"+str(i)) for i in range(6)]
        p=gp_duration_forecast(s,2.5,cohort="career:build1")
        self.assertGreater(p["upper_minutes"],p["mean_minutes"])
        self.assertLess(p["sigma_minutes"], 10)
        with self.assertRaises(ActivityChainError):
            gp_duration_forecast(s,2.5,cohort="ecology:build1")
        for k in ("RBF","PERIODIC"):
            self.assertTrue(gp_duration_forecast(s,2.5,cohort="career:build1",kernel=k)["upper_minutes"] > 0)

if __name__ == "__main__":
    unittest.main()
