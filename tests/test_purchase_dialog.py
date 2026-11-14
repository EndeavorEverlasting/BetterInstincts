"""Adversarial offline tests for observed Sims purchase dialogs; no game access."""
from __future__ import annotations

import unittest

from betterinstincts.purchase_dialog import (
    derive_demand, discover_dialog_page, propose_dialog_cart_step,
    verify_dialog_purchase, MAX_PAGES, TRIGGERS,
)


def page(revision, rows, *, menu="apothecary_advanced", actor="portrait:servo-2",
         source="nectar_machine", top=True, bottom=True):
    return {
        "revision": revision, "menu_id": menu, "actor_id": actor, "source": source,
        "scroll": {"verified": True, "at_top": top, "at_bottom": bottom},
        "rows": [{"item_id": x[0], "label": x[1], "unit_price": x[2],
                  "selected_count": x[3] if len(x) > 3 else 0,
                  "increment_visible": True, "increment_hitbox_verified": True}
                 for x in rows],
    }


TOP = [("acorn", "Acorn", 35), ("aura_petal", "Aura Petal", 7),
       ("basil", "Basil", 11), ("daisy", "Daisy", 12),
       ("lemon", "Lemon", 30)]
BOTTOM = [("lemon", "Lemon", 30), ("lightning_root", "Lightning Root Leaf", 70),
          ("moss", "Lump of Moss", 9), ("sage", "Sage", 15),
          ("critter_bone", "Small Critter Bone", 55)]


def scan_advanced():
    first = discover_dialog_page(page("top1", TOP, bottom=False))
    assert first["action"]["kind"] == "SCROLL_DOWN_ONE_PAGE"
    final = discover_dialog_page(
        page("bottom1", BOTTOM, top=False), catalog=first["catalog"],
        last_acted_revision="top1")
    assert final["state"] == "COMPLETE"
    return final["catalog"]


def cart_step(catalog, shown, *, requests=None, cart=None, count=0, cost=0,
              spend_cap=100, **kwargs):
    data = dict(
        catalog=catalog, page=shown, requests=requests or {"acorn": 1},
        observed_total_count=count, observed_total_cost=cost,
        observed_funds=535262, approved_spend_cap=spend_cap,
        inventory_before={"acorn": 0, "critter_bone": 0},
        cart=cart, spending_authorized=True, explicit_command=True,
        player_idle_verified=True, paused_live_verified=True,
        scene_and_actor_verified=True, native_channel_verified=True,
        buy_control_visible=True, buy_control_hitbox_verified=True,
    )
    data.update(kwargs)
    return propose_dialog_cart_step(**data)


