"""Aggregate seed-level curriculum results into reader-friendly tables."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import pandas as pd

from pipeline.runs import (
    SelectedRun,
    load_manifest,
    manifest_is_selectable,
    select_identity_runs,
    write_report_manifest,
)


IDENTITY_COLUMNS = ["dataset", "lags", "horizon", "model", "method"]


def _markdown_table(frame: pd.DataFrame) -> str:
    columns = [str(column) for column in frame.columns]

    def cell(value) -> str:
        if pd.isna(value):
            return "--"
        return str(value).replace("|", "\\|").replace("\n", " ")

    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    lines.extend(
        "| " + " | ".join(cell(value) for value in row) + " |"
        for row in frame.itertuples(index=False, name=None)
    )
    return "\n".join(lines) + "\n"


def _latex_table(frame: pd.DataFrame) -> str:
    def cell(value) -> str:
        if pd.isna(value):
            return "--"
        replacements = {
            "\\": r"\textbackslash{}",
            "&": r"\&",
            "%": r"\%",
            "$": r"\$",
            "#": r"\#",
            "_": r"\_",
            "{": r"\{",
            "}": r"\}",
        }
        return "".join(replacements.get(char, char) for char in str(value))

    columns = [cell(column) for column in frame.columns]
    lines = [
        rf"\begin{{tabular}}{{{'l' * len(columns)}}}",
        r"\hline",
        " & ".join(columns) + r" \\",
        r"\hline",
    ]
    lines.extend(
        " & ".join(cell(value) for value in row) + r" \\"
        for row in frame.itertuples(index=False, name=None)
    )
    lines.extend([r"\hline", r"\end{tabular}"])
    return "\n".join(lines) + "\n"


def _selected_runs(
    root: str | Path,
    *,
    pipeline_config: dict | None = None,
    config_policy: str = "distinct",
    repeat_policy: str = "selected",
    purposes: list[str] | None = None,
) -> list[SelectedRun]:
    base = Path(root).expanduser().resolve()
    active_launch = os.environ.get("EXPERIMENT_LAUNCH_ID")
    identity_roots = sorted(
        {path.parent.parent for path in base.rglob("manifest.json") if path.parent.name.startswith("run_") and "archive" not in path.relative_to(base).parts}
    )
    selected: list[SelectedRun] = []
    for identity_root in identity_roots:
        manifests = [load_manifest(path) for path in identity_root.glob("run_*/manifest.json")]
        if any(manifest_is_selectable(manifest, allow_ready_launch_id=active_launch) for manifest in manifests):
            selected.extend(
                select_identity_runs(
                    identity_root,
                    requested_pipeline=pipeline_config,
                    config_policy=config_policy,
                    repeat_policy=repeat_policy,
                    purposes=purposes,
                    allow_ready_launch_id=active_launch,
                )
            )
    return selected


def collect_results(root: str | Path, **selection) -> tuple[pd.DataFrame, pd.DataFrame]:
    metric_rows = []
    quantile_rows = []
    for selected in _selected_runs(root, **selection):
        for seed, state in selected.manifest.get("seed_status", {}).items():
            if state.get("status") not in {"ready", "completed"}:
                continue
            path = selected.run_dir / f"seed_{seed}" / "results.json"
            payload = json.loads(path.read_text(encoding="utf-8"))
            identity = {
                "dataset": payload["dataset"],
                "lags": int(payload["task"]["lags"]),
                "horizon": int(payload["task"]["horizon"]),
                "model": selected.manifest["identity"]["backbone"],
                "method": selected.label,
                "seed": int(payload["seed"]),
                "result_path": str(path),
            }
            for split, metrics in payload.get("metrics", {}).items():
                for metric, value in metrics.items():
                    metric_rows.append(
                        {**identity, "split": split, "metric": metric, "value": float(value)}
                    )
            for split, metrics in payload.get("difficulty_quantiles", {}).items():
                for metric, quantiles in metrics.items():
                    for quantile, values in quantiles.items():
                        quantile_rows.append(
                            {
                                **identity,
                                "split": split,
                                "metric": metric,
                                "quantile": quantile,
                                "value": float(values["mean"]),
                                "users": int(values["users"]),
                            }
                        )
    return pd.DataFrame(metric_rows), pd.DataFrame(quantile_rows)


def aggregate_results(
    root: str | Path,
    output_dir: str | Path | None = None,
    **selection,
) -> dict[str, Path]:
    root = Path(root)
    output_dir = Path(output_dir) if output_dir is not None else root / "tables"
    output_dir.mkdir(parents=True, exist_ok=True)
    metrics, quantiles = collect_results(root, **selection)
    if metrics.empty:
        raise ValueError(f"no seed-level results.json found below {root}")

    group_columns = [*IDENTITY_COLUMNS, "split", "metric"]
    summary = (
        metrics.groupby(group_columns, as_index=False)["value"]
        .agg(["mean", "std", "count"])
        .reset_index()
    )
    summary["mean_std"] = summary.apply(
        lambda row: (
            f"{row['mean']:.6g}"
            if int(row["count"]) == 1
            else f"{row['mean']:.6g} ± {row['std']:.3g}"
        ),
        axis=1,
    )

    paths = {
        "seed_metrics": output_dir / "seed_metrics.csv",
        "summary_csv": output_dir / "summary.csv",
        "summary_markdown": output_dir / "summary.md",
        "summary_latex": output_dir / "summary.tex",
        "summary_json": output_dir / "summary.json",
    }
    metrics.to_csv(paths["seed_metrics"], index=False)
    summary.to_csv(paths["summary_csv"], index=False)
    paths["summary_markdown"].write_text(
        _markdown_table(summary),
        encoding="utf-8",
    )
    paths["summary_latex"].write_text(
        _latex_table(summary),
        encoding="utf-8",
    )
    json_records = summary.astype(object).where(summary.notna(), None).to_dict(
        orient="records"
    )
    paths["summary_json"].write_text(
        json.dumps(json_records, indent=2, allow_nan=False),
        encoding="utf-8",
    )
    if not quantiles.empty:
        quantile_path = output_dir / "difficulty_quantiles.csv"
        quantiles.to_csv(quantile_path, index=False)
        paths["difficulty_quantiles"] = quantile_path
    write_report_manifest(
        output_dir / "report_manifest.json",
        inputs=_selected_runs(root, **selection),
        config_policy=str(selection.get("config_policy", "distinct")),
        repeat_policy=str(selection.get("repeat_policy", "selected")),
        filters={"pipeline": selection.get("pipeline_config", {}), "purposes": selection.get("purposes", [])},
    )
    return paths


def _value(text: str):
    lowered = text.casefold()
    if lowered in {"true", "false"}:
        return lowered == "true"
    try:
        return int(text)
    except ValueError:
        try:
            return float(text)
        except ValueError:
            return text


def _pipeline(values: list[str]) -> dict:
    output = {}
    for item in values:
        key, value = item.split("=", 1)
        output[key] = _value(value)
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--pipeline-config", action="append", default=[])
    parser.add_argument("--config-policy", choices=["distinct", "latest", "average"], default="distinct")
    parser.add_argument("--repeat-policy", default="selected")
    parser.add_argument("--purpose", action="append", default=[])
    args = parser.parse_args()
    paths = aggregate_results(
        args.root,
        args.output_dir,
        pipeline_config=_pipeline(args.pipeline_config),
        config_policy=args.config_policy,
        repeat_policy=args.repeat_policy,
        purposes=args.purpose,
    )
    for name, path in paths.items():
        print(f"{name}={path}")


if __name__ == "__main__":
    main()
