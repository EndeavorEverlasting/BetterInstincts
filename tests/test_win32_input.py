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

    def test_send_click_parks_safe_rest_after(self):
        import ctypes
        from ctypes import Structure, c_ulong, c_void_p, POINTER, Union

        class MOUSEINPUT(Structure):
            _fields_ = [
                ("dx", c_ulong),
                ("dy", c_ulong),
                ("mouseData", c_ulong),
                ("dwFlags", c_ulong),
                ("time", c_ulong),
                ("dwExtraInfo", c_void_p),
            ]

        class _INPUTunion(Union):
            _fields_ = [("mi", MOUSEINPUT)]

        class INPUT(Structure):
            _fields_ = [("type", c_ulong), ("_input", _INPUTunion)]

            @property
            def mi(self):
                return self._input.mi

            @mi.setter
            def mi(self, value):
                self._input.mi = value

        class FakeUser32:
            def SetCursorPos(self, x, y):
                return 1

            def SendInput(self, *_a, **_k):
                return 1

        with patch.object(win32_input.sys, "platform", "win32"), patch(
            "scripts.win32_input._mouse_input_types", return_value=(ctypes, MOUSEINPUT, INPUT)
        ), patch("ctypes.windll.user32", FakeUser32()), patch(
            "scripts.win32_input.time.sleep", return_value=None
        ), patch(
            "scripts.win32_input.park_safe_cursor_rest", return_value={"state": "SAFE_CURSOR_REST"}
        ) as park:
            win32_input.send_click(400, 20, settle_sec=0, between_sec=0, safe_rest_after=True)
            park.assert_called_once()
            win32_input.send_click(400, 20, settle_sec=0, between_sec=0, safe_rest_after=False)
            self.assertEqual(park.call_count, 1)

    def test_move_cursor_edge_redirects_to_safe_rest(self):
        with patch.object(win32_input.sys, "platform", "win32"), patch(
            "scripts.win32_input.park_safe_cursor_rest", return_value={"state": "SAFE_CURSOR_REST"}
        ) as park, patch("ctypes.windll.user32.SetCursorPos") as setpos, patch(
            "scripts.win32_input.time.sleep", return_value=None
        ):
            win32_input.move_cursor(5, 540)
            park.assert_called_once()
            setpos.assert_not_called()

    def test_non_windows_send_key_chord_fails_closed(self):
        with patch.object(win32_input.sys, "platform", "linux"):
            with self.assertRaises(win32_input.Win32InputError) as ctx:
                win32_input.send_key_chord(["F3"])
        self.assertEqual(str(ctx.exception), "LOCAL_WINDOWS_GAME_HOST_REQUIRED")

    def test_resolve_vk_aliases(self):
        self.assertEqual(win32_input.resolve_vk("F3"), 0x72)
        self.assertEqual(win32_input.resolve_vk("CTRL"), 0x11)
        self.assertEqual(win32_input.resolve_vk("Z"), ord("Z"))
        with self.assertRaises(win32_input.Win32InputError):
            win32_input.resolve_vk("NOT_A_KEY")


if __name__ == "__main__":
    unittest.main()
