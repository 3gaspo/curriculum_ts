"""Train-only, model-independent user difficulty estimation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import torch


VALID_DIFFICULTIES = {"persistence_nmse", "persistence_mse"}
VALID_AGGREGATIONS = {"median", "mean"}


def score_user_difficulty(
    dataset: Any,
    *,
    name: str = "persistence_nmse",
    stride: int = 1,
    aggregation: str = "median",
    eps: float = 1e-8,
) -> list[dict[str, Any]]:
    """Score each local user over windows whose targets belong to train.

    Persistence repeats the last lookback value across the forecast horizon.
    nMSE divides errors by the population standard deviation of that lookback,
    matching the training loss convention.
    """
    name = str(name).lower()
    aggregation = str(aggregation).lower()
    if name not in VALID_DIFFICULTIES:
        raise ValueError(f"unknown difficulty score {name!r}")
    if aggregation not in VALID_AGGREGATIONS:
        raise ValueError(f"unknown difficulty aggregation {aggregation!r}")
    if int(stride) < 1:
        raise ValueError("difficulty stride must be positive")

    values = dataset.data.values.detach().cpu()
    lags = int(dataset.lags)
    horizon = int(dataset.horizon)
    query_dates = dataset.index_sampler.base_date_candidates[:: int(stride)]
    per_user: list[list[float]] = [[] for _ in range(values.shape[0])]

    for query_t in query_dates:
        lookback = values[..., query_t - lags + 1 : query_t + 1]
        target = values[..., query_t + 1 : query_t + horizon + 1]
        prediction = lookback[..., -1:].expand_as(target)
        errors = (target - prediction).pow(2)
        valid = torch.isfinite(lookback).all(dim=(1, 2))
        valid &= torch.isfinite(target).all(dim=(1, 2))
        if name == "persistence_nmse":
            scale = lookback.std(dim=-1, unbiased=False)
            valid &= (scale > float(eps)).all(dim=1)
            errors = errors / (scale.unsqueeze(-1) + float(eps)).pow(2)
        window_scores = errors.mean(dim=(1, 2))
        for local_index in torch.nonzero(valid, as_tuple=False).flatten().tolist():
            per_user[local_index].append(float(window_scores[local_index]))

    records = []
    source_ids = dataset.data.individual_ids.detach().cpu().tolist()
    for local_index, scores in enumerate(per_user):
        if not scores:
            raise ValueError(
                f"user {source_ids[local_index]} has no finite non-constant "
                "training window for difficulty scoring"
            )
        tensor = torch.as_tensor(scores, dtype=torch.float64)
        median = torch.quantile(tensor, 0.5)
        score = median if aggregation == "median" else tensor.mean()
        source_id = int(source_ids[local_index])
        records.append(
            {
                "local_index": local_index,
                "source_id": source_id,
                "name": str(dataset.data.individual_names[source_id]),
                "score": float(score),
                "mean_score": float(tensor.mean()),
                "median_score": float(median),
                "windows": len(scores),
            }
        )
    return records


def save_difficulty(
    records: list[dict[str, Any]],
    path: str | Path,
    *,
    config: dict[str, Any],
) -> Path:
    path = Path(path).expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "scope": "accessible_training_windows_only",
        "config": config,
        "users": records,
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return path
