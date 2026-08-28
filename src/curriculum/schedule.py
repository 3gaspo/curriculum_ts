"""Deterministic user-level curriculum plans and exposure controls."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

import numpy as np


VALID_METHODS = {
    "uniform",
    "easy_to_hard",
    "hard_to_easy",
    "random_order",
    "exposure_matched",
}
VALID_PACING = {"linear", "sqrt", "quadratic"}


@dataclass(frozen=True)
class CurriculumPhase:
    index: int
    start_step: int
    end_step: int
    active_local_indices: tuple[int, ...]

    @property
    def duration(self) -> int:
        return self.end_step - self.start_step


@dataclass(frozen=True)
class CurriculumPlan:
    method: str
    steps: int
    ordered_local_indices: tuple[int, ...]
    phases: tuple[CurriculumPhase, ...]
    expected_exposure: tuple[float, ...]
    sampling_weights: tuple[float, ...] | None
    reference_phases: tuple[CurriculumPhase, ...] | None = None

    def phase_at(self, step: int) -> CurriculumPhase:
        if not 0 <= int(step) < self.steps:
            raise IndexError(f"step {step} is outside [0, {self.steps})")
        for phase in self.phases:
            if int(step) < phase.end_step:
                return phase
        return self.phases[-1]

    def to_dict(self, records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
        by_local = {int(record["local_index"]): dict(record) for record in records}

        def phase_dict(phase: CurriculumPhase) -> dict[str, Any]:
            return {
                "index": phase.index,
                "start_step": phase.start_step,
                "end_step": phase.end_step,
                "duration": phase.duration,
                "active_local_indices": list(phase.active_local_indices),
                "active_source_ids": [
                    int(by_local[index]["source_id"])
                    for index in phase.active_local_indices
                ],
            }

        return {
            "method": self.method,
            "steps": self.steps,
            "ordered_local_indices": list(self.ordered_local_indices),
            "ordered_source_ids": [
                int(by_local[index]["source_id"])
                for index in self.ordered_local_indices
            ],
            "ranking": [
                {
                    "rank": rank,
                    **by_local[index],
                    "expected_exposure_probability": self.expected_exposure[index],
                    "sampling_weight": (
                        None
                        if self.sampling_weights is None
                        else self.sampling_weights[index]
                    ),
                }
                for rank, index in enumerate(self.ordered_local_indices, start=1)
            ],
            "phases": [phase_dict(phase) for phase in self.phases],
            "reference_phases": (
                None
                if self.reference_phases is None
                else [phase_dict(phase) for phase in self.reference_phases]
            ),
        }


def _step_bounds(steps: int, phases: int) -> list[tuple[int, int]]:
    phases = min(int(phases), int(steps))
    base, remainder = divmod(int(steps), phases)
    bounds = []
    start = 0
    for index in range(phases):
        duration = base + (1 if index < remainder else 0)
        bounds.append((start, start + duration))
        start += duration
    return bounds


def _paced_progress(progress: float, pacing: str) -> float:
    if pacing == "linear":
        return progress
    if pacing == "sqrt":
        return math.sqrt(progress)
    if pacing == "quadratic":
        return progress * progress
    raise ValueError(f"unknown pacing {pacing!r}")


def _progressive_phases(
    order: Sequence[int],
    *,
    steps: int,
    phases: int,
    initial_fraction: float,
    pacing: str,
) -> tuple[CurriculumPhase, ...]:
    bounds = _step_bounds(steps, phases)
    initial_count = max(1, math.ceil(len(order) * float(initial_fraction)))
    result = []
    for index, (start, end) in enumerate(bounds):
        progress = 1.0 if len(bounds) == 1 else index / (len(bounds) - 1)
        revealed = _paced_progress(progress, pacing)
        active_count = math.ceil(
            initial_count + (len(order) - initial_count) * revealed
        )
        result.append(
            CurriculumPhase(
                index=index,
                start_step=start,
                end_step=end,
                active_local_indices=tuple(order[:active_count]),
            )
        )
    return tuple(result)


def _expected_exposure(
    phases: Sequence[CurriculumPhase],
    *,
    users: int,
    steps: int,
) -> tuple[float, ...]:
    exposure = np.zeros(users, dtype=float)
    for phase in phases:
        probability_mass = phase.duration / int(steps)
        per_user = probability_mass / len(phase.active_local_indices)
        exposure[list(phase.active_local_indices)] += per_user
    exposure /= exposure.sum()
    return tuple(float(value) for value in exposure)


def build_curriculum_plan(
    records: Sequence[Mapping[str, Any]],
    *,
    method: str,
    steps: int,
    phases: int = 5,
    initial_fraction: float = 0.2,
    pacing: str = "linear",
    seed: int | None = None,
) -> CurriculumPlan:
    """Build a curriculum from train-only difficulty records.

    ``exposure_matched`` uses the marginal user probabilities implied by the
    easy-to-hard reference curriculum but applies them throughout training.
    """
    method = str(method).lower()
    pacing = str(pacing).lower()
    if method not in VALID_METHODS:
        raise ValueError(f"unknown curriculum method {method!r}")
    if pacing not in VALID_PACING:
        raise ValueError(f"unknown pacing {pacing!r}")
    if int(steps) < 1 or int(phases) < 1:
        raise ValueError("steps and phases must be positive")
    if not 0 < float(initial_fraction) <= 1:
        raise ValueError("initial_fraction must be in (0, 1]")
    if not records:
        raise ValueError("difficulty records cannot be empty")

    local_indices = sorted(int(record["local_index"]) for record in records)
    if local_indices != list(range(len(records))):
        raise ValueError("difficulty local indices must be dense and zero-based")
    easy_order = [
        int(record["local_index"])
        for record in sorted(
            records,
            key=lambda record: (
                float(record["score"]),
                int(record["source_id"]),
            ),
        )
    ]
    if method == "hard_to_easy":
        order = [
            int(record["local_index"])
            for record in sorted(
                records,
                key=lambda record: (
                    -float(record["score"]),
                    int(record["source_id"]),
                ),
            )
        ]
    elif method == "random_order":
        order = np.random.default_rng(seed).permutation(local_indices).astype(int).tolist()
    else:
        order = easy_order

    if method == "uniform":
        all_users = tuple(local_indices)
        actual_phases = (
            CurriculumPhase(0, 0, int(steps), all_users),
        )
        expected = tuple(1.0 / len(local_indices) for _ in local_indices)
        return CurriculumPlan(
            method=method,
            steps=int(steps),
            ordered_local_indices=tuple(easy_order),
            phases=actual_phases,
            expected_exposure=expected,
            sampling_weights=None,
        )

    reference = _progressive_phases(
        easy_order,
        steps=int(steps),
        phases=int(phases),
        initial_fraction=float(initial_fraction),
        pacing=pacing,
    )
    if method == "exposure_matched":
        expected = _expected_exposure(
            reference,
            users=len(local_indices),
            steps=int(steps),
        )
        return CurriculumPlan(
            method=method,
            steps=int(steps),
            ordered_local_indices=tuple(easy_order),
            phases=(
                CurriculumPhase(0, 0, int(steps), tuple(local_indices)),
            ),
            expected_exposure=expected,
            sampling_weights=expected,
            reference_phases=reference,
        )

    actual_phases = _progressive_phases(
        order,
        steps=int(steps),
        phases=int(phases),
        initial_fraction=float(initial_fraction),
        pacing=pacing,
    )
    expected = _expected_exposure(
        actual_phases,
        users=len(local_indices),
        steps=int(steps),
    )
    return CurriculumPlan(
        method=method,
        steps=int(steps),
        ordered_local_indices=tuple(order),
        phases=actual_phases,
        expected_exposure=expected,
        sampling_weights=None,
    )
