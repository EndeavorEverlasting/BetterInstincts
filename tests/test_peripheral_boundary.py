"""Regression cases for the Sims/Windows peripheral ownership boundary."""
import json
from pathlib import Path
import tempfile
import unittest

from scripts.check_peripheral_boundary import inspect_repository, inspect_source

ROOT = Path(__file__).resolve().parents[1]


class PeripheralBoundaryTests(unittest.TestCase):
    def test_deny_known_service_driver_and_preference_controls(self):
        examples = {
            "OS_SERVICE_CONTROL": ["Start-Service bthserv", "sc.exe config bthserv start= auto",
                                   "BluetoothUserService_abc"],
            "OS_PNP_MUTATION": ["pnputil.exe /restart-device USB\\RADIO",
                                "Disable-PnpDevice -InstanceId ID"],
            "OS_PERIPHERAL_PREFERENCE": ["PrintScreenKeyForSnippingEnabled",
                                         "BlockInput(True)"],
        }
        for reason, cases in examples.items():
            for case in cases:
                with self.subTest(case=case):
                    self.assertIn(reason, inspect_source(case))

    def test_protect_screenshot_escape_u_and_global_input_channels(self):
        examples = {
            "OS_KEYBOARD_REMAP_OR_ACCESSIBILITY": [
                "Scancode Map", "SetKeyboardState(...)", "SystemParametersInfoW(...)",
                "FilterKeys enabled", "Keyboard Layout\\\\Scancode",
            ],
            "OS_GLOBAL_INPUT_INTERCEPTION": [
                "SetWindowsHookExW(...)", "RegisterHotKey(hwnd, U)",
            ],
            "OS_REGISTRY_MUTATION": [
                "reg.exe add HKCU\\\\Software", "Set-ItemProperty -Path HKCU:",
                "winreg.SetValueEx(key, name, 0, type, data)",
            ],
        }
        for reason, cases in examples.items():
            for code in cases:
                with self.subTest(code=code):
                    self.assertIn(reason, inspect_source(code))

    def test_allow_game_observation_and_readonly_service_language(self):
        self.assertEqual(inspect_source("passive PrintWindow; Get-Service bthserv; idle probe"), ())

    def test_scan_catches_new_adapter_outside_the_existing_capture_path(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "betterinstincts").mkdir()
            (root / "scripts").mkdir()
            (root / "scripts" / "new_adapter.py").write_text(
                "import subprocess\nsubprocess.run('pnputil.exe /remove-device ID')\n",
                encoding="utf-8",
            )
            self.assertIn(("scripts/new_adapter.py", "OS_PNP_MUTATION"), inspect_repository(root))

    def test_contract_explicitly_denies_windows_repairs(self):
        authority = json.loads((ROOT / "contracts/peripheral-authority.v1.json").read_text(encoding="utf-8"))
        self.assertEqual(authority["unknown_effect"], "DENY_UNTIL_CLASSIFIED")
        for effect in ("OS_BLUETOOTH_SERVICE", "OS_DRIVER_OR_ADAPTER", "OS_INPUT_PREFERENCE"):
            self.assertTrue(authority["effect_classes"][effect]["decision"].startswith("DENY"))

    def test_ontology_graph_owns_windows_peripheral_authority(self):
        graph = json.loads((ROOT / "contracts/ontology.v1.json").read_text(encoding="utf-8"))
        concept = graph["concepts"]["OS_PERIPHERAL_AUTHORITY"]
        self.assertEqual(concept["canonical_owner"], "contracts/peripheral-authority.v1.json")
        self.assertIn({"from": "CONTROL_PERMIT",
                       "predicate": "DOES_NOT_GRANT_OS_REPAIR_AUTHORITY",
                       "to": "OS_PERIPHERAL_AUTHORITY"}, graph["relations"])
        invariants = {x["id"]: x for x in graph["invariants"]}
        self.assertEqual(invariants["BI-ONT-025"]["term"],
                         "GAME_AGENT_MUST_NOT_MUTATE_WINDOWS_PERIPHERALS")

    def test_repository_source_boundary(self):
        self.assertEqual(inspect_repository(ROOT), [], "Game source must not operate Bluetooth/driver/preferences")


    def test_pairing_and_failsafe_controls_cannot_be_game_recovery(self):
        for code, reason in (
            ("await mouse.PairAsync()", "OS_BLUETOOTH_PAIRING"),
            ("BluetoothRemoveDevice(address)", "OS_BLUETOOTH_PAIRING"),
            ("thing.UnpairAsync()", "OS_BLUETOOTH_PAIRING"),
            ("BluetoothSetServiceState()", "OS_BLUETOOTH_PAIRING"),
            ("pyautogui.FAILSAFE = False", "OS_INPUT_FAILSAFE_DISABLED"),
            ("SetWindowsHookExW(...)", "OS_GLOBAL_INPUT_INTERCEPTION"),
        ):
            with self.subTest(code=code):
                self.assertIn(reason, inspect_source(code))
        self.assertEqual(inspect_source(
            "DeviceWatcher; BluetoothLEDevice.FromIdAsync(endpoint); "
            "appearance = 962; label = 'Mouse'; PrintWindow; Get-Service bthserv"
        ), ())

    def test_scans_root_launcher_cursor_hooks_workflows_and_future_tools(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for folder in ("betterinstincts", "scripts", ".cursor/hooks",
                           ".github/workflows", "newtools"):
                (root / folder).mkdir(parents=True)
            cases = (
                ("bootstrap.py", "Start-Service bthserv", "OS_SERVICE_CONTROL"),
                ("Start-BetterInstincts.cmd", "pnputil.exe /remove-device HID", "OS_PNP_MUTATION"),
                (".cursor/hooks/secondary.py", "UnpairAsync()", "OS_BLUETOOTH_PAIRING"),
                (".github/workflows/repair.yml", "run: sc.exe config bthserv start= disabled",
                 "OS_SERVICE_CONTROL"),
                ("newtools/remap.ps1", "Set-ItemProperty HKCU:", "OS_REGISTRY_MUTATION"),
            )
            for path, content, _ in cases:
                (root / path).write_text(content, encoding="utf-8")
            found = set(inspect_repository(root))
            for path, _, reason in cases:
                with self.subTest(path=path):
                    self.assertIn((path, reason), found)
            (root / "tests").mkdir()
            (root / "tests" / "malicious_fixture.py").write_text(
                "Start-Service bthserv", encoding="utf-8"
            )
            self.assertNotIn(("tests/malicious_fixture.py", "OS_SERVICE_CONTROL"),
                             set(inspect_repository(root)))

    def test_endpoints_are_not_self_authenticating_by_type_or_generic_name(self):
        authority = json.loads((ROOT / "contracts/peripheral-authority.v1.json").read_text(encoding="utf-8"))
        identity = authority["bluetooth_identity"]
        self.assertEqual(identity["early_appearance_mouse"], 962)
        self.assertFalse(identity["early_name_is_identity"])
        self.assertIn("UNKNOWN_TRANSITION", identity["transitions_to_preserve"])
        self.assertIn("MATCHED_HID_NODE", identity["compare_only_after"])
        self.assertEqual(authority["effect_classes"]["OS_BLUETOOTH_PAIRING"]["decision"],
                         "DENY_AND_REFER_SYSADMINSUITE")
        self.assertEqual(authority["cross_harness"]["runtime"],
                         "HOOK_EFFECTIVE_ONLY_WHEN_PROVIDER_HAS_LOADED_AND_REPORTED_DENY")

    def test_revision_nine_binds_perimeter_identity_and_independent_proofs(self):
        graph = json.loads((ROOT / "contracts/ontology.v1.json").read_text(encoding="utf-8"))
        self.assertGreaterEqual(graph["revision"], 9)
        for concept in ("PERIPHERAL_IDENTITY_EVIDENCE", "AGENT_EFFECT_PERIMETER"):
            self.assertIn(concept, graph["concepts"])
        ids = {row["id"] for row in graph["invariants"]}
        self.assertTrue({"BI-ONT-046", "BI-ONT-047", "BI-ONT-048"} <= ids)
        self.assertIn({"from": "CONTROL_PERMIT", "predicate": "CANNOT_BYPASS",
                       "to": "AGENT_EFFECT_PERIMETER"}, graph["relations"])


    def test_executable_powershell_modules_and_windows_script_host_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "betterinstincts").mkdir()
            (root / "scripts").mkdir()
            cases = (
                ("host_tools/mouse.psm1", "Stop-Service bthserv", "OS_SERVICE_CONTROL"),
                ("host_tools/driver.psd1", "pnputil.exe /remove-device HID", "OS_PNP_MUTATION"),
                ("host_tools/input.pyw", "gui.FAILSAFE = False", "OS_INPUT_FAILSAFE_DISABLED"),
                ("host_tools/repair.vbs", "BluetoothRemoveDevice(device)", "OS_BLUETOOTH_PAIRING"),
            )
            for path, content, _ in cases:
                dest = root / path
                dest.parent.mkdir(exist_ok=True)
                dest.write_text(content, encoding="utf-8")
            observed = set(inspect_repository(root))
            for path, _, reason in cases:
                with self.subTest(path=path):
                    self.assertIn((path, reason), observed)

    def test_all_aliased_pyautogui_failsafe_disables_are_denied(self):
        for source in (
            "import pyautogui as gui\ngui.FAILSAFE = False",
            "import pyautogui as pg\npg.FAILSAFE = False",
            "import pyautogui as pya\npya.FAILSAFE = 0",
            "setattr(gui, 'FAILSAFE', False)",
            'setattr(pg, "FAILSAFE", 0)',
        ):
            with self.subTest(source=source):
                self.assertIn("OS_INPUT_FAILSAFE_DISABLED", inspect_source(source))
        self.assertEqual(inspect_source("gui.FAILSAFE = True; gui.moveTo(10, 10)"), ())

if __name__ == "__main__":
    unittest.main()
