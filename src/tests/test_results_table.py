"""Check that one-seed smoke tables omit undefined seed uncertainty."""

from pathlib import Path
from tempfile import TemporaryDirectory

import torch

from pipeline.runs import allocate_run, mark_status
from results.reporting import generate_results_table


def _save_run(root: Path, method: str, mse: float) -> None:
    identity = root / "electricity" / "504_168" / "patchtst" / method
    allocation = allocate_run(
        identity,
        project="curriculum_learning",
        workflow="curriculum",
        dataset="electricity",
        lookback=504,
        horizon=168,
        backbone="patchtst",
        model_config_order=["method"],
        model_config={"method": method},
        pipeline_config={},
        seeds=[1],
        display_name=method,
    )
    relative = "seed_1/all_losses.pt"
    path = allocation.run_dir / relative
    path.parent.mkdir(parents=True)
    torch.save({"test1": {"mse": torch.tensor([mse, mse])}}, path)
    mark_status(allocation.run_dir, "completed", seed=1, required_artifacts=[relative])
    mark_status(allocation.run_dir, "completed", required_artifacts=[relative])


def main() -> None:
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        for method, mse in (("uniform", 0.0012), ("easy_to_hard", 0.0009)):
            _save_run(root, method, mse)
        output = generate_results_table(
            root,
            methods=["uniform", "easy_to_hard"],
            reference="uniform",
            show_std=True,
        )
        latex = output.read_text(encoding="utf-8")
        assert r"\pm" not in latex


if __name__ == "__main__":
    main()
