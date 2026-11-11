"""P00/P01 negative acceptance tests for native-first gameplay implementation."""
from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from scripts.check_native_gameplay_authority import (
    NativeGameplayError, inspect_core_source,
    validate_contract, validate_route_decisions,
)

ROOT=Path(__file__).resolve().parents[1]
CONTRACT=json.loads((ROOT/"contracts/native-gameplay-authority.v1.json").read_text())
CORE="betterinstincts/autonomy_moderation.py"
HOST="betterinstincts/host_automate.py"


def decision(path: str, route: str="POLICY_ONLY", **kwargs) -> dict:
    row={"path":path,"route":route,
         "reason":"Bounded evaluation without installed Sims game side effects",
         "game_effect_claim":"NONE"}
    if route=="POLICY_ONLY":
        row["successor_issue"]=171
    if route=="HOST_LAB_ONLY":
        row["autonomy_runtime"]=False
    if route in {"EA_TUNING","EA_SCRIPT"}:
        row.update(game_effect_claim="OFFLINE_ONLY",
                   game_build="1.121.361.1020",
                   ea_source_ref="local:read-only-selected-xml-export")
    row.update(kwargs)
    return {"schema":"betterinstincts.native-gameplay-decision/v1","files":[row]}


class NativeGameplayAuthorityTests(unittest.TestCase):
    def test_manifest_is_wired_to_governance_and_ci(self):
        report=validate_contract(CONTRACT)
        self.assertEqual(report["state"],"PASS")
        self.assertGreaterEqual(report["core_owners"],7)

    def test_native_first_cannot_be_diluted(self):
        broken=copy.deepcopy(CONTRACT)
        broken["native_first"]=False
        with self.assertRaisesRegex(NativeGameplayError,"EA_NATIVE_FIRST_REGRESSION"):
            validate_contract(broken)
        broken=copy.deepcopy(CONTRACT)
        broken["routes"]["HOST_LAB_ONLY"]["game_effect_candidate"]=True
        with self.assertRaisesRegex(NativeGameplayError,"HOST_OR_POLICY_PROMOTED_TO_GAME_EFFECT"):
            validate_contract(broken)

    def test_product_change_requires_routed_decision(self):
        with self.assertRaisesRegex(NativeGameplayError,"UNROUTED_PRODUCT_CHANGE"):
            validate_route_decisions(CONTRACT,[CORE],[])
        with self.assertRaisesRegex(NativeGameplayError,"NATIVE_DECISION_PATH_UNRELATED"):
            validate_route_decisions(CONTRACT,[CORE],[decision(HOST,"HOST_LAB_ONLY")])

    def test_all_new_product_modules_need_review(self):
        new="betterinstincts/new_future_microsystem.py"
        with self.assertRaisesRegex(NativeGameplayError,"UNROUTED_PRODUCT_CHANGE"):
            validate_route_decisions(CONTRACT,[new],[])
        self.assertEqual(validate_route_decisions(CONTRACT,[new],
                         [decision(new,"NON_GAMEPLAY")])["changed_product_files"],1)

    def test_core_gameplay_cannot_be_mislabeled_host_or_non_game(self):
        for route in ("HOST_LAB_ONLY","NON_GAMEPLAY"):
            with self.subTest(route=route),self.assertRaisesRegex(
                NativeGameplayError,"GAMEPLAY_CORE_CANNOT_USE_DESKTOP"
            ):
                validate_route_decisions(CONTRACT,[CORE],[decision(CORE,route)])

    def test_core_screen_input_is_rejected_even_when_disguised_as_policy(self):
        for payload in ("import pyautogui", "from ctypes import windll",
                        "SendInput(123)", "SetForegroundWindow(pid)",
                        "win32gui.PostMessage"):
            with self.subTest(payload=payload):
                self.assertTrue(inspect_core_source(payload,
                    CONTRACT["source_policy"]["core_desktop_input_sentinels"]))
        self.assertFalse(inspect_core_source("import math\ndef decide(): return 1",
                    CONTRACT["source_policy"]["core_desktop_input_sentinels"]))

    def test_policy_cannot_claim_runtime_or_missing_successor(self):
        cases=(
            ({"game_effect_claim":"OFFLINE_ONLY"},"NON_NATIVE_GAME_EFFECT_CLAIM"),
            ({"game_effect_claim":"GAME_CERTIFIED"},"NATIVE_ROUTE_CANNOT_SELF_CERTIFY"),
            ({"successor_issue":None},"NON_NATIVE_GAME_EFFECT_CLAIM"),
        )
        for kwargs,error in cases:
            with self.subTest(kwargs=kwargs),self.assertRaisesRegex(
                NativeGameplayError,error
            ):
                validate_route_decisions(CONTRACT,[CORE],[decision(CORE,**kwargs)])

    def test_native_scripts_require_game_build_and_source_provenance(self):
        for kwargs in (
            {"game_build":"UNKNOWN"},
            {"game_build":"latest"},
            {"ea_source_ref":""},
            {"game_effect_claim":"NONE"},
        ):
            with self.subTest(kwargs=kwargs),self.assertRaisesRegex(
                NativeGameplayError,"EA_NATIVE_SOURCE_EVIDENCE_MISSING"
            ):
                validate_route_decisions(CONTRACT,[CORE],[decision(CORE,"EA_SCRIPT",**kwargs)])
        ok=validate_route_decisions(CONTRACT,[CORE],[decision(CORE,"EA_SCRIPT")])
        self.assertEqual(ok["declared_routes"][CORE],"EA_SCRIPT")

    def test_agent_cannot_self_certify_ea_gameplay(self):
        with self.assertRaisesRegex(NativeGameplayError,"NATIVE_ROUTE_CANNOT_SELF_CERTIFY"):
            validate_route_decisions(CONTRACT,[CORE],[decision(
                CORE,"EA_TUNING",game_effect_claim="GAME_CERTIFIED")])

    def test_host_lab_may_support_test_but_not_gameplay_engine(self):
        ok=validate_route_decisions(CONTRACT,[HOST],[decision(HOST,"HOST_LAB_ONLY")])
        self.assertEqual(ok["declared_routes"][HOST],"HOST_LAB_ONLY")
        with self.assertRaisesRegex(NativeGameplayError,"HOST_LAB_AS_AUTONOMY_RUNTIME"):
            validate_route_decisions(CONTRACT,[HOST],[decision(HOST,"HOST_LAB_ONLY",
                                                                 autonomy_runtime=True)])

    def test_decisions_must_bind_exact_changed_file_once(self):
        with self.assertRaisesRegex(NativeGameplayError,"NATIVE_DECISION_DUPLICATE"):
            validate_route_decisions(CONTRACT,[CORE],[decision(CORE),decision(CORE)])
        with self.assertRaisesRegex(NativeGameplayError,"NATIVE_DECISION_PATH_UNRELATED"):
            validate_route_decisions(CONTRACT,[CORE],[decision("../outside.py")])
        with self.assertRaisesRegex(NativeGameplayError,"NATIVE_DECISION_PATH_UNRELATED"):
            validate_route_decisions(CONTRACT,[CORE],[decision(HOST)])
        with self.assertRaisesRegex(NativeGameplayError,"NATIVE_ROUTE_REASON_MISSING"):
            validate_route_decisions(CONTRACT,[CORE],[decision(CORE,reason="none")])

    def test_native_mod_source_paths_are_always_native(self):
        path="tuning/hunger.xml"
        with self.assertRaisesRegex(NativeGameplayError,"NATIVE_MOD_PATH_REQUIRES_EA_ROUTE"):
            validate_route_decisions(CONTRACT,[path],[decision(path,"POLICY_ONLY")])
        self.assertEqual(validate_route_decisions(CONTRACT,[path],
                         [decision(path,"EA_TUNING")])["changed_product_files"],1)


if __name__=="__main__":
    unittest.main()
