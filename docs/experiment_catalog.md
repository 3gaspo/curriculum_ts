# Experiment catalog

This is the readable checklist for the executable curriculum study. The Slurm
front remains the submission interface; the detailed protocol remains in the
[`experiment guideline`](../latex/experiment_guideline.pdf).

## Shared profiles

| Mode | Datasets | Settings | Backbones | Seeds |
|---|---|---|---|---|
| `test` | Electricity | `504:168` | PatchTST | 1 |
| `full` | ETTh1, Electricity, Traffic, Solar, Weather, Exchange Rate | `168:24`, `336:48`, `504:168` | PatchTST | 1--3 |
| `ultra` | Full profile | Full profile | PatchTST, DLinear | 1--3 |

## Slurm evaluations

| Front | Scientific question | Compared treatments | Expected report |
|---|---|---|---|
| `curriculum.slurm` | Does user ordering improve convergence, final error, or worst-user error? | uniform, easy-to-hard, hard-to-easy, random order, exposure-matched | `outputs/reports/curriculum/<mode>/` |

The Selena counterpart is `curriculum_selena.slurm` and executes the same
science.

## Required comparisons

- Primary: easy-to-hard versus uniform.
- Ordering control: easy-to-hard versus hard-to-easy and random order.
- Exposure control: easy-to-hard versus exposure-matched.
- Metrics: global error, equal-user error, worst-10%-user error, convergence by
  optimizer step, and performance by difficulty quantile.
