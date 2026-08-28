# Curriculum learning experiment

This project tests whether presenting training users from easier to harder
improves forecasting convergence, final accuracy, or worst-user performance.
The model, initialization, optimizer-step budget, batch size, normalization,
loss, chronological splits, and evaluation rows remain fixed; only the
training-user sampling schedule changes.

The primary comparison is easy-to-hard against uniform sampling. Reverse,
seeded-random, and exposure-matched controls distinguish temporal ordering from
ordinary reweighting. DLinear and PatchTST are trained from scratch.

## Documentation map

| Need | Document |
|---|---|
| Paper-ready problem and method | [`latex/method_overview.pdf`](latex/method_overview.pdf) |
| Code path and package ownership | [`docs/architecture.md`](docs/architecture.md) |
| Profiles, Slurm front, and required comparisons | [`docs/experiment_catalog.md`](docs/experiment_catalog.md) |
| Finalized evidence and missing runs | [`docs/results_recap.md`](docs/results_recap.md) |
| Complete reproducibility specification | [`latex/experiment_guideline.pdf`](latex/experiment_guideline.pdf) |
| Full analyzed evidence record | [`latex/executive_summary.pdf`](latex/executive_summary.pdf) |

## Setup

Use the project-managed environment from the repository root and expose the
flat source tree:

```bash
uv sync
export PYTHONPATH=src
```

Place wide CSV datasets under `datasets/<name>/`; an adjacent `config.json`
controls targets, exclusions, date handling, and aggregation. This project
reads CSV directly and does not use TimeTensors prepared `.pt` datasets.

## Main executions

Run the smoke gate before either publication profile:

```bash
EXPERIMENT_MODE=test sbatch curriculum.slurm
EXPERIMENT_MODE=full sbatch curriculum.slurm
EXPERIMENT_MODE=ultra sbatch curriculum.slurm
```

`test` is Electricity `504:168` with PatchTST and seed 1. `full` is the
six-dataset, three-setting PatchTST study with seeds 1--3; `ultra` adds
DLinear. All modes use the same resumable identity tree. The default
`STAGES=train,tables` runs fitting before aggregate reporting; a stage subset
is a recovery override only.

Use the matching overflow front on Selena:

```bash
EXPERIMENT_MODE=test sbatch curriculum_selena.slurm
```

The exact methods, profile axes, metrics, and interpretation checklist are in
the [experiment catalog](docs/experiment_catalog.md). Scientific and artifact
details are intentionally kept in the experiment guideline rather than here.

## Outputs and cluster operations

- Runs: `outputs/curriculum/` on DGX or `outputs_selena/curriculum/` on Selena.
- Publishable tables: `outputs/reports/curriculum/<mode>/`.
- Runtime logs: `logs/` or `logs_selena/`.
- Run identity and lifecycle: each `run_n/manifest.json`; report inputs:
  `report_manifest.json`.

Mirror maintained code from DGX after previewing remote deletions:

```bash
bash sync_code_to_selena.sh --dry-run
bash sync_code_to_selena.sh
```

The preview marks stale maintained files with `*deleting`. The real transfer
uses delayed deletion; cluster-owned environments, dependency manifests,
datasets, weights, outputs, and logs remain protected.

Pull results from Selena on DGX with the smallest useful tier:

```bash
bash sync_results_to_dgx.sh
bash sync_results_to_dgx.sh --size detailed
bash sync_results_to_dgx.sh --size full
```

The default retrieves logs and aggregate reports. `detailed` adds non-binary
run diagnostics; `full` is for binary recovery. Publish a terminal job with
`bash publish_job.sh <job-id>` or publish all logs and aggregate reports with
`bash publish_job.sh`.

## Documentation maintenance

```bash
PYTHONPATH=src python -m scripts.build_docs
PYTHONPATH=src python -m scripts.build_docs --render method
PYTHONPATH=src python -m scripts.build_docs --render all
```

The default validates the documentation map and Slurm coverage. Update only
the view that owns the changed information: formulation in the method note,
implementation flow in architecture, planned execution in the catalog, and
newly analyzed evidence in the recap and executive summary.
