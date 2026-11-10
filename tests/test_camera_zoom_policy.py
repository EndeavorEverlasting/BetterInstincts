"""Agent zoom ladder + zoomed-in overlay clear (P01 semantic refinement)."""
from __future__ import annotations

import unittest

from betterinstincts.camera_traverse import (
    assess_agent_zoom_mode,
    plan_agent_default_view,
    plan_object_pick_identify,
    resolve_zoom_mode_alias,
    load_contract,
    zoom_controls,
)
from betterinstincts.active_sim_camera_lock import evaluate_active_sim_camera_lock
from betterinstincts.scene_ui_semantics import assess_overlay_clear_after_metadata
from betterinstincts.scenes import load_catalog


CAPTURE = "capture:zoom-1"


def obs(**overrides):
    data = {
        "source": "HOST_CAPTURE",
        "capture_ref": CAPTURE,
        "scene_id": "live_mode",
        "mode": "LIVE",
        "game_version": load_catalog()["game_version"],
        "capture_quality": "CONTENT_PRESENT",
        "viewport_state": "NORMAL",
        "save_authorized": True,
        "player_queue_owned": False,
        "text_entry_active": False,
        "modal_open": False,
        "player_camera_owned": False,
        "camera_revision": "camera:1",
        "active_sim_id": 492,
        "active_sim_instanced": True,
        "camera_follow_sim_id": 492,
        "camera_centered_sim_id": 492,
        "camera_displaced": False,
        "client_width": 1920,
        "client_height": 1080,
        "independent_cues": [
            {"source": "visual", "token": "live_hud"},
            {"source": "operator", "token": "live_confirmed"},
        ],
    }
    data.update(overrides)
    return data


