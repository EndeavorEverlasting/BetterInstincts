import unittest
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from betterinstincts import host_listener
from betterinstincts.player_presence import PresenceProbe
from betterinstincts.preference_corrections import IDENTITY, TARGET, evaluate_correction


def request(stage="live", **observation):
    data = {
        "request_ref": "request-1",
        "session_id": "sims-live-1",
        "process_id": 412,
        "game_build": "1.121.361.1020",
        "save_ref": "lab-save",
        "sim_id": "sim-1",
        "pref_revision": "revision-1",
        "family": "likes_dislikes",
        "category": "activity",
        "topic_id": "robotics",
        "current_value": "dislike",
        "desired_value": "like",
        "preference_owner": "automation",
        "reason": "mistake",
        "now_ms": 1050,
        "observation": {
            "stage": stage, "capture_ref": "capture:current", "captured_at_ms": 1000,
            "authorized_lab_save": True, "paused": True, "stage_verified": True,
            "modal_open": False, "pref_revision": "revision-1", **observation,
        },
    }
    data["observation"].update({key: data[key] for key in IDENTITY})
    attach_mistake(data)
    return data


def attach_mistake(data):
    data["mistake"] = {
        **{key: data[key] for key in (*IDENTITY, *TARGET, "pref_revision")},
        "receipt_ref": "mistake-1", "source": "automation_receipt",
        "mistaken_value": data["current_value"], "restore_value": data["desired_value"],
    }


def dispatched(data, target):
    return {
        **{k: data[k] for k in ("request_ref", *IDENTITY, *TARGET, "desired_value")},
        "state": "INPUT_DISPATCHED", "target": target,
        "capture_ref": "previous-capture", "captured_at_ms": 900,
    }


def evaluate(data, **context):
    return evaluate_correction(data, **{"automation_opt_in": True, "known_game_build": True, **context})


class PreferenceCorrectionTests(unittest.TestCase):
    def test_live_open_and_simology_entry(self):
        first = evaluate(request())
        self.assertEqual(first["hotkey"], ["Y"])
        self.assertEqual(first["mouse_reference"]["client_xy"], [1786, 1045])
        self.assertIsNone(first["control_permit"])
        self.assertEqual(evaluate(request("simology"))["target"],
                         "live.simology.preferences.enter_create_a_sim")

    def test_category_alias_and_distinct_fashion_way_of_life(self):
        data = request("cas_preference_categories", family="likes_dislikes", existing_household_verified=True)
        self.assertEqual(evaluate(data)["labels"], ["Activity", "Hobbies & Skills"])
        data.update(category="fashion", topic_id="preppy")
        attach_mistake(data)
        self.assertEqual(evaluate(data)["target"], "cas.likes_dislikes.category.fashion")

        data.update(family="attraction", current_value="turn_off", desired_value="turn_on")
        attach_mistake(data)
        self.assertEqual(evaluate(data)["reason"], "LOVESTRUCK_AVAILABILITY_REQUIRED")
        data["observation"]["lovestruck_attested"] = True
        self.assertEqual(evaluate(data)["target"], "cas.preferences.back_to_families")
        data["observation"]["family"] = "attraction"
        self.assertEqual(evaluate(data)["target"], "cas.attraction.category.fashion")
        data.update(category="way_of_life", topic_id="academic")
        attach_mistake(data)
        self.assertEqual(evaluate(data)["target"], "cas.attraction.category.way_of_life")

    def test_staged_change_requires_a_distinct_receipt_and_game_readback(self):
        data = request("cas_preference_tiles", existing_household_verified=True, family="likes_dislikes",
                       category="activity", topic_id="robotics", value="dislike",
                       other_cas_edits_detected=False)
        clear = evaluate(data)["target"]
        self.assertEqual(clear, "cas.likes_dislikes.activity.robotics.clear.dislike")
        data["previous_action"] = dispatched(data, clear)
        self.assertEqual(evaluate(data)["reason"], "PREVIOUS_EDIT_RECONCILIATION_REQUIRED")
        del data["previous_action"]
        data["observation"]["value"] = "neutral"
        self.assertEqual(evaluate(data)["reason"], "PREFERENCE_VALUE_CHANGED")
        data["previous_action"] = dispatched(data, clear)
        select = evaluate(data)["target"]
        self.assertEqual(select, "cas.likes_dislikes.activity.robotics.select.like")
        data["observation"]["value"] = "like"
        self.assertEqual(evaluate(data)["reason"], "STAGED_EDIT_READBACK_REQUIRED")
        data["previous_action"] = dispatched(data, select)
        data["observation"]["other_cas_edits_detected"] = True
        self.assertEqual(evaluate(data)["reason"], "CAS_EDIT_SCOPE_UNVERIFIED")
        data["observation"]["other_cas_edits_detected"] = False
        confirm = evaluate(data)["target"]

        data["observation"].update(stage="live_readback", pref_revision="revision-2")
        self.assertEqual(evaluate(data)["reason"], "LIVE_EFFECT_READBACK_REQUIRED")
        data["confirmation"] = dispatched(data, confirm)
        self.assertEqual(evaluate(data)["state"], "OBSERVED_DESIRED_VALUE")
        data["observation"]["capture_ref"] = data["confirmation"]["capture_ref"]
        self.assertEqual(evaluate(data)["reason"], "LIVE_EFFECT_READBACK_REQUIRED")

    def test_player_context_and_fresh_same_sim_lab_are_required(self):
        data = request()
        self.assertEqual(evaluate(data, player_directed=True)["reason"], "PLAYER_DIRECTED")
        data["preference_owner"] = "player"
        self.assertEqual(evaluate(data)["reason"], "PLAYER_INTENT_PROTECTED")
        data["mistake"]["source"] = "operator_correction"
        self.assertEqual(evaluate(data)["state"], "NEXT_TARGET")

        for key, value, reason in (
            ("process_id", 413, "CURRENT_SIM_SAVE_SESSION_REQUIRED"),
            ("sim_id", "other-sim", "CURRENT_SIM_SAVE_SESSION_REQUIRED"),
            ("authorized_lab_save", False, "FRESH_PAUSED_LAB_SCENE_REQUIRED"),
            ("captured_at_ms", 1051, "FRESH_CAPTURE_REQUIRED"),
            ("stage", "cas_existing_household", "EXISTING_HOUSEHOLD_CAS_REQUIRED"),
        ):
            changed = deepcopy(data)
            changed["observation"][key] = value
            self.assertEqual(evaluate(changed)["reason"], reason)

    def test_attributed_outcomes_protect_needs_and_reject_duplicates(self):
        data = request()
        data["reason"] = "repeated_behavior"
        data["paired_outcomes"] = [
            {
                **{key: data[key] for key in ("game_build", "save_ref", "sim_id", *TARGET)},
                "attributed_to_preference": True, "matched_conditions": True,
                "availability_unchanged": True, "window_ref": f"window-{i}",
                "current_receipt": f"before-{i}", "candidate_receipt": f"after-{i}",
                "current_value": "dislike", "candidate_value": "like",
                "current_outcome": {"needs": 0, "net_income": -.6, "skill": -.5, "career": -.5},
                "candidate_outcome": {"needs": 0, "net_income": .6, "skill": .5, "career": .5},
            }
            for i in range(3)
        ]
        positive = evaluate(data)
        self.assertEqual(positive["state"], "NEXT_TARGET")
        self.assertAlmostEqual(positive["score"]["conservative_gain"], .325)
        for key, value in (
            ("current_receipt", "after-0"), ("window_ref", "window-0"), ("sim_id", "other-sim"),
            ("attributed_to_preference", False), ("availability_unchanged", False),
        ):
            modified = deepcopy(data)
            modified["paired_outcomes"][-1][key] = value
            self.assertEqual(evaluate(modified)["reason"], "ATTRIBUTED_COMPARISON_REQUIRED")
        protected = deepcopy(data)
        protected["paired_outcomes"][-1]["candidate_outcome"]["needs"] = -.01
        self.assertEqual(evaluate(protected)["reason"], "ATTRIBUTED_COMPARISON_REQUIRED")
        contradictory = deepcopy(data)
        contradictory["paired_outcomes"][-1]["candidate_outcome"] = {
            "needs": 0, "net_income": -1, "skill": -1, "career": -1,
        }
        self.assertEqual(evaluate(contradictory)["reason"], "PRODUCTIVITY_GAIN_INSUFFICIENT")
        data["preference_owner"] = "player"
        self.assertEqual(evaluate(data)["reason"], "PLAYER_INTENT_PROTECTED")

    def test_unknown_preference_scene_and_hidden_target_hold(self):
        self.assertEqual(evaluate(request("cas_create_household", existing_household_verified=True))["reason"],
                         "UNKNOWN_PREFERENCE_SCENE")
        data = request("cas_preference_tiles", existing_household_verified=True,
                       family="likes_dislikes", category="activity")
        result = evaluate(data)
        self.assertEqual(result["search_container"], "cas.likes_dislikes.category.activity")
        self.assertEqual(result["reason"], "TARGET_ROW_NOT_OBSERVED")