class PurchaseDialogTests(unittest.TestCase):
    def test_screen_sourced_advanced_list_scans_overlap_and_bottom(self):
        catalog = scan_advanced()
        self.assertEqual(len(catalog["items"]), 9)
        self.assertEqual(catalog["items"]["lemon"]["unit_price"], 30)
        self.assertTrue(catalog["complete"])
        self.assertEqual(len(catalog["pages"]), 2)

    def test_start_mid_catalog_seeks_top_before_scanning(self):
        first = discover_dialog_page(page("initial", BOTTOM, top=False))
        self.assertEqual(first["action"]["kind"], "SCROLL_UP_ONE_PAGE")
        self.assertEqual(first["catalog"]["items"], {})
        second = discover_dialog_page(
            page("after_up", TOP, bottom=False), catalog=first["catalog"],
            last_acted_revision="initial")
        self.assertEqual(second["action"]["kind"], "SCROLL_DOWN_ONE_PAGE")
        final = discover_dialog_page(
            page("after_down", BOTTOM, top=False), catalog=second["catalog"],
            last_acted_revision="after_up")
        self.assertEqual(final["state"], "COMPLETE")

    def test_no_scroll_medicine_and_other_five_row_pickers(self):
        fixtures = [
            ("purchase_medicine", "computer", [("medicine", "Medicine", 50)]),
            ("purchase_basic_ingredients", "nectar_machine", [
                ("apple", "Apple", 14), ("grape", "Grape", 41),
                ("lemon", "Lemon", 30), ("potato", "Potato", 17),
                ("strawberry", "Strawberry", 44)]),
            ("oversized_crop_seeds", "computer", [
                ("aubergine", "Aubergine Seeds", 15),
                ("lettuce", "Lettuce Seeds", 10),
                ("mushroom", "Mushroom Seeds", 15),
                ("pumpkin", "Pumpkin Seeds", 20),
                ("watermelon", "Watermelon Seeds", 25)]),
        ]
        for name, source, items in fixtures:
            with self.subTest(name=name):
                result = discover_dialog_page(page("one", items, menu=name, source=source))
                self.assertEqual(result["state"], "COMPLETE")
                self.assertEqual(len(result["catalog"]["items"]), len(items))

    def test_scroll_guards_are_bounded_not_infinite(self):
        first = discover_dialog_page(page("p1", TOP, bottom=False))
        stalled = discover_dialog_page(page("p2", TOP, top=False, bottom=False),
                                       catalog=first["catalog"])
        self.assertEqual(stalled["reason"], "SCROLL_DID_NOT_REVEAL_NEW_ROWS")
        stale = discover_dialog_page(page("p1", BOTTOM, top=False),
                                     catalog=first["catalog"], last_acted_revision="p1")
        self.assertEqual(stale["reason"], "FRESH_PAGE_REVISION_REQUIRED")
        seek = discover_dialog_page(page("seek1", BOTTOM, top=False))
        self.assertEqual(discover_dialog_page(
            page("seek2", BOTTOM, top=False), catalog=seek["catalog"]
        )["reason"], "SCROLL_TO_TOP_STALLED_OR_BOUNDED")
        self.assertEqual(MAX_PAGES, 24)

    def test_identity_drift_price_change_and_malformed_scroller_fail_closed(self):
        first = discover_dialog_page(page("p1", TOP, bottom=False))
        wrong_actor = discover_dialog_page(
            page("p2", BOTTOM, top=False, actor="portrait:other"),
            catalog=first["catalog"])
        self.assertEqual(wrong_actor["reason"], "MENU_OR_SELECTED_PORTRAIT_CHANGED")
        changed = list(BOTTOM)
        changed[0] = ("lemon", "Lemon", 300)
        self.assertEqual(discover_dialog_page(
            page("p3", changed, top=False), catalog=first["catalog"]
        )["reason"], "CATALOG_ITEM_IDENTITY_OR_PRICE_CHANGED")
        unverified = page("bad", TOP)
        unverified["scroll"]["verified"] = False
        self.assertEqual(discover_dialog_page(unverified)["reason"],
                         "FRESH_SCROLL_ENDPOINT_OBSERVATION_REQUIRED")
        unverified["scroll"]["verified"] = True
        unverified["rows"][0]["unit_price"] = True
        self.assertEqual(discover_dialog_page(unverified)["reason"],
                         "INVALID_OR_DUPLICATE_VISIBLE_ROW")

    def test_natural_triggers_require_real_stock_gap_evidence(self):
        catalog = scan_advanced()
        demands = derive_demand(catalog, [
            {"kind": "apothecary_recipe", "menu_id": catalog["menu_id"],
             "actor_id": catalog["actor_id"], "item_id": "lemon",
             "required": 3, "owned": 1, "evidence_ref": "observed-recipe-v1"},
            {"kind": "household_restock", "menu_id": catalog["menu_id"],
             "actor_id": catalog["actor_id"], "item_id": "sage",
             "required": 2, "owned": 2, "evidence_ref": "household-stock-v1"},
        ])
        self.assertEqual(demands["requests"], {"lemon": 2})
        self.assertIn("servo_repair_part", TRIGGERS)
        self.assertIn("career_required_material", TRIGGERS)
        self.assertIn("garden_missing_seed", TRIGGERS)
        self.assertEqual(derive_demand(catalog, [{
            "kind": "unknown", "menu_id": catalog["menu_id"],
            "actor_id": catalog["actor_id"], "item_id": "lemon",
            "required": 1, "owned": 0, "evidence_ref": "x",
        }])["reason"], "UNREVIEWED_ACTIVITY_TRIGGER")
        self.assertEqual(derive_demand(catalog, [{
            "kind": "garden_missing_seed", "menu_id": catalog["menu_id"],
            "actor_id": catalog["actor_id"], "item_id": "ghost",
            "required": 1, "owned": 0, "evidence_ref": "x",
        }])["reason"], "REQUIRED_ITEM_NOT_IN_FULL_CATALOG")

    def test_missing_ingredient_is_not_buy_everything(self):
        catalog = scan_advanced()
        result = derive_demand(catalog, [
            {"kind": "apothecary_recipe", "menu_id": catalog["menu_id"],
             "actor_id": catalog["actor_id"], "item_id": "lemon",
             "required": 1, "owned": 1, "evidence_ref": "recipe-readback"},
        ])
        self.assertEqual(result["requests"], {})

    def test_cross_page_cart_one_increment_per_readback_then_single_buy(self):
        catalog = scan_advanced()
        requests = {"acorn": 1, "critter_bone": 1}
        bottom = page("b1", BOTTOM, top=False)
        find_first = cart_step(catalog, bottom, requests=requests)
        self.assertEqual(find_first["action"]["kind"], "SCROLL_UP_ONE_PAGE")
        top = page("t1", TOP, bottom=False)
        inc1 = cart_step(catalog, top, requests=requests, cart=find_first["cart"])
        self.assertEqual(inc1["action"]["kind"], "INCREMENT_OBSERVED_ROW")
        self.assertEqual(inc1["action"]["item_id"], "acorn")
        self.assertFalse(inc1["execute_allowed"])
        self.assertEqual(cart_step(catalog, top, requests=requests,
                                   cart=inc1["cart"])["reason"],
                         "PENDING_EFFECT_REQUIRES_FRESH_READBACK")
        new_top = page("t2", [("acorn", "Acorn", 35, 1), *TOP[1:]], bottom=False)
        scroll = cart_step(catalog, new_top, requests=requests,
                           cart=inc1["cart"], count=1, cost=35)
        self.assertEqual(scroll["action"]["kind"], "SCROLL_DOWN_ONE_PAGE")
        self.assertEqual(scroll["cart"]["selected"], {"acorn": 1})
        inc2 = cart_step(catalog, page("b2", BOTTOM, top=False),
                         requests=requests, cart=scroll["cart"], count=1, cost=35)
        self.assertEqual(inc2["action"]["item_id"], "critter_bone")
        new_bottom = page("b3", [*BOTTOM[:-1],
                                ("critter_bone", "Small Critter Bone", 55, 1)], top=False)
        confirm = cart_step(catalog, new_bottom, requests=requests,
                            cart=inc2["cart"], count=2, cost=90)
        self.assertEqual(confirm["action"]["kind"], "CONFIRM_OBSERVED_PURCHASE")
        self.assertEqual(confirm["action"]["expected_total_cost"], 90)
        self.assertEqual(cart_step(catalog, new_bottom, requests=requests,
                                   cart=confirm["cart"], count=2, cost=90)["state"],
                         "NEEDS_RECONCILIATION")
        outcome = verify_dialog_purchase(catalog=catalog, cart=confirm["cart"],
                                         requests=requests,
                                         inventory_before={"acorn": 0, "critter_bone": 2},
                                         inventory_after={"acorn": 1, "critter_bone": 3},
                                         funds_before=535262, funds_after=535172)
        self.assertEqual(outcome["state"], "PURCHASE_OBSERVED")

    def test_no_spending_without_live_player_and_budget_gates(self):
        catalog = scan_advanced()
        top = page("fresh", TOP, bottom=False)
        cases = [
            ({"explicit_command": False}, "EXPLICIT_SPENDING_AUTHORIZATION_REQUIRED"),
            ({"spending_authorized": False}, "EXPLICIT_SPENDING_AUTHORIZATION_REQUIRED"),
            ({"player_idle_verified": False}, "FRESH_PLAYER_SCENE_AND_ACTOR_GUARD_REQUIRED"),
            ({"paused_live_verified": False}, "FRESH_PLAYER_SCENE_AND_ACTOR_GUARD_REQUIRED"),
            ({"scene_and_actor_verified": False}, "FRESH_PLAYER_SCENE_AND_ACTOR_GUARD_REQUIRED"),
            ({"native_channel_verified": False}, "VERIFIED_CHANNEL_OR_EXPLICIT_FALLBACK_OPT_IN_REQUIRED"),
            ({"spend_cap": 34}, "APPROVED_CAP_OR_FUNDS_EXCEEDED"),
            ({"observed_funds": 1}, "APPROVED_CAP_OR_FUNDS_EXCEEDED"),
            ({"inventory_before": {}}, "SELECTED_SIM_INVENTORY_BASELINE_REQUIRED"),
        ]
        for overrides, reason in cases:
            kwargs = dict(overrides)
            if "spend_cap" in kwargs:
                kwargs["approved_spend_cap"] = kwargs.pop("spend_cap")
            with self.subTest(kwargs=kwargs):
                self.assertEqual(cart_step(catalog, top, **kwargs)["reason"], reason)

    def test_increment_mismatch_does_not_blind_retry(self):
        catalog = scan_advanced()
        action = cart_step(catalog, page("p1", TOP, bottom=False))
        mismatch = cart_step(catalog, page("p2", TOP, bottom=False),
                             cart=action["cart"], count=0, cost=0)
        self.assertEqual(mismatch["state"], "NEEDS_RECONCILIATION")
        self.assertEqual(mismatch["reason"], "PENDING_CART_EFFECT_NOT_RECONCILED")

    def test_cart_rejects_hidden_manual_selection_and_price_drift(self):
        catalog = scan_advanced()
        manual = page("p1", [("acorn", "Acorn", 35, 1), *TOP[1:]], bottom=False)
        self.assertEqual(cart_step(catalog, manual, count=1, cost=35)["reason"],
                         "CART_TOTALS_OR_VISIBLE_COUNTS_MISMATCH")
        changed = page("p2", [("acorn", "Acorn", 36), *TOP[1:]], bottom=False)
        self.assertEqual(cart_step(catalog, changed)["reason"],
                         "VISIBLE_ROW_NOT_IN_FRESH_CATALOG")

    def test_outcome_requires_exact_funds_and_pocket_deltas(self):
        catalog = scan_advanced()
        confirm = {"pending": {"kind": "CONFIRM_OBSERVED_PURCHASE",
                               "expected_total_cost": 35},
                   "selected": {"acorn": 1}, "actor_id": catalog["actor_id"],
                   "menu_id": catalog["menu_id"]}
        base = dict(catalog=catalog, cart=confirm, requests={"acorn": 1},
                    inventory_before={"acorn": 0}, inventory_after={"acorn": 1},
                    funds_before=100, funds_after=65)
        self.assertEqual(verify_dialog_purchase(**base)["state"], "PURCHASE_OBSERVED")
        for changes in ({"funds_after": 66}, {"inventory_after": {"acorn": 0}},
                        {"requests": {"acorn": 2}}, {"inventory_before": {}},
                        {"funds_before": True}):
            with self.subTest(changes=changes):
                self.assertEqual(verify_dialog_purchase(**{**base, **changes})["state"],
                                 "NEEDS_RECONCILIATION")


if __name__ == "__main__":
    unittest.main()
