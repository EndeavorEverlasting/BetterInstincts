import unittest
from scripts.compatibility_status import main

class CompatibilityStatusCLITests(unittest.TestCase):
    def test_no_certified_profiles_yields_nonzero_unknown(self):
        self.assertEqual(main(["--game-version","1.121.342.1030","--platform","windows","--module","hunger"]),3)
if __name__=="__main__":
    unittest.main()
