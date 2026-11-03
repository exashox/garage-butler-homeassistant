"""VERSION, manifest.json and CHANGELOG.md agree: python -m unittest discover tests"""

import json
from pathlib import Path
import unittest

ROOT = Path(__file__).parents[1]


class VersionTest(unittest.TestCase):
    def test_versions_agree(self):
        version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
        manifest = json.loads(
            (ROOT / "custom_components" / "garagebutler" / "manifest.json").read_text(encoding="utf-8")
        )
        changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        self.assertEqual(manifest["version"], version)
        self.assertIn(f"## [{version}]", changelog)
        self.assertIn("## [Unveröffentlicht]", changelog)


if __name__ == "__main__":
    unittest.main()
