"""P124 characterization: shared Win32 mouse primitives stay script-owned."""
from __future__ import annotations

import unittest
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

    def test_non_windows_send_click_fails_closed(self):
        with patch.object(win32_input.sys, "platform", "linux"):
            with self.assertRaises(win32_input.Win32InputError) as ctx:
                win32_input.send_click(1, 2)
        self.assertEqual(str(ctx.exception), "LOCAL_WINDOWS_GAME_HOST_REQUIRED")


if __name__ == "__main__":
    unittest.main()