class AgentZoomPolicyTests(unittest.TestCase):
    def test_contract_default_is_right_click_view_at_fifteen_percent_pullback(self):
        policy = load_contract()["agent_zoom_policy"]
        self.assertEqual(policy["default_mode"], "RIGHT_CLICK_VIEW")
        row = policy["modes"]["RIGHT_CLICK_VIEW"]
        self.assertEqual(row["zoom_in_fraction_of_max"], 0.85)
        self.assertEqual(row["pullback_from_max_fraction"], 0.15)
        self.assertEqual(policy["modes"]["ENVIRONMENT_NAV"]["zoom_in_fraction_of_max"], 0.5)
        self.assertEqual(policy["modes"]["TRAVEL_AFAR"]["zoom_in_fraction_of_max"], 0.0)

    def test_screenshot_aliases_resolve(self):
        self.assertEqual(resolve_zoom_mode_alias("SCREENSHOT_2"), "RIGHT_CLICK_VIEW")
        self.assertEqual(resolve_zoom_mode_alias("SCREENSHOT_3"), "MAX_CLOSE")
        self.assertEqual(resolve_zoom_mode_alias("SCREENSHOT_1"), "TRAVEL_AFAR")
        self.assertEqual(resolve_zoom_mode_alias("SCREENSHOT_4"), "TRAVEL_AFAR")
        self.assertEqual(resolve_zoom_mode_alias("HALFWAY_ZOOM"), "ENVIRONMENT_NAV")

    def test_default_view_is_right_click_not_street(self):
        out = plan_agent_default_view(observation=obs())
        self.assertEqual(out["state"], "AGENT_ZOOM_READY_FOR_ADMISSION")
        self.assertEqual(out["mode"], "RIGHT_CLICK_VIEW")
        self.assertEqual(out["zoom_in_fraction_of_max"], 0.85)
        self.assertFalse(out["execute_allowed"])

    def test_street_topdown_requires_restore_to_right_click_view(self):
        out = assess_agent_zoom_mode(
            observation=obs(zoom_mode_observed="TRAVEL_AFAR"),
        )
        self.assertEqual(out["state"], "AGENT_ZOOM_RESTORE_REQUIRED")
        self.assertEqual(out["gate"], "LEAVE_STREET_TOPDOWN_FOR_RIGHT_CLICK_VIEW")

    def test_travel_afar_without_goal_fails_closed(self):
        out = assess_agent_zoom_mode(intent="TRAVEL_AFAR", observation=obs())
        self.assertEqual(out["state"], "AGENT_ZOOM_HOLD")
        self.assertEqual(out["gate"], "TRAVEL_AFAR_GOAL_REQUIRED")

    def test_travel_afar_with_verified_goal_admits_plan_only(self):
        out = assess_agent_zoom_mode(
            intent="TRAVEL_AFAR",
            observation=obs(),
            travel_goal={
                "goal_id": "goal:travel-willow",
                "kind": "LONG_DISTANCE_TRAVEL",
                "source": "HOST_TASK",
                "destination_attested": True,
            },
        )
        self.assertEqual(out["state"], "AGENT_ZOOM_READY_FOR_ADMISSION")
        self.assertEqual(out["mode"], "TRAVEL_AFAR")
        self.assertTrue(out["forbidden_as_default"])

    def test_environment_nav_requires_planning_goal(self):
        blocked = assess_agent_zoom_mode(intent="ENVIRONMENT_NAV", observation=obs())
        self.assertEqual(blocked["gate"], "ENVIRONMENT_NAV_GOAL_REQUIRED")
        ok = assess_agent_zoom_mode(
            intent="ENVIRONMENT_NAV",
            observation=obs(),
            planning_goal={
                "goal_id": "goal:scan-lot",
                "kind": "ENVIRONMENT_PLANNING",
                "source": "HOST_TASK",
            },
        )
        self.assertEqual(ok["mode"], "ENVIRONMENT_NAV")
        self.assertEqual(ok["zoom_in_fraction_of_max"], 0.5)

    def test_build_top_down_map_is_default_census_zoom(self):
        self.assertEqual(resolve_zoom_mode_alias("ROOM_CENSUS_ZOOM"), "BUILD_TOP_DOWN_MAP")
        self.assertEqual(resolve_zoom_mode_alias("FLOOR_MAP_ZOOM"), "BUILD_TOP_DOWN_MAP")
        blocked = assess_agent_zoom_mode(intent="BUILD_TOP_DOWN_MAP", observation=obs())
        self.assertEqual(blocked["gate"], "BUILD_TOP_DOWN_MAP_GOAL_REQUIRED")
        ok = assess_agent_zoom_mode(
            intent="BUILD_TOP_DOWN_MAP",
            observation=obs(build_top_down_map_room_fit_attested=True),
            planning_goal={
                "goal_id": "goal:floor-census-n4",
                "kind": "LOT_FLOOR_MAP_CENSUS",
                "source": "HOST_TASK",
            },
        )
        self.assertEqual(ok["mode"], "BUILD_TOP_DOWN_MAP")
        self.assertEqual(ok["zoom_in_fraction_of_max"], 0.35)
        self.assertTrue(ok["preserve_operator_centered_frame"])
        self.assertTrue(ok["forbid_rezoom"])
        self.assertEqual(ok["census_inspect"], "BUILD_SELECT_INSPECT_ESCAPE")
        row = load_contract()["agent_zoom_policy"]["modes"]["BUILD_TOP_DOWN_MAP"]
        self.assertIn("lot_floor_map", row["default_for"])

    def test_camera_lock_blocks_parked_street_topdown(self):
        out = evaluate_active_sim_camera_lock(
            capture_ref=CAPTURE,
            observation=obs(zoom_mode_observed="SCREENSHOT_1"),
        )
        self.assertEqual(out["state"], "CAMERA_ZOOM_POLICY_BLOCK")
        self.assertEqual(out["gate"], "LEAVE_STREET_TOPDOWN_FOR_RIGHT_CLICK_VIEW")
        self.assertEqual(out["default_view"]["mode"], "RIGHT_CLICK_VIEW")


