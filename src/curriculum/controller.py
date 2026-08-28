"""Apply curriculum plans to a TimeTensors training dataset."""

from __future__ import annotations

import logging
from collections import Counter
from typing import Any, Mapping, Sequence

import torch

from .schedule import CurriculumPlan


class CurriculumController:
    def __init__(
        self,
        dataset: Any,
        plan: CurriculumPlan,
        records: Sequence[Mapping[str, Any]],
        *,
        samples_per_step: int,
        logger: logging.Logger | None = None,
    ):
        if not hasattr(dataset, "set_sampler"):
            raise TypeError("curriculum training requires a TimeSeriesDataset")
        self.dataset = dataset
        self.plan = plan
        self.records = [dict(record) for record in records]
        self.logger = logger
        self.samples_per_step = int(samples_per_step)
        if self.samples_per_step < 1:
            raise ValueError("samples_per_step must be positive")
        self.current_phase: int | None = None
        self.events: list[dict[str, Any]] = []
        self.actual_exposures: Counter[int] = Counter()
        self._source_ids = {
            int(record["local_index"]): int(record["source_id"])
            for record in self.records
        }

    def before_step(self, step: int) -> dict[str, Any] | None:
        phase = self.plan.phase_at(step)
        if phase.index == self.current_phase:
            return None
        weights = (
            None
            if self.plan.sampling_weights is None
            else list(self.plan.sampling_weights)
        )
        self.dataset.set_sampler(
            idx_mode="random",
            subset_mode="individuals",
            subset_indices=list(phase.active_local_indices),
            individual_weights=weights,
            block_individuals=1,
            weight=self.samples_per_step,
        )
        self.current_phase = phase.index
        event = {
            "phase": phase.index,
            "start_step": int(step),
            "end_step": phase.end_step,
            "active_local_indices": list(phase.active_local_indices),
            "active_source_ids": [
                self._source_ids[index] for index in phase.active_local_indices
            ],
        }
        self.events.append(event)
        if self.logger is not None:
            self.logger.info(
                "curriculum phase=%s steps=[%s,%s) active_users=%s/%s source_ids=%s",
                phase.index,
                step,
                phase.end_step,
                len(phase.active_local_indices),
                len(self.records),
                event["active_source_ids"],
            )
        return event

    def after_batch(self, batch: Mapping[str, Any]) -> None:
        metadata = batch.get("metadata", {})
        ids = metadata.get("individual_ids")
        if ids is None:
            return
        values = ids.detach().cpu().tolist() if torch.is_tensor(ids) else list(ids)
        self.actual_exposures.update(int(value) for value in values)

    def provenance(self) -> dict[str, Any]:
        total = sum(self.actual_exposures.values())
        return {
            "events": self.events,
            "actual_exposure_counts": {
                str(source_id): int(self.actual_exposures.get(source_id, 0))
                for source_id in sorted(self._source_ids.values())
            },
            "actual_exposure_probabilities": {
                str(source_id): (
                    0.0
                    if total == 0
                    else self.actual_exposures.get(source_id, 0) / total
                )
                for source_id in sorted(self._source_ids.values())
            },
            "actual_samples": total,
        }
