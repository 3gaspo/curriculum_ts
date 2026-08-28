"""Dependency-light aggregation check for seed result tables."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from pipeline.runs import allocate_run, mark_status
from scripts.summarize import aggregate_results, collect_results


def _write_run(root: Path, lookback: int, horizon: int, values: dict[int, float]) -> None:
    identity = root / "electricity" / f"{lookback}_{horizon}" / "dlinear" / "uniform"
    allocation = allocate_run(
        identity,
        project="curriculum_learning",
        workflow="curriculum",
        dataset="electricity",
        lookback=lookback,
        horizon=horizon,
        backbone="dlinear",
        model_config_order=["method"],
        model_config={"method": "uniform"},
        pipeline_config={},
        seeds=list(values),
        display_name="uniform",
    )
    artifacts = []
    for seed, value in values.items():
        relative = f"seed_{seed}/results.json"
        path = allocation.run_dir / relative
        path.parent.mkdir(parents=True)
        path.write_text(
            json.dumps(
                {
                    "dataset": "electricity",
                    "model": "dlinear",
                    "method": "uniform",
                    "seed": seed,
                    "task": {"lags": lookback, "horizon": horizon},
                    "metrics": {"test1": {"mse": value}},
                    "difficulty_quantiles": {},
                }
            ),
            encoding="utf-8",
        )
        mark_status(allocation.run_dir, "completed", seed=seed, required_artifacts=[relative])
        artifacts.append(relative)
    mark_status(allocation.run_dir, "completed", required_artifacts=artifacts)


class SummaryTest(unittest.TestCase):
    def test_seed_metrics_are_aggregated(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            _write_run(root, 168, 24, {1: 2.0, 2: 4.0})
            paths = aggregate_results(root)
            metrics, _ = collect_results(root)
            self.assertEqual(len(metrics), 2)
            summary = json.loads(paths["summary_json"].read_text(encoding="utf-8"))
            self.assertEqual(summary[0]["mean"], 3.0)
            self.assertEqual(summary[0]["count"], 2)
            self.assertTrue(paths["summary_latex"].exists())

    def test_single_seed_has_no_fictitious_standard_deviation(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            _write_run(root, 504, 168, {1: 2.0})
            paths = aggregate_results(root)
            summary = json.loads(paths["summary_json"].read_text(encoding="utf-8"))
            self.assertEqual(summary[0]["mean_std"], "2")
            self.assertIsNone(summary[0]["std"])
            latex = paths["summary_latex"].read_text(encoding="utf-8")
            self.assertNotIn("±", latex)
            self.assertNotIn("nan", latex.casefold())
            self.assertIn("--", latex)


if __name__ == "__main__":
    unittest.main()