class OverlayClearAfterMetadataTests(unittest.TestCase):
    def test_withholds_until_metadata_tracked(self):
        out = assess_overlay_clear_after_metadata(
            capture_ref=CAPTURE,
            zoom_mode="RIGHT_CLICK_VIEW",
            observation=obs(clearable_overlays=[{
                "kind": "OPPORTUNITY_PANEL_EXPANDED",
                "capture_ref": CAPTURE,
                "visible": True,
                "metadata_tracked": False,
            }]),
        )
        self.assertEqual(out["state"], "OVERLAY_CLEAR_WITHHELD")
        self.assertEqual(out["withheld"][0]["reason"], "METADATA_NOT_TRACKED")

    def test_withholds_peer_leased_phone_surface(self):
        out = assess_overlay_clear_after_metadata(
            capture_ref=CAPTURE,
            zoom_mode="RIGHT_CLICK_VIEW",
            observation=obs(
                peer_hud_leases=[{
                    "surface": "PHONE",
                    "clearable_kind": "PHONE_INTERFACE_EXPANDED",
                    "reason": "PEER_LEASED_HUD_SURFACE",
                }],
                clearable_overlays=[{
                    "kind": "PHONE_INTERFACE_EXPANDED",
                    "capture_ref": CAPTURE,
                    "visible": True,
                    "metadata_tracked": True,
                    "accounted_by": "BETTER_INSTINCTS",
                    "dismiss_target": {
                        "capture_ref": CAPTURE,
                        "visible": True,
                        "enabled": True,
                        "obscured": False,
                        "hitbox": [200, 800, 260, 860],
                        "cues": [
                            {"source": "visual", "token": "tracked_overlay_dismiss_control"},
                            {"source": "operator", "token": "tracked_overlay_dismiss_confirmed"},
                        ],
                    },
                }],
            ),
        )
        self.assertEqual(out["state"], "OVERLAY_CLEAR_WITHHELD")
        self.assertEqual(out["withheld"][0]["reason"], "PEER_LEASED_HUD_SURFACE")

    def test_ready_only_after_accounted_metadata_and_hitbox(self):
        out = assess_overlay_clear_after_metadata(
            capture_ref=CAPTURE,
            zoom_mode="RIGHT_CLICK_VIEW",
            observation=obs(clearable_overlays=[{
                "kind": "CHEAT_CONSOLE",
                "capture_ref": CAPTURE,
                "visible": True,
                "metadata_tracked": True,
                "accounted_by": "BETTER_INSTINCTS",
                "dismiss_target": {
                    "capture_ref": CAPTURE,
                    "visible": True,
                    "enabled": True,
                    "obscured": False,
                    "hitbox": [20, 900, 80, 940],
                    "cues": [
                        {"source": "visual", "token": "tracked_overlay_dismiss_control"},
                        {"source": "operator", "token": "tracked_overlay_dismiss_confirmed"},
                    ],
                },
            }]),
        )
        self.assertEqual(out["state"], "OVERLAY_CLEAR_AWAIT_NATIVE_ADMISSION")
        self.assertEqual(out["clears"][0]["kind"], "CHEAT_CONSOLE")
        self.assertFalse(out["execute_allowed"])

    def test_unresolved_decision_blocks_chrome_clear(self):
        out = assess_overlay_clear_after_metadata(
            capture_ref=CAPTURE,
            zoom_mode="RIGHT_CLICK_VIEW",
            observation=obs(overlay={
                "overlay_id": "evt:1",
                "kind": "RANDOM_EVENT",
                "visible": True,
                "decision_state": "PENDING",
            }),
        )
        self.assertEqual(out["gate"], "OVERLAY_CLEAR_BLOCKED_BY_DECISION")

    def test_not_applicable_when_travel_afar(self):
        out = assess_overlay_clear_after_metadata(
            capture_ref=CAPTURE,
            zoom_mode="TRAVEL_AFAR",
            observation=obs(),
        )
        self.assertEqual(out["gate"], "OVERLAY_CLEAR_NOT_APPLICABLE")

    def test_zoom_controls_are_hotkey_not_right_click(self):
        zc = zoom_controls()
        self.assertEqual(zc["semantic_split"], "ZOOM_MODE_IS_NOT_ZOOM_CONTROL")
        self.assertEqual(zc["controls"]["CAMERA_ZOOM_IN"]["chord"], ["Z"])
        self.assertEqual(zc["controls"]["CAMERA_ZOOM_OUT"]["chord"], ["X"])
        self.assertIn("RIGHT_CLICK", zc["not_zoom_controls"])
        self.assertIn("RIGHT_CLICK_VIEW", zc["not_zoom_controls"])
        forbid = set(load_contract().get("forbidden") or [])
        self.assertIn("RIGHT_CLICK_AS_ZOOM_ACTUATOR", forbid)

    def test_object_pick_identify_plans_z_or_wheel(self):
        plan = plan_object_pick_identify(
            target_id="desk_computer",
            observation={"zoom_mode_observed": "TRAVEL_AFAR"},
        )
        self.assertEqual(plan["state"], "OBJECT_PICK_IDENTIFY_PLAN_READY")
        self.assertTrue(plan["leave_travel_afar_first"])
        self.assertEqual(plan["zoom_actuator"]["chord"], ["Z"])
        self.assertIn("RIGHT_CLICK", plan["zoom_actuator"]["forbidden"])
        self.assertFalse(plan["execute_allowed"])
        self.assertIn("ZOOM_IN_VIA_CAMERA_ZOOM_IN_OR_WHEEL", plan["steps"])
        self.assertIn("IDENTIFY_OBJECT_FROM_ZOOMED_CAPTURE", plan["steps"])


if __name__ == "__main__":
    unittest.main()
