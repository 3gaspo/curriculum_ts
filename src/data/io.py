"""CSV ingestion and serialized time-series dataset I/O."""

from __future__ import annotations

import json
import math
import warnings
from bisect import bisect_right
from dataclasses import asdict, dataclass, replace
from functools import cached_property
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
import torch
from torch.utils.data import DataLoader, Dataset

from .core import *  # noqa: F401,F403
from .core import _cuda_available, _path, _ensure_dir, _json_file, _read_json, _write_json, _as_values_3d, _as_individual_context, _as_global_context, _normalise_indices, _valid_query_dates
from .sampling import *  # noqa: F401,F403
from .sampling import _slice_temporal_context
from .frames import *  # noqa: F401,F403
from .frames import _selected_variates, _value_columns, _repeat_static_context, _unroll_batches

def fetch_csv(
    data_path: str | Path,
    data_name: str,
    global_context_cols: Optional[Sequence[str]] = None,
    target_cols: Optional[Sequence[str]] = None,
    drop_users: Optional[str | Sequence[int]] = None,
    rename_cols: Optional[Mapping[str, str]] = None,
    aggr: Optional[str] = None,
    aggr_period: str = "h",
    users_dim: int = 1,
    date_col: Optional[str] = None,
    dates: Optional[Sequence[Any]] = None,
    drop: Optional[str | Sequence[Any]] = None,
    return_metadata: bool = False,
) -> Tuple[pd.DataFrame, Optional[pd.DataFrame], List[Any]] | Tuple[
    pd.DataFrame,
    Optional[pd.DataFrame],
    List[Any],
    Dict[str, Any],
]:
    """Load a CSV into date-by-series values and optional global context.

    ``users_dim=1`` expects series in columns. ``users_dim=0`` expects series
    in rows and transposes the frame. Source series positions are retained as
    stable individual IDs even after columns are dropped.
    """
    if users_dim not in {0, 1}:
        raise ValueError("users_dim must be 0 or 1")
    csv_path = _path(data_path) / f"{data_name}.csv"
    if date_col is not None:
        if users_dim == 0:
            raise ValueError("date_col is only supported when users_dim=1")
        df = pd.read_csv(csv_path)
        if date_col not in df.columns:
            raise KeyError(f"date column {date_col!r} not found")
        df[date_col] = pd.to_datetime(df[date_col])
        df = df.set_index(date_col)
    else:
        df = pd.read_csv(
            csv_path,
            index_col=0,
            parse_dates=users_dim == 1,
        )
    if users_dim == 0:
        df = df.T
        try:
            df.index = pd.to_datetime(df.index)
        except (TypeError, ValueError):
            pass
    if dates is not None:
        if len(dates) != len(df):
            raise ValueError(
                f"dates length {len(dates)} does not match dataframe length {len(df)}"
            )
        df.index = pd.to_datetime(dates)
    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.RangeIndex(len(df))

    if global_context_cols is None:
        values_df, global_context_df = df.copy(), None
    else:
        columns = list(global_context_cols)
        global_context_df = df[columns].copy()
        values_df = df.drop(columns=columns).copy()

    source_columns = list(values_df.columns)
    source_ids = list(range(len(source_columns)))
    source_names = {
        source_id: str(
            rename_cols.get(column, column) if rename_cols is not None else column
        )
        for source_id, column in zip(source_ids, source_columns)
    }
    if target_cols is not None:
        requested_targets = [str(column) for column in target_cols]
        missing = [column for column in requested_targets if column not in source_columns]
        if missing:
            raise KeyError(f"target columns not found: {missing}")
        source_ids = [source_columns.index(column) for column in requested_targets]
        values_df = values_df.iloc[:, source_ids]
    requested_drop = drop if drop is not None else drop_users
    if requested_drop is not None:
        items = (
            requested_drop.split(";")
            if isinstance(requested_drop, str)
            else list(requested_drop)
        )
        drop_ids = set()
        for item in items:
            if item in source_columns:
                drop_ids.add(source_columns.index(item))
            elif str(item) in source_columns:
                drop_ids.add(source_columns.index(str(item)))
            elif isinstance(item, (int, np.integer)) or str(item).isdigit():
                source_id = int(item)
                if source_id < 0 or source_id >= len(source_columns):
                    raise IndexError(f"series index {source_id} is out of bounds")
                drop_ids.add(source_id)
            else:
                raise KeyError(f"series {item!r} not found")
        keep_ids = [source_id for source_id in source_ids if source_id not in drop_ids]
        keep_positions = [source_ids.index(source_id) for source_id in keep_ids]
        values_df = values_df.iloc[:, keep_positions]
        source_ids = keep_ids

    values_df.columns = [f"serie_{source_id}" for source_id in source_ids]

    if aggr is not None:
        if not isinstance(values_df.index, pd.DatetimeIndex):
            raise ValueError(
                "aggregation requires a DatetimeIndex; provide date_col or dates"
            )
        if aggr == "sum":
            reducer = "sum"
        elif aggr in {"mean", "last", "first"}:
            reducer = aggr
        elif aggr == "asfreq":
            reducer = None
        else:
            raise ValueError(
                "aggr must be one of: None, 'sum', 'mean', 'last', 'first', "
                "'asfreq'"
            )
        if reducer is None:
            values_df = values_df.asfreq(aggr_period)
            if global_context_df is not None:
                global_context_df = global_context_df.asfreq(aggr_period)
        else:
            values_df = getattr(values_df.resample(aggr_period), reducer)()
            if global_context_df is not None:
                global_context_df = getattr(
                    global_context_df.resample(aggr_period), reducer
                )()

    result = (values_df, global_context_df, list(values_df.index))
    if not return_metadata:
        return result
    metadata = {
        "individual_ids": source_ids,
        "individual_names": {
            source_id: source_names[source_id] for source_id in source_ids
        },
    }
    return (*result, metadata)


def read_csv_data(
    data_path: str | Path,
    data_name: str,
    global_context_cols: Optional[Sequence[str]] = None,
    target_cols: Optional[Sequence[str]] = None,
    drop_users: Optional[str | Sequence[int]] = None,
    build_individual_ids_context: bool = False,
    rename_cols: Optional[Mapping[str, str]] = None,
    aggr: Optional[str] = None,
    aggr_period: str = "h",
    users_dim: int = 1,
    date_col: Optional[str] = None,
    dates: Optional[Sequence[Any]] = None,
    drop: Optional[str | Sequence[Any]] = None,
) -> TimeSeriesData:
    """Read one CSV dataset into memory without writing tensor artifacts."""
    values_df, global_df, datetimes, metadata = fetch_csv(
        data_path,
        data_name,
        global_context_cols=global_context_cols,
        target_cols=target_cols,
        drop_users=drop_users,
        rename_cols=rename_cols,
        aggr=aggr,
        aggr_period=aggr_period,
        users_dim=users_dim,
        date_col=date_col,
        dates=dates,
        drop=drop,
        return_metadata=True,
    )
    values = torch.tensor(values_df.values, dtype=torch.float32).T.unsqueeze(1)
    individual_context = None
    if build_individual_ids_context:
        individual_context = torch.tensor(
            metadata["individual_ids"], dtype=torch.float32
        ).view(values.shape[0], 1, 1)
    global_context = None
    if global_df is not None:
        global_context = torch.tensor(
            global_df.values, dtype=torch.float32
        ).T
    return TimeSeriesData(
        values,
        datetimes,
        individual_context=individual_context,
        global_context=global_context,
        individual_ids=metadata["individual_ids"],
        individual_names=metadata["individual_names"],
    )
