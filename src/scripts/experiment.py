"""Hydra entry point for curriculum-learning forecasting experiments."""

from __future__ import annotations

import logging
from copy import deepcopy
from pathlib import Path
from time import perf_counter
from typing import Any, Mapping

from curriculum.controller import CurriculumController
from curriculum.difficulty import save_difficulty, score_user_difficulty
from results.curriculum import (
    history_summary,
    save_json,
    summarize_difficulty_quantiles,
    summarize_losses,
)
from curriculum.schedule import build_curriculum_plan
from curriculum.training import fit_curriculum
from data.load import build_dataset_stage
from model_loading import load_model
from pipeline.runtime import (
    config_bool,
    device,
    model_specs,
    run_dir,
    save_torch,
    section,
    seed,
    seeded_configs,
    setup_logging,
    task_shape,
    to_plain_config,
)
from training.evaluate import eval_stage
from training.losses import get_losses
from training.pipeline import TorchLearner, set_seed
from visualization.experiment_plots import save_criterion_loss_plot


LOGGER = logging.getLogger(__name__)


def _save_resolved_config(config: Mapping[str, Any], path: Path) -> Path:
    return save_json(dict(config), path)


def _curriculum_config(config: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    curriculum = section(config, "curriculum")
    difficulty = dict(curriculum.get("difficulty") or {})
    schedule = dict(curriculum.get("schedule") or {})
    return {
        "method": str(curriculum.get("method", "uniform")),
        "difficulty": difficulty,
        "schedule": schedule,
    }, curriculum


def run_experiment(config: Mapping[str, Any]) -> dict[str, Any]:
    config = to_plain_config(config)
    setup_logging(section(config, "misc").get("log_level", "INFO"))
    started = perf_counter()
    out_dir = run_dir(config)
    _save_resolved_config(config, out_dir / "resolved_config.json")

    experiment_seed = seed(config)
    set_seed(experiment_seed)
    LOGGER.info("%s", "=" * 72)
    LOGGER.info(
        "experiment dataset=%s model=%s method=%s seed=%s out=%s",
        section(config, "data").get("name"),
        section(config, "model").get("name"),
        section(config, "curriculum").get("method"),
        experiment_seed,
        out_dir,
    )

    built = build_dataset_stage(config)
    loaders = built["loaders"]
    stats = built.get("stats")
    train_loader = loaders["train"]
    train_dataset = train_loader.dataset
    lags, horizon = task_shape(config)
    shape = (
        lags,
        int(train_dataset.data.values.shape[1]),
        horizon,
    )

    curriculum_config, curriculum = _curriculum_config(config)
    difficulty_config = curriculum_config["difficulty"]
    records = score_user_difficulty(
        train_dataset,
        name=str(difficulty_config.get("name", "persistence_nmse")),
        stride=int(difficulty_config.get("stride", difficulty_config.get("eval_stride", 1))),
        aggregation=str(difficulty_config.get("aggregation", "median")),
        eps=float(difficulty_config.get("eps", 1e-8)),
    )
    difficulty_path = save_difficulty(
        records,
        out_dir / "difficulty.json",
        config={
            "name": str(difficulty_config.get("name", "persistence_nmse")),
            "stride": int(
                difficulty_config.get("stride", difficulty_config.get("eval_stride", 1))
            ),
            "aggregation": str(difficulty_config.get("aggregation", "median")),
            "eps": float(difficulty_config.get("eps", 1e-8)),
            "window_anchor": "query_t",
        },
    )

    training = section(config, "training")
    steps = int(training.get("steps", 10000))
    schedule = curriculum_config["schedule"]
    plan = build_curriculum_plan(
        records,
        method=curriculum_config["method"],
        steps=steps,
        phases=int(schedule.get("phases", 5)),
        initial_fraction=float(schedule.get("initial_fraction", 0.2)),
        pacing=str(schedule.get("pacing", "linear")),
        seed=experiment_seed,
    )
    plan_payload = plan.to_dict(records)
    plan_path = save_json(plan_payload, out_dir / "curriculum_plan.json")

    # Data loading consumes RNG state; reseed before model construction so every
    # method starts from the same initialization for a given experiment seed.
    set_seed(experiment_seed)
    model = load_model(model_specs(config, shape), normalization_stats=stats)
    criterion, eval_losses = get_losses(
        training.get("loss", "nmse"),
        complete_evaluation=bool(training.get("complete_evaluation", True)),
    )
    learner = TorchLearner(
        model,
        criterion,
        eval_losses=eval_losses,
        lr=float(training.get("lr", 1e-5)),
        device=device(config),
        optimizer_name=str(training.get("optimizer", "adam")),
        optimizer_kwargs=training.get("optimizer_kwargs"),
        grad_clip=training.get("grad_clip"),
    )
    controller = CurriculumController(
        train_dataset,
        plan,
        records,
        samples_per_step=int(training.get("batch_size", 256)),
        logger=LOGGER,
    )
    valid_loaders = {
        split: loader for split, loader in loaders.items() if "valid" in split
    }
    history = fit_curriculum(
        learner,
        train_loader,
        controller,
        steps=steps,
        valid_loaders=valid_loaders,
        valid_eval_freq=training.get("valid_eval_freq"),
        logging_eval_freq=training.get("logging_eval_freq"),
        eval_runs=int(training.get("eval_runs", 1)),
        seed=experiment_seed,
        logger=LOGGER,
    )
    state_path = learner.model.save_state_dict(out_dir / "model_state.pt")
    history_path = save_torch(history, out_dir / "train_history.pt")
    plot_path = save_criterion_loss_plot(
        history,
        criterion.name,
        out_dir / "criterion_loss.pdf",
        plot_step_train_loss=config_bool(training.get("plot_step_train_loss", False)),
    )

    eval_config = deepcopy(config)
    evaluation = eval_config.setdefault("evaluation", {})
    configured_splits = evaluation.get("splits")
    if configured_splits is None or (
        isinstance(configured_splits, str)
        and configured_splits in {"None", "none", ""}
    ):
        evaluation["splits"] = [
            split for split in loaders if split != "train"
        ]
    evaluated = eval_stage(
        eval_config,
        model=model,
        learner=learner,
        loaders=loaders,
    )

    results = {
        "dataset": section(config, "data").get("name"),
        "model": section(config, "model").get("name"),
        "method": curriculum_config["method"],
        "seed": experiment_seed,
        "task": {"lags": lags, "horizon": horizon},
        "training": history_summary(history),
        "metrics": summarize_losses(evaluated["all_losses"]),
        "difficulty_quantiles": summarize_difficulty_quantiles(
            evaluated["per_user_all_losses"],
            records,
            quantiles=int(curriculum.get("quantiles", 5)),
        ),
        "curriculum": {
            "plan": plan_payload,
            "realized": history["exposure"],
        },
        "artifacts": {
            "state": str(state_path),
            "history": str(history_path),
            "criterion_plot": str(plot_path),
            "difficulty": str(difficulty_path),
            "curriculum_plan": str(plan_path),
            "dataset_config": str(built["dataset_config_path"]),
            "all_losses": str(evaluated["all_losses_path"]),
            "per_user_all_losses": str(evaluated["per_user_all_losses_path"]),
        },
        "elapsed_seconds": perf_counter() - started,
    }
    result_path = save_json(results, out_dir / "results.json")
    LOGGER.info("experiment done result=%s seconds=%.2f", result_path, results["elapsed_seconds"])
    LOGGER.info("%s", "=" * 72)
    return results


def main(config: Mapping[str, Any] | None = None) -> dict[str, Any]:
    configs = seeded_configs(config or {})
    if len(configs) == 1:
        return run_experiment(configs[0])
    return {
        int(seed(item)): run_experiment(item)
        for item in configs
    }


try:
    import hydra  # type: ignore
except Exception:  # pragma: no cover
    hydra = None


if hydra is not None:

    @hydra.main(version_base=None, config_path="../conf", config_name="config")
    def _hydra_main(cfg):
        main(cfg)


if __name__ == "__main__":
    if hydra is None:
        raise RuntimeError("Hydra is required to run scripts.experiment")
    _hydra_main()