class ListenerPreferenceCorrectionTests(unittest.TestCase):
    def test_tick_routes_cas_and_yields_to_player(self):
        data = request("cas_preference_categories", family="likes_dislikes",
                       existing_household_verified=True)
        observation = {
            "schema": "betterinstincts.host-listener.observation/v1",
            "needs": dict.fromkeys(("hunger", "bladder", "energy", "hygiene", "fun", "social"), .8),
            "queue": [],
            "game_version": data["game_build"],
            "capture_ref": data["observation"]["capture_ref"],
            "preference_correction_opt_in": True,
            "preference_game_build_confirmed": True,
            "preference_correction": data,
        }
        with TemporaryDirectory() as scratch:
            root = Path(scratch)
            with (patch.object(host_listener, "OUTPUT", root / "dist"),
                  patch.object(host_listener, "ROOT", root),
                  patch.object(host_listener.time, "time_ns", return_value=1_050_000_000)):
                session = data["session_id"]
                host_listener.activate(session)
                probe = PresenceProbe(foreground_is_sims=True, cursor_in_client=False,
                                      foreground_process_id=data["process_id"], last_input_age_ms=60_000)
                result = host_listener.tick(session, observation, presence_probe=probe)
                self.assertEqual(result["preference_correction"]["target"],
                                 "cas.likes_dislikes.category.activity")
                busy = PresenceProbe(foreground_is_sims=True, cursor_in_client=True,
                                     foreground_process_id=data["process_id"], last_input_age_ms=0)
                yielded = host_listener.tick(session, observation, presence_probe=busy)
                self.assertEqual(yielded["preference_correction"]["reason"], "PLAYER_DIRECTED")
                observation["capture_ref"] = "capture:different"
                stale = host_listener.tick(session, observation, presence_probe=probe)
                self.assertEqual(stale["preference_correction"]["reason"], "LISTENER_CONTEXT_MISMATCH")


if __name__ == "__main__":
    unittest.main()
