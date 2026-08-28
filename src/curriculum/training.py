"""Exact-step training loop with curriculum phase updates."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from time import perf_counter
from typing import Any

from training.pipeline import TorchLearner, set_seed

from .controller import CurriculumController


def _positive_frequency(value: Any, *, default: int, name: str) -> int:
    frequency = default if value in {None, "None", "none", "null", ""} else int(value)
    if frequency < 1:
        raise ValueError(f"{name} must be positive")
    return frequency


def fit_curriculum(
    learner: TorchLearner,
    train_loader: Iterable[Any],
    controller: CurriculumController,
    *,
    steps: int,
    valid_loaders: Mapping[str, Iterable[Any]] | None = None,
    valid_eval_freq: int | None = None,
    logging_eval_freq: int | None = None,
    eval_runs: int = 1,
    seed: int | None = None,
    logger: Any = None,
) -> dict[str, Any]:
    """Train for exactly ``steps`` optimizer updates without resetting state."""
    steps = int(steps)
    if steps < 1:
        raise ValueError("training.steps must be positive")
    set_seed(seed)
    valid_interval = _positive_frequency(
        valid_eval_freq,
        default=steps,
        name="valid_eval_freq",
    )
    logging_interval = _positive_frequency(
        logging_eval_freq,
        default=valid_interval,
        name="logging_eval_freq",
    )
    if logging_interval % valid_interval != 0:
        raise ValueError("logging_eval_freq must be a multiple of valid_eval_freq")

    history: dict[str, Any] = {
        "train": [],
        "train_batch": [],
        "valid": {},
        "curriculum": [],
    }
    recent_losses: list[float] = []
    criterion_name = getattr(learner.criterion, "name", "loss")
    start = perf_counter()
    iterator = None

    def record_interval(step: int) -> dict[str, Any] | None:
        if not recent_losses:
            return None
        value = sum(recent_losses) / len(recent_losses)
        item = {
            "step": step,
            "loss": value,
            "losses": {criterion_name: value},
        }
        history["train_batch"].append(item)
        recent_losses.clear()
        return item

    def validate(step: int, *, log: bool) -> None:
        for split, loader in (valid_loaders or {}).items():
            result = learner.evaluate(loader, runs=int(eval_runs), seed=None)
            history["valid"].setdefault(split, []).append(
                {"step": step, **result}
            )
            if log and logger is not None:
                logger.info("step=%s valid[%s]=%s", step, split, result["losses"])

    if logger is not None:
        logger.info(
            "training steps=%s batch_size=%s valid_eval_freq=%s logging_eval_freq=%s",
            steps,
            controller.samples_per_step,
            valid_interval,
            logging_interval,
        )

    for run_step in range(steps):
        event = controller.before_step(run_step)
        if event is not None:
            history["curriculum"].append(event)
            iterator = iter(train_loader)
        if iterator is None:
            iterator = iter(train_loader)
        try:
            batch = next(iterator)
        except StopIteration:
            iterator = iter(train_loader)
            batch = next(iterator)

        loss = learner.train_step(batch)
        controller.after_batch(batch)
        history["train"].append(loss)
        recent_losses.append(loss)
        completed_step = run_step + 1
        if completed_step % valid_interval == 0 or completed_step == steps:
            interval = record_interval(completed_step)
            should_log = (
                completed_step % logging_interval == 0 or completed_step == steps
            )
            if should_log and logger is not None and interval is not None:
                logger.info(
                    "step=%s train_interval=%s",
                    completed_step,
                    interval["losses"],
                )
            validate(completed_step, log=should_log)

    history["elapsed_seconds"] = perf_counter() - start
    history["optimizer_steps"] = steps
    history["exposure"] = controller.provenance()
    if logger is not None:
        logger.info(
            "training_done steps=%s samples=%s seconds=%.2f",
            steps,
            history["exposure"]["actual_samples"],
            history["elapsed_seconds"],
        )
    return history
