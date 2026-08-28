"""Tiny synthetic end-to-end curriculum run for a prepared project environment."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from scripts.experiment import run_experiment


class CurriculumSmokeTest(unittest.TestCase):
    def test_dlinear_exposure_matched_run(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            dataset_dir = root / "synthetic"
            dataset_dir.mkdir()
            dates = pd.date_range("2025-01-01", periods=80, freq="h")
            rng = np.random.default_rng(4)
            frame = pd.DataFrame(
                {
                    f"user_{index}": np.sin(np.arange(80) / (4 + index))
                    + 0.02 * (index + 1) * rng.normal(size=80)
                    for index in range(4)
                },
                index=dates,
            )
            frame.to_csv(dataset_dir / "synthetic.csv")
            config = {
                "data": {
                    "raw_path": str(dataset_dir),
                    "name": "synthetic",
                    "config_path": None,
                    "drop_users": None,
                    "target_cols": None,
                    "splits": {
                        "date_splits": [0.6, 0.2, 0.2],
                        "indiv_split": 1.0,
                    },
                    "sampling": {
                        "train_idx_mode": "random",
                        "eval_idx_mode": "all",
                        "train_stride": 1,
                        "eval_stride": 2,
                        "shuffle_train": True,
                        "shuffle_eval": False,
                        "drop_train_constant_individuals": False,
                        "drop_eval_constant_individuals": False,
                        "train_block_individuals": 1,
                        "eval_block_individuals": 1,
                    },
                },
                "task": {"lags": 8, "horizon": 2},
                "model": {"name": "dlinear", "path": "dlinear", "kwargs": {}},
                "normalization": {
                    "name": "instance",
                    "kwargs": {"affine": False},
                },
                "training": {
                    "batch_size": 4,
                    "steps": 5,
                    "lr": 1e-4,
                    "loss": "nmse",
                    "device": "cpu",
                    "valid_eval_freq": 5,
                    "logging_eval_freq": 5,
                    "plot_step_train_loss": False,
                },
                "curriculum": {
                    "method": "exposure_matched",
                    "quantiles": 2,
                    "difficulty": {
                        "name": "persistence_nmse",
                        "stride": 2,
                        "aggregation": "median",
                    },
                    "schedule": {
                        "phases": 2,
                        "initial_fraction": 0.5,
                        "pacing": "linear",
                    },
                },
                "evaluation": {"splits": None, "runs": 1},
                "experiment": {
                    "seed": 1,
                    "seeds": None,
                    "prepare_loaders": True,
                    "recompute_stats": False,
                },
                "output": {
                    "dir": str(root / "outputs"),
                    "name": "dlinear/exposure_matched",
                },
                "misc": {"log_level": "WARNING"},
            }
            result = run_experiment(config)
            run_dir = root / "outputs" / "dlinear" / "exposure_matched"
            self.assertEqual(result["training"]["optimizer_steps"], 5)
            self.assertEqual(
                result["curriculum"]["realized"]["actual_samples"],
                20,
            )
            self.assertTrue((run_dir / "results.json").exists())
            self.assertTrue((run_dir / "difficulty.json").exists())
            self.assertFalse((dataset_dir / "values.pt").exists())


if __name__ == "__main__":
    unittest.main()
