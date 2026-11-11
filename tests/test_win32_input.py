"""P124 characterization: shared Win32 mouse/keyboard primitives stay script-owned."""
from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import win32_input
from scripts import needs_force
from scripts import host_menu
from scripts import menu_blockers
from scripts import funds_inject
from scripts import viewport_recover


class Win32InputOwnershipTests(unittest.TestCase):
    def test_adapters_delegate_left_click_to_shared_owner(self):
        self.assertIs(needs_force._send_click, win32_input.send_click)
        self.assertIs(host_menu._send_click, win32_input.send_click)
        self.assertIs(viewport_recover._send_wheel, win32_input.send_wheel)
        self.assertIs(viewport_recover._right_drag, win32_input.right_drag)
        # Thin timing wrappers remain local; they must call the shared owner.
        self.assertTrue(callable(menu_blockers._send_click))
        self.assertTrue(callable(funds_inject._click))

    def test_viewport_prefers_hotkeys_for_mode_transitions(self):
        self.assertEqual(viewport_recover.HOTKEY_BUILD, ("F3",))
        self.assertEqual(viewport_recover.HOTKEY_LIVE, ("F1",))
        # Mouse HUD coords remain documented fallbacks, not the preferred channel.
        self.assertEqual(viewport_recover.HUD_BUILD, (1505, 22))
        self.assertEqual(viewport_recover.HUD_LIVE_FROM_BUILD, (1585, 35))

    def test_funds_inject_delegates_keyboard_to_shared_owner(self):
        src = Path(funds_inject.__file__).read_text(encoding="utf-8")
        self.assertIn("from scripts.win32_input import send_vk", src)
        self.assertIn("from scripts.win32_input import type_text", src)
        self.assertNotIn("class KEYBDINPUT", src)

    def test_non_windows_send_click_fails_closed(self):
        with patch.object(win32_input.sys, "platform", "linux"):
            with self.assertRaises(win32_input.Win32InputError) as ctx:
                win32_input.send_click(1, 2)
        self.assertEqual(str(ctx.exception), "LOCAL_WINDOWS_GAME_HOST_REQUIRED")

    def test_left_drag_fails_closed_off_windows(self):
        self.assertTrue(callable(win32_input.left_drag))
        with patch.object(win32_input.sys, "platform", "linux"):
            with self.assertRaises(win32_input.Win32InputError) as ctx:
                win32_input.left_drag(1722, 810, 1722, 225)
        self.assertEqual(str(ctx.exception), "LOCAL_WINDOWS_GAME_HOST_REQUIRED")

    def test_send_click_parks_safe_rest_after(self):
        from unittest.mock import MagicMock

        class MOUSEINPUT:
            def __init__(self, *a, **k):
                pass

        class INPUT:
            def __init__(self, type=0):
                self.type = type
                self.mi = None

        fake_ctypes = MagicMock()
        fake_ctypes.windll.user32.SetCursorPos.return_value = 1
        fake_ctypes.windll.user32.SendInput.return_value = 1
        fake_ctypes.byref.side_effect = lambda x: x
        fake_ctypes.sizeof.return_value = 1

        with patch.object(win32_input.sys, "platform", "win32"), patch(
            "scripts.win32_input._mouse_input_types",
            return_value=(fake_ctypes, MOUSEINPUT, INPUT),
        ), patch("scripts.win32_input.time.sleep", return_value=None), patch(
            "scripts.win32_input.park_safe_cursor_rest",
            return_value={"state": "SAFE_CURSOR_REST"},
        ) as park:
            win32_input.send_click(400, 20, settle_sec=0, between_sec=0, safe_rest_after=True)
            park.assert_called_once()
            win32_input.send_click(400, 20, settle_sec=0, between_sec=0, safe_rest_after=False)
            self.assertEqual(park.call_count, 1)

    def test_right_click_uses_shared_flags_and_safe_rest(self):
        from unittest.mock import MagicMock
        class MOUSEINPUT:
            def __init__(self, _dx, _dy, _wheel, flags, _time, _extra):
                self.flags = flags
        class INPUT:
            def __init__(self, type=0):
                self.type = type
                self.mi = None
        fake = MagicMock()
        captured = []
        fake.byref.side_effect = lambda x: x
        fake.sizeof.return_value = 1
        fake.windll.user32.SendInput.side_effect = lambda count, inp, size: captured.append(inp.mi.flags)
        with (
            patch.object(win32_input.sys, "platform", "win32"),
            patch("scripts.win32_input._mouse_input_types", return_value=(fake,MOUSEINPUT,INPUT)),
            patch("scripts.win32_input.time.sleep"),
            patch("scripts.win32_input.park_safe_cursor_rest") as park,
        ):
            win32_input.send_right_click(300,800,settle_sec=0,between_sec=0)
            self.assertEqual(captured,[8,16])
            park.assert_called_once()

    def test_nonwindows_right_click_fails_closed(self):
        with patch.object(win32_input.sys, "platform", "linux"):
            with self.assertRaises(win32_input.Win32InputError):
                win32_input.send_right_click(300,800)

    def test_move_cursor_edge_redirects_to_safe_rest(self):
        with patch.object(win32_input.sys, "platform", "win32"), patch(
            "betterinstincts.camera_traverse.classify_cursor",
            return_value={
                "in_edge_band": True,
                "zone": "EDGE_BAND",
                "practice": "EDGE_MOUSE_PARK",
            },
        ), patch(
            "scripts.win32_input.park_safe_cursor_rest",
            return_value={"state": "SAFE_CURSOR_REST"},
        ) as park, patch("scripts.win32_input.time.sleep", return_value=None):
            win32_input.move_cursor(5, 540)
            park.assert_called_once()

    def test_non_windows_send_key_chord_fails_closed(self):
        with patch.object(win32_input.sys, "platform", "linux"):
            with self.assertRaises(win32_input.Win32InputError) as ctx:
                win32_input.send_key_chord(["F3"])
        self.assertEqual(str(ctx.exception), "LOCAL_WINDOWS_GAME_HOST_REQUIRED")

    def test_interrupted_keybd_chord_releases_ctrl_and_u_in_reverse(self):
        import ctypes
        from types import SimpleNamespace

        calls = []
        pauses = 0

        def record_key(vk, _scan, flag, _extra):
            calls.append((vk, flag))

        def interrupt_second_delay(_seconds):
            nonlocal pauses
            pauses += 1
            if pauses == 2:
                raise RuntimeError("SIMULATED_HUMAN_INTERRUPT")

        fake = SimpleNamespace(user32=SimpleNamespace(keybd_event=record_key))
        with (
            patch.object(win32_input.sys, "platform", "win32"),
            patch.object(ctypes, "windll", fake, create=True),
            patch("scripts.win32_input.time.sleep", side_effect=interrupt_second_delay),
        ):
            with self.assertRaisesRegex(RuntimeError, "SIMULATED_HUMAN_INTERRUPT"):
                win32_input.send_key_chord(["CTRL", "U"], via="keybd_event")
        self.assertEqual(
            calls,
            [(0x11, 0), (ord("U"), 0), (ord("U"), 2), (0x11, 2)],
        )

    def test_interrupted_sendinput_chord_releases_escape(self):
        calls = []

        def record_vk(vk, *, up=False):
            calls.append((vk, up))

        with (
            patch.object(win32_input.sys, "platform", "win32"),
            patch("scripts.win32_input.send_vk", side_effect=record_vk),
            patch("scripts.win32_input.time.sleep", side_effect=[RuntimeError("ABORTED"), None]),
        ):
            with self.assertRaisesRegex(RuntimeError, "ABORTED"):
                win32_input.send_key_chord(["ESC"], via="sendinput")
        self.assertEqual(calls, [(0x1B, False), (0x1B, True)])

    def test_key_release_failure_attempts_other_modifier_release(self):
        import ctypes
        from types import SimpleNamespace

        calls = []

        def fake_keybd(vk, _scan, flag, _extra):
            calls.append((vk, flag))
            if vk == ord("U") and flag == 2:
                raise RuntimeError("KEYUP_FAILED")

        fake = SimpleNamespace(user32=SimpleNamespace(keybd_event=fake_keybd))
        with (
            patch.object(win32_input.sys, "platform", "win32"),
            patch.object(ctypes, "windll", fake, create=True),
            patch("scripts.win32_input.time.sleep"),
        ):
            with self.assertRaisesRegex(win32_input.Win32InputError, "SYNTHETIC_KEY_RELEASE_UNCONFIRMED"):
                win32_input.send_key_chord(["CTRL", "U"])
        self.assertEqual(calls[-2:], [(ord("U"), 2), (0x11, 2)])

    def test_resolve_vk_aliases(self):
        self.assertEqual(win32_input.resolve_vk("F3"), 0x72)
        self.assertEqual(win32_input.resolve_vk("CTRL"), 0x11)
        self.assertEqual(win32_input.resolve_vk("Z"), ord("Z"))
        with self.assertRaises(win32_input.Win32InputError):
            win32_input.resolve_vk("NOT_A_KEY")


if __name__ == "__main__":
    unittest.main()
