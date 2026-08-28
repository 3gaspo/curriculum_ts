"""Focused Torch checks for difficulty ranking and weighted sampling."""

from __future__ import annotations

import unittest
from types import SimpleNamespace

import torch

from curriculum.difficulty import score_user_difficulty
from data import IndexSampler, SamplerConfig
from model_loading import RevIN, build_normalization


class DifficultyTest(unittest.TestCase):
    def test_revin_uses_canonical_type_name(self):
        normalization = build_normalization(
            {"name": "revin", "kwargs": {}},
            dim=1,
        )
        self.assertIsInstance(normalization, RevIN)

    def test_persistence_mse_ranks_train_users(self):
        values = torch.tensor(
            [
                [[0.0, 1.0, 2.0, 3.0, 4.0, 5.0]],
                [[0.0, 2.0, 4.0, 6.0, 8.0, 10.0]],
            ]
        )
        data = SimpleNamespace(
            values=values,
            individual_ids=torch.tensor([10, 20]),
            individual_names={10: "easy", 20: "hard"},
        )
        dataset = SimpleNamespace(
            data=data,
            lags=2,
            horizon=1,
            index_sampler=SimpleNamespace(base_date_candidates=[1, 2, 3, 4]),
        )
        scored = score_user_difficulty(
            dataset,
            name="persistence_mse",
            aggregation="median",
        )
        self.assertEqual([record["source_id"] for record in scored], [10, 20])
        self.assertLess(scored[0]["score"], scored[1]["score"])
        self.assertEqual(scored[0]["windows"], 4)


class WeightedSamplerTest(unittest.TestCase):
    def test_zero_weight_user_is_never_drawn(self):
        values = torch.arange(20, dtype=torch.float32).reshape(2, 1, 10)
        sampler = IndexSampler(
            values,
            lags=2,
            horizon=1,
            config=SamplerConfig(
                idx_mode="random",
                individual_weights=[1.0, 0.0],
            ),
        )
        draws = [sampler(0)[0][0] for _ in range(50)]
        self.assertEqual(set(draws), {0})


if __name__ == "__main__":
    unittest.main()
