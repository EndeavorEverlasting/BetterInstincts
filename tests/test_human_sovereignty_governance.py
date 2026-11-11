"""P00 regression: human-first ontology and canonical agent doctrine."""
import json
from pathlib import Path
import unittest

from scripts.check_ontology import validate_ontology

ROOT = Path(__file__).resolve().parents[1]


class HumanSovereigntyGovernanceTests(unittest.TestCase):
    def setUp(self):
        self.ontology = json.loads((ROOT / "contracts/ontology.v1.json").read_text(encoding="utf-8"))
        self.glossary = json.loads((ROOT / "contracts/glossary.v1.json").read_text(encoding="utf-8"))
        self.agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        self.doctrine = (ROOT / "docs/DOCTRINE.md").read_text(encoding="utf-8")

    def test_graph_schema_and_human_first_concepts(self):
        validate_ontology(self.ontology)
        self.assertGreaterEqual(self.ontology["revision"], 5)
        names = {
            "EFFECT_ADMISSION_CLASS", "PASSIVE_BACKGROUND_LANE", "HUMAN_CONTROL_RECLAIM",
            "OS_INPUT_CAPABILITY", "AGENT_ADOPTION_COVERAGE",
        }
        self.assertTrue(names.issubset(self.ontology["concepts"]))
        self.assertTrue(names.issubset(self.glossary["terms"]))

    def test_required_invariants_and_owned_relations(self):
        ids = {x["id"] for x in self.ontology["invariants"]}
        self.assertTrue({f"BI-ONT-{n:03}" for n in range(28,33)}.issubset(ids))
        edges = self.ontology["relations"]
        for source, predicate, dest in [
            ("PLAYER_INTENT", "OUTRANKS", "EFFECT_ADMISSION_CLASS"),
            ("HUMAN_CONTROL_RECLAIM", "REVOKES_STALE", "CONTROL_PERMIT"),
            ("PASSIVE_BACKGROUND_LANE", "MUST_NOT_ACQUIRE", "CONTROL_PERMIT"),
            ("OS_INPUT_CAPABILITY", "NOT_GRANTED_BY", "CONTROL_PERMIT"),
        ]:
            self.assertIn({"from":source,"predicate":predicate,"to":dest},edges)

    def test_governance_is_original_and_human_first(self):
        self.assertLessEqual(len(self.agents), 3600)
        self.assertIn("No agent may disable, dodge or remove the guard", self.agents)
        self.assertIn("scripts/check_human_sovereignty.py", self.agents)
        self.assertIn("15s idle", self.agents)
        self.assertIn("Print Screen", self.agents)
        self.assertIn("EFFECT_ADMISSION_CLASS", self.doctrine)
        self.assertIn("BI-002", self.doctrine)

    def test_glossary_classification_not_conflated(self):
        self.assertIn("acquisition", self.glossary["terms"]["EFFECT_ADMISSION_CLASS"]["definition"])
        self.assertIn("not a Python sandbox", self.glossary["terms"]["PASSIVE_BACKGROUND_LANE"]["definition"])
        self.assertIn("Windows", self.glossary["terms"]["P00_P01_HUMAN_FIRST_GATE"]["definition"])


if __name__ == "__main__":
    unittest.main()
