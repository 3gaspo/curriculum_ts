"""Dataset-building stage for TimeTensor experiments."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Mapping

from .io import read_csv_data
from .loaders import fetch_training_data, get_sizes
from pipeline.runtime import (
    batch_size,
    default_sampling,
    default_splits,
    default_subsets,
    recompute_stats,
    run_dir,
    section,
    seed,
    setup_logging,
    stats_eps,
    stats_max_windows,
    stats_seed,
    task_shape,
    to_plain_config,
)


LOGGER = logging.getLogger(__name__)


DATASET_CONFIG_KEYS = {
    "global_context_cols",
    "target_cols",
    "drop_users",
    "build_individual_ids_context",
    "rename_cols",
    "aggr",
    "aggr_period",
    "users_dim",
    "date_col",
    "dates",
    "prefix",
}


def _as_list(value: Any) -> list[Any]:
    if value is None or value == "":
        return []
    if isinstance(value, str):
        return [part.strip() for part in value.replace(";", ",").split(",") if part.strip()]
    if isinstance(value, (list, tuple, set)):
        return list(value)
    return [value]


def _dataset_config_path(data_cfg: Mapping[str, Any]) -> tuple[Path | None, bool]:
    config_path = data_cfg.get("config_path")
    if config_path not in {None, ""}:
        path = Path(str(config_path)).expanduser()
        return (path / "config.json" if path.is_dir() else path), True
    base = data_cfg.get("raw_path") or data_cfg.get("path")
    if base in {None, ""}:
        return None, False
    base_path = Path(str(base)).expanduser()
    directory = base_path.parent if base_path.suffix.lower() == ".csv" else base_path
    return directory / "config.json", False


def _dataset_config_options(raw: Mapping[str, Any]) -> dict[str, Any]:
    options = {key: raw[key] for key in DATASET_CONFIG_KEYS if key in raw}
    scoped = raw.get("curriculum_learning")
    if scoped is not None:
        if not isinstance(scoped, Mapping):
            raise ValueError(
                "dataset config field 'curriculum_learning' must be an object"
            )
        if scoped.get("drop_users") is not None:
            options["drop_users"] = _as_list(scoped["drop_users"])
        options.update(
            {
                key: value
                for key, value in scoped.items()
                if key in DATASET_CONFIG_KEYS and key != "drop_users"
            }
        )
    return options


def _merge_dataset_config(
    data_cfg: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    explicit_keys = sorted(
        key for key, value in data_cfg.items() if value is not None
    )
    path, explicit = _dataset_config_path(data_cfg)
    if path is None or not path.exists():
        if explicit:
            raise FileNotFoundError(path)
        return dict(data_cfg), {
            "selected_path": None,
            "applied_keys": [],
            "explicit_keys": explicit_keys,
            "effective_drop_users": _as_list(data_cfg.get("drop_users")),
            "effective_target_cols": data_cfg.get("target_cols"),
            "window_anchor": "query_t",
        }
    if path.suffix.lower() != ".json":
        raise ValueError(f"dataset config must be JSON, got {path}")
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, Mapping):
        raise ValueError(f"dataset config must contain a JSON object: {path}")
    loaded = _dataset_config_options(raw)
    merged = dict(loaded)
    explicit = {key: value for key, value in data_cfg.items() if value is not None}
    merged.update({key: value for key, value in explicit.items() if key != "drop_users"})
    merged["drop_users"] = (
        _as_list(explicit["drop_users"])
        if "drop_users" in explicit
        else _as_list(loaded.get("drop_users"))
    )
    merged["config_path"] = str(path)
    LOGGER.info("loaded dataset config path=%s keys=%s", path, sorted(loaded))
    return merged, {
        "selected_path": str(path),
        "applied_keys": sorted(loaded),
        "explicit_keys": explicit_keys,
        "effective_drop_users": merged["drop_users"],
        "effective_target_cols": merged.get("target_cols"),
        "window_anchor": "query_t",
    }


def build_dataset_stage(config: Mapping[str, Any]) -> dict[str, Any]:
    """Read the configured CSV, then optionally construct loaders and stats."""
    config = to_plain_config(config)
    data_cfg, dataset_config = _merge_dataset_config(section(config, "data"))
    config = {**config, "data": data_cfg}
    experiment = section(config, "experiment")
    raw_path = Path(data_cfg.get("raw_path", "."))
    data_name = raw_path.stem if raw_path.suffix.lower() == ".csv" else data_cfg.get("name")
    if data_name is None:
        raise ValueError("data.name is required to load a CSV dataset")
    csv_path = raw_path if raw_path.suffix.lower() == ".csv" else raw_path / f"{data_name}.csv"
    csv_root = raw_path.parent if raw_path.suffix.lower() == ".csv" else raw_path
    provenance_path = run_dir(config) / "dataset_config.json"
    provenance_path.write_text(
        json.dumps(dataset_config, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    LOGGER.info(
        "dataset config path=%s applied_keys=%s explicit_keys=%s",
        dataset_config["selected_path"],
        dataset_config["applied_keys"],
        dataset_config["explicit_keys"],
    )
    data = read_csv_data(
        csv_root,
        str(data_name),
        global_context_cols=data_cfg.get("global_context_cols"),
        target_cols=data_cfg.get("target_cols"),
        drop_users=data_cfg.get("drop_users"),
        build_individual_ids_context=bool(data_cfg.get("build_individual_ids_context", False)),
        rename_cols=data_cfg.get("rename_cols"),
        aggr=data_cfg.get("aggr"),
        aggr_period=data_cfg.get("aggr_period", "h"),
        users_dim=int(data_cfg.get("users_dim", 1)),
        date_col=data_cfg.get("date_col"),
        dates=data_cfg.get("dates"),
    )
    result: dict[str, Any] = {
        "data": data,
        "dataset_path": csv_path,
        "dataset_config": dataset_config,
        "dataset_config_path": provenance_path,
    }
    if bool(experiment.get("prepare_loaders", data_cfg.get("prepare_loaders", True))):
        lags, horizon = task_shape(config)
        loaders, stats = fetch_training_data(
            data,
            default_splits(config),
            default_sampling(config),
            default_subsets(config),
            batch_size(config),
            lags,
            horizon,
            seed=seed(config),
            stats_save_path=run_dir(config) / "dataset_artifacts",
            compute_stats=recompute_stats(config),
            stats_max_windows=stats_max_windows(config),
            stats_seed=stats_seed(config),
            stats_eps=stats_eps(config),
        )
        result["loaders"] = loaders
        result["stats"] = stats
        result["shape"] = get_sizes(loaders)
    return result


def main(config: Mapping[str, Any] | None = None) -> dict[str, Any]:
    setup_logging(section(to_plain_config(config or {}), "misc").get("log_level", "INFO"))
    return build_dataset_stage(config or {})
