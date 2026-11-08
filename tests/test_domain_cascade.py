import unittest

from betterinstincts.domain_cascade import load_contract, poll_cascade

SIX = {
    "hunger": 0.1,
    "bladder": 0.2,
    "energy": 0.8,
    "hygiene": 0.8,
    "fun": 0.4,
    "social": 0.5,
}


class DomainCascadeTests(unittest.TestCase):
    def test_contract_order(self):
        cfg = load_contract()
        self.assertEqual(
            cfg["cascade_order"],
            [
                "needs",
                "balance",
                "budget",
                "career",
                "aspirations",
                "skills_whims",
                "relationships",
            ],
        )

    def test_cascade_includes_lb_detach_and_budget(self):
        out = poll_cascade(
            SIX,
            available_objects=["toilet", "bed", "shower", "phone"],
            funds=800,
        )
        self.assertEqual(out["state"], "DOMAIN_CASCADE_POLLED")
        domains = [r["domain"] for r in out["receipts"]]
        self.assertEqual(
            domains,
            [
                "needs",
                "balance",
                "budget",
                "career",
                "aspirations",
                "skills_whims",
                "relationships",
            ],
        )
        needs = out["receipts"][0]
        self.assertEqual(needs["gate"], "NEED_SERVICES_LOAD_BALANCE")
        self.assertIn("NEED_LB_DETACH", needs["findings"])
        self.assertIn("hunger", needs["payload"]["need_services"]["detached_needs"])
        balance = out["receipts"][1]
        self.assertEqual(balance["gate"], "BALANCE_IDLE")
        budget = out["receipts"][2]
        self.assertEqual(budget["payload"]["prior_needs_gate"], balance["gate"])

    def test_balance_ailment_receipt_beside_needs(self):
        out = poll_cascade(
            {need: 0.9 for need in SIX},
            balance_level="very_imbalanced",
            ailment="Burning Passion",
            funds=800,
        )
        balance = next(row for row in out["receipts"] if row["domain"] == "balance")
        self.assertEqual(balance["gate"], "READY_NATUROPATH")
        self.assertIn("BALANCE_CONDITION_HELD", balance["findings"])
        service = balance["payload"].get("balance_service") or {}
        self.assertTrue(service.get("condition_held"))
        self.assertEqual(service.get("ailment"), "burning_passion")

    def test_player_first_halts(self):
        out = poll_cascade(SIX, player_directed=True, funds=1000)
        self.assertEqual(out["gate"], "PLAYER_FIRST_OR_BUSY")
        self.assertEqual(out["action"], "HALT_CASCADE")
        self.assertEqual(len(out["receipts"]), 1)

    def test_completed_homework_is_not_reopened_by_book_observations(self):
        for book_present in (True, False):
            with self.subTest(book_present=book_present):
                out = poll_cascade(
                    {need: 0.9 for need in SIX}, homework_pending=False,
                    inventory_has_homework=book_present, homework_on_lot=not book_present,
                    location_kind="home", life_stage="teen",
                )
                career = next(row for row in out["receipts"] if row["domain"] == "career")
                self.assertEqual(career["gate"], "CAREER_IDLE")
                service = career["payload"].get("career_service") or {}
                self.assertFalse(service.get("obligation_held"))
                self.assertNotIn("teen_homework", career["payload"])

    def test_pending_homework_and_survival_priority_remain(self):
        for hunger, expected in ((0.9, "QUEUE_TEEN_HOMEWORK"), (0.1, "SURVIVAL_BEFORE_HOMEWORK")):
            with self.subTest(hunger=hunger):
                needs = {need: 0.9 for need in SIX}
                needs["hunger"] = hunger
                out = poll_cascade(
                    needs, homework_pending=True, inventory_has_homework=True,
                    location_kind="home", life_stage="teen",
                    available_objects=["fridge", "toilet", "bed", "shower", "phone"],
                )
                career = next(row for row in out["receipts"] if row["domain"] == "career")
                self.assertEqual(career["gate"], expected)

    def test_navigating_needs_advisory_on_needs_receipt(self):
        out = poll_cascade(
            {
                "hunger": 0.05,
                "bladder": 0.9,
                "energy": 0.9,
                "hygiene": 0.9,
                "fun": 0.2,
                "social": 0.2,
            },
            available_objects=["fridge", "toilet", "bed", "shower", "tv", "phone"],
            navigating_needs_active=True,
            navigating_needs_incomplete=["Cook a Meal or Have a Quick Meal"],
            funds=1200,
        )
        nav = out["receipts"][0]["payload"].get("navigating_needs")
        self.assertIsNotNone(nav)
        self.assertEqual(nav["gate"], "NAVIGATING_NEEDS_TANDEM")


if __name__ == "__main__":
    unittest.main()
