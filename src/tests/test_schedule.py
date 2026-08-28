"""Dependency-light checks for curriculum schedule semantics."""

from __future__ import annotations

import unittest

from curriculum.schedule import build_curriculum_plan


def records(count: int = 5):
    return [
        {
            "local_index": index,
            "source_id": 100 + index,
            "name": f"user_{index}",
            "score": float(index),
        }
        for index in range(count)
    ]


class CurriculumScheduleTest(unittest.TestCase):
    def test_easy_to_hard_is_cumulative(self):
        plan = build_curriculum_plan(
            records(),
            method="easy_to_hard",
            steps=500,
            phases=5,
            initial_fraction=0.2,
        )
        self.assertEqual(
            [len(phase.active_local_indices) for phase in plan.phases],
            [1, 2, 3, 4, 5],
        )
        for earlier, later in zip(plan.phases, plan.phases[1:]):
            self.assertTrue(
                set(earlier.active_local_indices)
                <= set(later.active_local_indices)
            )
        self.assertAlmostEqual(sum(plan.expected_exposure), 1.0)

    def test_exposure_match_preserves_marginals_without_ordering(self):
        progressive = build_curriculum_plan(
            records(),
            method="easy_to_hard",
            steps=500,
            phases=5,
            initial_fraction=0.2,
        )
        matched = build_curriculum_plan(
            records(),
            method="exposure_matched",
            steps=500,
            phases=5,
            initial_fraction=0.2,
        )
        self.assertEqual(progressive.expected_exposure, matched.sampling_weights)
        self.assertEqual(progressive.expected_exposure, matched.expected_exposure)
        self.assertEqual(
            matched.phases[0].active_local_indices,
            (0, 1, 2, 3, 4),
        )
        self.assertEqual(len(matched.phases), 1)
        self.assertGreater(matched.sampling_weights[0], matched.sampling_weights[-1])

    def test_controls_are_deterministic(self):
        tied = records(3)
        tied[0]["score"] = tied[1]["score"] = 1.0
        easy = build_curriculum_plan(
            tied,
            method="easy_to_hard",
            steps=9,
            phases=3,
            seed=7,
        )
        self.assertEqual(easy.ordered_local_indices[:2], (0, 1))
        random_a = build_curriculum_plan(
            tied,
            method="random_order",
            steps=9,
            phases=3,
            seed=7,
        )
        random_b = build_curriculum_plan(
            tied,
            method="random_order",
            steps=9,
            phases=3,
            seed=7,
        )
        self.assertEqual(random_a.ordered_local_indices, random_b.ordered_local_indices)


if __name__ == "__main__":
    unittest.main()
