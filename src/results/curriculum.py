"""JSON summaries for curriculum runs and difficulty quantiles."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

import torch


def _mean(value: Any) -> float:
    tensor = torch.as_tensor(value).float()
    return float(tensor.mean())


def summarize_losses(all_losses: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    return {
        split: {metric: _mean(value) for metric, value in metrics.items()}
        for split, metrics in all_losses.items()
    }


def _difficulty_groups(
    records: Sequence[Mapping[str, Any]],
    quantiles: int,
) -> list[list[int]]:
    ranked = [
        int(record["source_id"])
        for record in sorted(
            records,
            key=lambda record: (
                float(record["score"]),
                int(record["source_id"]),
            ),
        )
    ]
    groups = min(int(quantiles), len(ranked))
    base, remainder = divmod(len(ranked), groups)
    result = []
    start = 0
    for index in range(groups):
        size = base + (1 if index < remainder else 0)
        result.append(ranked[start : start + size])
        start += size
    return result


def summarize_difficulty_quantiles(
    per_user: Mapping[str, Mapping[str, Any]],
    records: Sequence[Mapping[str, Any]],
    *,
    quantiles: int = 5,
) -> dict[str, Any]:
    """Aggregate equal-user metrics from easiest to hardest ranked groups."""
    groups = _difficulty_groups(records, quantiles)
    output: dict[str, Any] = {}
    for split, split_payload in per_user.items():
        split_result: dict[str, Any] = {}
        for metric, user_values in (split_payload.get("losses") or {}).items():
            metric_result = {}
            for index, source_ids in enumerate(groups):
                values = [
                    _mean(user_values[str(source_id)])
                    for source_id in source_ids
                    if str(source_id) in user_values
                ]
                if not values:
                    continue
                label = (
                    f"q{index + 1}_easy"
                    if index == 0
                    else f"q{index + 1}_hard"
                    if index == len(groups) - 1
                    else f"q{index + 1}"
                )
                metric_result[label] = {
                    "mean": sum(values) / len(values),
                    "users": len(values),
                    "source_ids": [
                        source_id
                        for source_id in source_ids
                        if str(source_id) in user_values
                    ],
                }
            if metric_result:
                split_result[metric] = metric_result
        if split_result:
            output[split] = split_result
    return output


def save_json(payload: Mapping[str, Any], path: str | Path) -> Path:
    path = Path(path).expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False),
        encoding="utf-8",
    )
    return path


def history_summary(history: Mapping[str, Any]) -> dict[str, Any]:
    train = history.get("train") or []
    return {
        "optimizer_steps": int(history.get("optimizer_steps", len(train))),
        "elapsed_seconds": float(history.get("elapsed_seconds", math.nan)),
        "final_train_loss": None if not train else float(train[-1]),
        "intervals": len(history.get("train_batch") or []),
        "validation_points": {
            split: len(values)
            for split, values in (history.get("valid") or {}).items()
        },
    }
