import ast
import ctypes
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from scripts import game_capture


class CaptureOwnershipTests(unittest.TestCase):
    def test_minimized_game_yields_without_restoring_or_capturing(self):
        class User32:
            def IsWindowVisible(self, hwnd): return True
            def GetWindowTextLengthW(self, hwnd): return 6
            def GetWindowTextW(self, hwnd, buf, size): buf.value = 'Sims 4'
            def GetWindowThreadProcessId(self, hwnd, pid): pid._obj.value = 123
            def EnumWindows(self, callback, unused): callback(42, 0)
            def IsIconic(self, hwnd): return True

        # Any restore, input, focus or bitmap call is absent from this fake:
        # attempting one fails rather than hiding desktop interference.
        dlls = SimpleNamespace(user32=User32(), gdi32=object())
        with patch.object(game_capture.sys, 'platform', 'win32'), \
             patch.object(ctypes, 'windll', dlls, create=True), \
             patch.object(ctypes, 'WINFUNCTYPE', lambda *args: lambda f: f, create=True):
            with self.assertRaisesRegex(game_capture.GateError, 'SIMS_MINIMIZED_OPERATOR_RESTORE_REQUIRED'):
                game_capture.capture_sims(process_id=123, out=Path('unused.png'))

    def test_capture_has_no_desktop_control_or_preference_mutations(self):
        tree = ast.parse(Path(game_capture.__file__).read_text(encoding='utf-8'))
        forbidden = {'ShowWindow', 'SetForegroundWindow', 'AllowSetForegroundWindow',
                     'AttachThreadInput', 'PostMessageW', 'SendInput', 'keybd_event',
                     'BlockInput', 'ClipCursor', 'SetValueEx', 'SetValue'}
        calls = {n.func.attr for n in ast.walk(tree)
                 if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)}
        self.assertEqual(calls & forbidden, set())


if __name__ == '__main__':
    unittest.main()
