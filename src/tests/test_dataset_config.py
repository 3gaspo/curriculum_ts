"""Dataset config precedence and replacement exclusion checks."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from data.load import _merge_dataset_config


class DatasetConfigTest(unittest.TestCase):
    def test_scoped_and_run_values_replace_defaults(self):
        with tempfile.TemporaryDirectory() as folder:
            config_path = Path(folder) / "config.json"
            config_path.write_text(
                json.dumps(
                    {
                        "drop_users": [1],
                        "target_cols": ["shared"],
                        "curriculum_learning": {
                            "drop_users": [2],
                            "target_cols": ["scoped"],
                        },
                    }
                ),
                encoding="utf-8",
            )
            merged, provenance = _merge_dataset_config(
                {
                    "config_path": str(config_path),
                    "drop_users": [3],
                    "target_cols": ["explicit"],
                }
            )
        self.assertEqual(merged["drop_users"], [3])
        self.assertEqual(merged["target_cols"], ["explicit"])
        self.assertEqual(provenance["selected_path"], str(config_path))
        self.assertIn("target_cols", provenance["applied_keys"])


if __name__ == "__main__":
    unittest.main()
