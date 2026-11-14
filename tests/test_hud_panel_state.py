"""No-game, no-Pillow regressions for the HUD pixel/intent seam."""
import unittest
from betterinstincts.hud_panel_state import (
    PanelState, classify_calibrated_bounds, observe_inventory_image,
    propose_panel_posture,
)


class _Pixels:
    def __init__(self, title_y=None, sale=True):
        self.title_y, self.sale = title_y, sale

    def __getitem__(self, point):
        x, y = point
        if self.title_y is not None and y == self.title_y and 1520 <= x < 1570:
            return (20, 108, 155)
        if self.sale and y == 988 and 1640 <= x < 1710:
            return (20, 108, 155)
        return (10, 10, 10)


class _Image:
    def __init__(self, title_y=None, sale=True, size=(1919, 1079)):
        self.pixels, self.size = _Pixels(title_y, sale), size

    def convert(self, mode):
        assert mode == "RGB"
        return self

    def load(self):
        return self.pixels


def posture(state, intent="LONG_LIST", **changes):
    kw = dict(intent=intent, operator_idle=True, panel_owner="HOST",
              current_visible_panel_id="personal_inventory",
              scene_fresh=True, sim_fresh=True)
    kw.update(changes)
    return propose_panel_posture(state, **kw)


class HUDPanelStateTests(unittest.TestCase):
    def test_closed_inventory_is_not_a_global_hud_assertion(self):
        got = observe_inventory_image(_Image(sale=False), mode="LIVE")
        self.assertEqual(got.visibility, "COLLAPSED")
        self.assertEqual(got.panel_id, "personal_inventory")
        self.assertEqual(got.inventory_scroll, "UNKNOWN")
        self.assertFalse(got.executable)

    def test_min_max_and_intermediate_height(self):
        # Actual operator capture positions: min ~727, max 217,
        # intermediate screenshots ~346, 436, 521, 584, 731.
        cases = [
            (757, "CONDENSED", 0.0),
            (247, "EXPANDED", 1.0),
            (376, "CONDENSED", .747),
            (466, "CONDENSED", .571),
            (551, "CONDENSED", .404),
            (614, "CONDENSED", .28),
            (761, "CONDENSED", 0.0),
        ]
        for title_y, expected, ratio in cases:
            with self.subTest(title_y=title_y):
                got = observe_inventory_image(_Image(title_y), mode="LIVE")
                self.assertEqual(got.visibility, expected)
                self.assertAlmostEqual(got.expansion, ratio, places=2)
                self.assertEqual(got.cue_status, "TWO_CUES_PRESENT")

    def test_one_cue_is_not_presence_proof(self):
        self.assertEqual(observe_inventory_image(_Image(247, sale=False), mode="LIVE").visibility, "UNKNOWN")
        self.assertEqual(observe_inventory_image(_Image(None, sale=True), mode="LIVE").visibility, "UNKNOWN")

    def test_wrong_game_patch_mode_or_screen_fail_closed(self):
        self.assertEqual(observe_inventory_image(_Image(247), mode="BUILD").visibility, "UNKNOWN")
        self.assertEqual(observe_inventory_image(_Image(247), mode="LIVE", patch="1.120").visibility, "UNKNOWN")
        self.assertEqual(observe_inventory_image(_Image(247, size=(1920, 1080)), mode="LIVE").visibility, "UNKNOWN")

    def test_all_panels_get_generic_state_semantics_without_assumed_sensor(self):
        s = classify_calibrated_bounds(panel_id="skills", top_y=225, min_y=810,
                                       max_y=225, independent_cues=2)
        self.assertEqual(s.visibility, "EXPANDED")
        self.assertEqual(s.inventory_scroll, "UNKNOWN")
        t = classify_calibrated_bounds(panel_id="career", top_y=500, min_y=800,
                                       max_y=200, independent_cues=2)
        self.assertEqual(t.visibility, "CONDENSED")
        self.assertEqual(t.expansion, .5)
        u = classify_calibrated_bounds(panel_id="career", top_y=500, min_y=800,
                                       max_y=200, independent_cues=1)
        self.assertEqual(u.visibility, "UNKNOWN")
        self.assertEqual(classify_calibrated_bounds(
            panel_id="career", top_y=True, min_y=800, max_y=200,
            independent_cues=2).visibility, "UNKNOWN")

    def test_full_inventory_audit_requests_maximum_without_dispatch(self):
        compact = observe_inventory_image(_Image(757), mode="LIVE")
        p = posture(compact, "INVENTORY_AUDIT")
        self.assertEqual(p["requested"], "EXPANDED")
        self.assertEqual(p["target_expansion"], 1.0)
        self.assertEqual(p["op"], "REQUEST_CALIBRATED_RESIZE_THEN_REOBSERVE")
        self.assertFalse(p["execute_allowed"])

    def test_repeat_maximum_is_noop(self):
        expanded = observe_inventory_image(_Image(247), mode="LIVE")
        self.assertEqual(posture(expanded)["op"], "NOOP")

    def test_quick_inspection_preserves_condensed_state(self):
        compact = observe_inventory_image(_Image(757), mode="LIVE")
        self.assertEqual(posture(compact, "SINGLE_ITEM")["op"], "NOOP")

    def test_host_finishes_and_collapses_only_host_owned_panel(self):
        expanded = observe_inventory_image(_Image(247), mode="LIVE")
        p = posture(expanded, "FINISHED")
        self.assertEqual(p["op"], "REQUEST_EXISTING_HOTKEY_CLOSE")
        self.assertFalse(p["execute_allowed"])
        self.assertEqual(posture(expanded, "FINISHED", panel_owner="OPERATOR")["op"], "HOLD")

    def test_unsafe_and_unknown_conditions_never_propose_action(self):
        expanded = observe_inventory_image(_Image(247), mode="LIVE")
        conditions = [
            {"operator_idle": False}, {"panel_owner": "UNKNOWN"},
            {"scene_fresh": False}, {"sim_fresh": False},
            {"current_visible_panel_id": "career"},
        ]
        for gate in conditions:
            with self.subTest(gate=gate):
                self.assertEqual(posture(expanded, **gate)["op"], "HOLD")
        no_cue = observe_inventory_image(_Image(None), mode="LIVE")
        self.assertEqual(posture(no_cue)["op"], "HOLD")

    def test_open_and_unknown_intent_preserve_observation(self):
        closed = observe_inventory_image(_Image(sale=False), mode="LIVE")
        self.assertEqual(posture(closed)["op"], "HOLD")  # no proof that HUD is empty
        self.assertEqual(posture(closed, current_visible_panel_id=None)["op"], "HOLD")
        self.assertEqual(posture(closed, current_visible_panel_id="NONE")["op"],
                         "REQUEST_EXISTING_HOTKEY_OPEN_THEN_REOBSERVE")
        self.assertEqual(posture(closed, "BAD_INTENT")["op"], "HOLD")


if __name__ == "__main__":
    unittest.main()
