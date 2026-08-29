"""Static contract checks for the resumable Slurm workflow."""

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]


class SlurmWorkflowTest(unittest.TestCase):
    def test_cluster_sync_scripts(self):
        code = (ROOT / "sync_code_to_selena.sh").read_text(encoding="utf-8")
        results = (ROOT / "sync_results_to_dgx.sh").read_text(encoding="utf-8")
        for script in (code, results):
            self.assertIn('PROJECT_NAME="$(basename "$PROJECT_ROOT")"', script)
            self.assertIn("sed -n '1p'", script)
        for excluded in (
            ".git/",
            ".venv/",
            ".secrets/",
            "pyproject.toml",
            "uv.lock",
            "datasets/",
            "weights/",
            "outputs/",
            "logs/",
        ):
            self.assertIn(f"--exclude='{excluded}'", code)
        self.assertIn("selena.hpc.edf.fr", code)
        self.assertIn("--delete", code)
        self.assertNotIn("dgx-front.retd.edf.fr", results)
        self.assertIn(
            'SOURCE_ROOT="$nni@selena.hpc.edf.fr:~/codes/$PROJECT_NAME"',
            results,
        )
        self.assertIn('DESTINATION_ROOT="$PROJECT_ROOT"', results)
        self.assertIn('mkdir -p "$DESTINATION_ROOT/outputs_selena"', results)
        self.assertIn("--include='outputs_selena/.gitkeep'", code)
        self.assertIn("--exclude='outputs_selena/***'", code)
        self.assertIn("--include='logs_selena/.gitkeep'", code)
        self.assertIn("--exclude='logs_selena/***'", code)
        self.assertIn('"$SOURCE_ROOT/outputs_selena/"', results)
        self.assertIn('"$SOURCE_ROOT/logs_selena/"', results)
        self.assertIn("pulled from Selena to DGX", results)
        self.assertNotIn("--delete", results)

    def test_complete_front_and_internal_stages(self):
        front = (ROOT / "curriculum.slurm").read_text(encoding="utf-8")
        selena = (ROOT / "curriculum_selena.slurm").read_text(encoding="utf-8")
        runner = (ROOT / "src/slurm/run_curriculum_experiment.sh").read_text(
            encoding="utf-8"
        )
        self.assertIn('STAGES="${STAGES:-train,tables}"', front)
        self.assertIn('STAGES="${STAGES:-train,tables}"', selena)
        self.assertIn("#SBATCH --partition=a100", front)
        self.assertIn("#SBATCH --partition=an", selena)
        self.assertIn("#SBATCH --qos=an_preemptable", selena)
        self.assertIn("#SBATCH --output=logs_selena/%x_%j.out", selena)
        self.assertIn("#SBATCH --exclusive", selena)
        self.assertNotIn("#SBATCH --no-requeue", selena)
        self.assertIn("#SBATCH --wckey=P12CU:DATASCIENCE", selena)
        self.assertIn('OUTPUTS_ROOT="$PROJECT_ROOT/outputs_selena"', selena)
        self.assertIn('LOGS_ROOT="$PROJECT_ROOT/logs_selena"', selena)
        self.assertIn('EXPERIMENT_LAUNCH_ID="selena_${SLURM_JOB_ID', selena)
        self.assertIn('LOGS_ROOT="${LOGS_ROOT:-$ROOT/logs}"', runner)
        self.assertIn('OUTPUTS_ROOT="${OUTPUTS_ROOT:-$ROOT/outputs}"', runner)
        self.assertIn('DEFAULT_OUT_ROOT="$OUTPUTS_ROOT/curriculum"', runner)
        self.assertNotIn("RUN_MODE", front + runner)
        for mode in ("test)", "full)", "ultra)"):
            self.assertIn(mode, runner)
        self.assertNotIn("  small)", runner)
        self.assertIn('DEFAULT_SETTINGS="168:24 336:48 504:168"', runner)
        self.assertIn('DEFAULT_DATASETS="electricity"', runner)
        self.assertIn('DEFAULT_SETTINGS="504:168"', runner)
        self.assertEqual(runner.count('DEFAULT_MODELS="patchtst"'), 2)
        self.assertIn('DEFAULT_MODELS="dlinear patchtst"', runner)
        self.assertEqual(
            runner.count(
                'DEFAULT_DATASETS="ETTh1 electricity traffic solar weather exchange_rate"'
            ),
            2,
        )
        self.assertIn("python -m pipeline.runs allocate", runner)
        self.assertIn("python -m pipeline.runs pending-seeds", runner)
        self.assertIn("python -m pipeline.runs status", runner)
        self.assertIn("--status ready", runner)
        self.assertIn("python -m pipeline.runs ready", runner)
        self.assertIn("python -m pipeline.runs complete-launch", runner)
        self.assertIn("python -m pipeline.runs complete --run-dir", runner)
        self.assertIn("srun --ntasks=1 python -m scripts.experiment", runner)
        self.assertIn("srun --ntasks=1 python -m scripts.summarize", runner)
        self.assertIn("srun --ntasks=1 python -m scripts.report", runner)
        self.assertNotIn("--status completed", runner)
        self.assertNotIn("run.complete", runner)
        self.assertNotIn(
            "tables.complete", (ROOT / "src/slurm/stage_tables.sh").read_text()
        )
        self.assertTrue((ROOT / "src/slurm/stage_train.sh").is_file())


class TerminalCompletionContractTest(unittest.TestCase):
    def test_tasks_stages_and_workflow_have_terminal_markers(self) -> None:
        runner = (ROOT / "src/slurm/run_curriculum_experiment.sh").read_text(
            encoding="utf-8"
        )
        self.assertIn("task $ACTIVE_TASK completed status=$status", runner)
        self.assertIn("completed status=failed exit_code=$status", runner)
        self.assertIn("workflow completed status=success exit_code=0", runner)
        self.assertIn("workflow completed status=failed exit_code=$status", runner)
        for name in ("train", "tables"):
            stage = (ROOT / f"src/slurm/stage_{name}.sh").read_text(encoding="utf-8")
            self.assertIn(f"stage_start {name}", stage)
            self.assertIn("stage_complete", stage)


if __name__ == "__main__":
    unittest.main()
