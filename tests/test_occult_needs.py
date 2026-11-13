"""Offline characterisation of occult motive schemas and reviewed advisory safety."""
import copy
import unittest

from betterinstincts.occult_needs import (
    OccultNeedsError, learn, load_catalog, new_model, recommend,
)

PATCH = "1.121.361.1020"
BASE = dict.fromkeys(("bladder", "hunger", "energy", "hygiene", "fun", "social"), .85)


def advice(profile="human", needs=None, actions=(), **kw):
    return recommend(profile, BASE if needs is None else needs, list(actions),
                     game_version=kw.pop("game_version", PATCH),
                     platform=kw.pop("platform", "windows"),
                     **kw)


def review(need, action, ref, *, outcome="helpful", before=.15, after=.6):
    return {"observation_ref": ref, "need": need, "action": action, "outcome": outcome,
            "operator_reviewed": True, "opt_in": True, "scene_verified": True,
            "before": before, "after": after, "game_version": PATCH,
            "platform": "windows"}


class OccultNeedsTests(unittest.TestCase):
    def test_catalog_exact_six_and_supported_profiles(self):
        cat = load_catalog()
        self.assertEqual(set(cat["ordinary_six"]), set(BASE))
        self.assertEqual(len(cat["profiles"]["fairy"]["motives"]), 5)
        self.assertEqual(len(cat["profiles"]["servo"]["motives"]), 4)
        self.assertNotIn("bladder", cat["profiles"]["fairy"]["motives"])
        self.assertNotIn("hygiene", cat["profiles"]["servo"]["motives"])
        self.assertIn("fury", cat["profiles"]["werewolf"]["auxiliary"])
        self.assertNotIn("fury", cat["profiles"]["werewolf"]["motives"])

    def test_six_need_hunger_priority_and_no_effect(self):
        out = advice(needs={**BASE, "hunger": .10, "bladder": .40},
                     actions=("QUICK_MEAL", "USE_TOILET"))
        self.assertEqual((out["state"], out["need"], out["suggested_action"]),
                         ("ADVISORY", "hunger", "QUICK_MEAL"))
        self.assertFalse(out["execute"])
        self.assertEqual(out["source"], "DETERMINISTIC_CATALOG")

    def test_no_need_due(self):
        self.assertEqual(advice(actions=("QUICK_MEAL",))["reason"],
                         "NO_MOTIVE_BELOW_PREEMPTIVE_THRESHOLD")

    def test_player_first_and_busy(self):
        for kwargs in ({"player_active": True}, {"player_directed": True},
                       {"already_busy": True}, {"supported_life_stage": False}):
            out = advice(needs={**BASE, "hunger": .1},
                         actions=("QUICK_MEAL",), **kwargs)
            self.assertEqual(out["reason"], "PLAYER_FIRST_OR_BUSY")
            self.assertFalse(out["execute"])

    def test_fairy_replaces_hunger_bladder_and_can_restore_emotional_force(self):
        fairy = dict.fromkeys(("energy", "hygiene", "fun", "social", "emotional_force"), .85)
        fairy["emotional_force"] = .12
        out = advice("fairy", fairy, ("REGENERATE_EMOTIONAL_FORCE_SELF",),
                     installed_packs=("Enchanted by Nature",))
        self.assertEqual(out["need"], "emotional_force")
        self.assertEqual(out["suggested_action"], "REGENERATE_EMOTIONAL_FORCE_SELF")
        self.assertFalse(out["execute"])

    def test_servo_never_falls_back_to_bath_or_food(self):
        servo = {"fun": .8, "social": .8, "charge": .1, "durability": .5}
        out = advice("servo", servo, ("TAKE_BATH", "QUICK_MEAL", "RECHARGE_SELF"),
                     installed_packs=("Discover University",))
        self.assertEqual((out["need"], out["suggested_action"]), ("charge", "RECHARGE_SELF"))

    def test_servo_self_tune_up_capability_gate(self):
        servo = {"fun": .8, "social": .8, "charge": .8, "durability": .1}
        self.assertEqual(advice("servo", servo, ("SELF_TUNE_UP",),
                                installed_packs=("Discover University",))["state"], "ABSTAIN")
        out = advice("servo", servo, ("SELF_TUNE_UP",), capabilities=("servo_self_tune_up",),
                     installed_packs=("Discover University",))
        self.assertEqual(out["suggested_action"], "SELF_TUNE_UP")

    def test_mermaid_hydration_and_vampire_thirst(self):
        mermaid = {"bladder": .8, "hunger": .8, "energy": .8,
                   "hydration": .1, "fun": .8, "social": .8}
        self.assertEqual(advice("mermaid", mermaid, ("SWIM",),
                                installed_packs=("Island Living",))["need"], "hydration")
        vampire = {"bladder": .8, "thirst": .1, "vampire_energy": .8,
                   "hygiene": .8, "fun": .8, "social": .8}
        out = advice("vampire", vampire, ("DRINK_FROM_SIM", "DRINK_PLASMA_PACK"),
                     installed_packs=("Vampires",))
        self.assertEqual(out["suggested_action"], "DRINK_PLASMA_PACK")
        self.assertEqual(advice("vampire", vampire, ("DRINK_FROM_SIM",),
                                installed_packs=("Vampires",))["reason"],
                         "NO_SAFE_OBSERVED_REMEDY")

    def test_unknown_ghost_and_hybrid_abstain(self):
        self.assertEqual(advice("ghost", {}, ())["reason"], "LOCAL_MOTIVE_SCHEMA_REQUIRED")
        self.assertEqual(advice("vampire_fairy", {}, ())["reason"],
                         "UNSUPPORTED_OR_HYBRID_SIM_PROFILE")

    def test_missing_pack_and_exact_motive_schema_abstain(self):
        fairy = {"emotional_force": .1}
        self.assertEqual(advice("fairy", fairy, ("ABSORB_EMOTION",))["reason"],
                         "REQUIRED_PACK_NOT_CONFIRMED")
        self.assertEqual(advice("fairy", fairy, ("ABSORB_EMOTION",),
                                installed_packs=("Enchanted by Nature",))["reason"],
                         "MOTIVE_SCHEMA_MISMATCH")

    def test_invalid_meter_or_observed_action_is_rejected(self):
        with self.assertRaises(OccultNeedsError):
            advice(needs={**BASE, "hunger": float("nan")}, actions=("QUICK_MEAL",))
        with self.assertRaises(OccultNeedsError):
            advice(needs={**BASE, "hunger": .1}, actions=("QUICK_MEAL", "QUICK_MEAL"))
        self.assertEqual(advice(needs={**BASE, "hunger": .1}, actions=("FAKE_API",))["state"],
                         "ABSTAIN")

    def test_reviewed_learning_only_overrides_with_support(self):
        model = new_model(profile="human", game_version=PATCH, platform="windows")
        for i in range(3):
            model = learn(model, review("hunger", "COOK_MEAL", "capture:test:%04d" % i))
        out = advice(needs={**BASE, "hunger": .1}, actions=("QUICK_MEAL", "COOK_MEAL"),
                     model=model)
        self.assertEqual(out["suggested_action"], "COOK_MEAL")
        self.assertEqual((out["helpful"], out["harmful"]), (3, 0))
        self.assertEqual(out["source"], "REVIEWED_OUTCOMES")

    def test_replayed_review_rejected_across_model_updates(self):
        model = new_model(profile="human", game_version=PATCH, platform="windows")
        event = review("hunger", "QUICK_MEAL", "capture:test:0001")
        updated = learn(model, event)
        with self.assertRaisesRegex(OccultNeedsError, "OBSERVATION_REPLAY"):
            learn(updated, event)
        self.assertEqual(model["events"], [])  # No in-place model mutation.

    def test_bad_review_without_opt_in_or_meter_delta_rejected(self):
        model = new_model(profile="human", game_version=PATCH, platform="windows")
        event = review("hunger", "QUICK_MEAL", "capture:test:0002")
        event["opt_in"] = False
        with self.assertRaises(OccultNeedsError):
            learn(model, event)
        event["opt_in"] = True
        event["after"] = .15
        with self.assertRaisesRegex(OccultNeedsError, "HELPFUL_OUTCOME_NOT_MEASURED"):
            learn(model, event)

    def test_harmful_review_prevents_blind_replay(self):
        model = new_model(profile="human", game_version=PATCH, platform="windows")
        model = learn(model, review("hunger", "QUICK_MEAL", "capture:test:harm1",
                                    outcome="harmful", before=.15, after=.14))
        out = advice(needs={**BASE, "hunger": .1}, actions=("QUICK_MEAL", "COOK_MEAL"),
                     model=model)
        self.assertEqual(out["suggested_action"], "COOK_MEAL")

    def test_learning_profile_and_patch_cannot_leak(self):
        model = new_model(profile="human", game_version=PATCH, platform="windows")
        with self.assertRaisesRegex(OccultNeedsError, "MODEL_CONTEXT_MISMATCH"):
            advice("alien", {**BASE, "hunger": .1}, ("QUICK_MEAL",),
                   installed_packs=("Get to Work",), model=model)
        with self.assertRaisesRegex(OccultNeedsError, "MODEL_CONTEXT_MISMATCH"):
            advice(needs={**BASE, "hunger": .1}, actions=("QUICK_MEAL",),
                   game_version="1.121.361.1000", model=model)

    def test_model_replay_storage_corruption_rejected(self):
        model = new_model(profile="human", game_version=PATCH, platform="windows")
        model = learn(model, review("hunger", "QUICK_MEAL", "capture:test:0003"))
        corrupted = copy.deepcopy(model)
        corrupted["events"].append(copy.deepcopy(corrupted["events"][0]))
        with self.assertRaises(OccultNeedsError):
            advice(needs={**BASE, "hunger": .1}, actions=("QUICK_MEAL",), model=corrupted)

    def test_no_implicit_approval_from_catalog(self):
        self.assertEqual(advice(needs={**BASE, "hunger": .1})["reason"],
                         "NO_SAFE_OBSERVED_REMEDY")


if __name__ == "__main__":
    unittest.main()
