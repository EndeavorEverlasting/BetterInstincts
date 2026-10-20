import unittest
from scripts.check_tracked_assets import forbidden

class AssetSafetyTests(unittest.TestCase):
    def test_forbid_saves_compiled_mods_game_folders(self):
        paths = ("Mods/BetterInstincts/a.package", "saves/slot.save",
                 "dist/release.zip", "x.ts4script", "localthumbcache.package")
        self.assertEqual(set(forbidden(paths)), set(paths))
    def test_allow_project_sources(self):
        self.assertEqual(forbidden(("docs/LEDGER.md", "betterinstincts/priority.py",
                                    "tests/test_priority.py", "src/tuning/example.xml")), [])

if __name__ == "__main__":
    unittest.main()
