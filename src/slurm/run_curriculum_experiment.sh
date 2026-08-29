#!/bin/bash
# Configure and orchestrate the complete curriculum workflow.
set -euo pipefail

log() { printf '%s %s\n' "$(date -Is)" "$*"; }
log_section() { printf '\n%s %s\n' "$(date -Is)" "$*"; }
log_error() { printf '%s %s\n' "$(date -Is)" "$*" >&2; }

bootstrap_on_exit() {
  local status=$?
  trap - EXIT
  if [ "$status" -eq 0 ]; then
    log_section "workflow completed status=success exit_code=0"
  else
    log_error "workflow completed status=failed exit_code=$status"
  fi
  exit "$status"
}

trap bootstrap_on_exit EXIT

ROOT="${SLURM_SUBMIT_DIR:-$(pwd)}"
cd "$ROOT"
LOGS_ROOT="${LOGS_ROOT:-$ROOT/logs}"
OUTPUTS_ROOT="${OUTPUTS_ROOT:-$ROOT/outputs}"
mkdir -p "$LOGS_ROOT" "$OUTPUTS_ROOT"
EXPERIMENT_MODE="${EXPERIMENT_MODE:-test}"
STAGES_SPEC="${STAGES:-train,tables}"
VENV_ACTIVATE="${VENV_ACTIVATE:-$ROOT/.venv/bin/activate}"
if [ -f "$VENV_ACTIVATE" ]; then
  source "$VENV_ACTIVATE"
elif [ -z "${VIRTUAL_ENV:-}" ]; then
  log_error "no active environment and $VENV_ACTIVATE does not exist"
  exit 1
fi
export PYTHONPATH="$ROOT/src"

DEFAULT_METHODS="uniform easy_to_hard hard_to_easy random_order exposure_matched"
DEFAULT_SEEDS="1 2 3"
DEFAULT_SETTINGS="168:24 336:48 504:168"
DEFAULT_STEPS=10000
DEFAULT_VALID_EVAL_FREQ=1000
DEFAULT_LOGGING_EVAL_FREQ=1000
DEFAULT_BATCH_SIZE=256
DEFAULT_OUT_ROOT="$OUTPUTS_ROOT/curriculum"
DEFAULT_SKIP_COMPLETED=true

case "$EXPERIMENT_MODE" in
  test)
    DEFAULT_DATASETS="electricity"
    DEFAULT_SETTINGS="504:168"
    DEFAULT_MODELS="patchtst"
    DEFAULT_SEEDS="1"
    DEFAULT_STEPS=20
    DEFAULT_VALID_EVAL_FREQ=10
    DEFAULT_LOGGING_EVAL_FREQ=10
    ;;
  full)
    DEFAULT_DATASETS="ETTh1 electricity traffic solar weather exchange_rate"
    DEFAULT_MODELS="patchtst"
    ;;
  ultra)
    DEFAULT_DATASETS="ETTh1 electricity traffic solar weather exchange_rate"
    DEFAULT_MODELS="dlinear patchtst"
    ;;
  *)
    log_error "EXPERIMENT_MODE must be test, full, or ultra (got $EXPERIMENT_MODE)"
    exit 2
    ;;
esac

DATASETS_SPEC="${DATASETS:-$DEFAULT_DATASETS}"
SETTINGS_SPEC="${SETTINGS:-$DEFAULT_SETTINGS}"
MODELS_SPEC="${MODELS:-$DEFAULT_MODELS}"
METHODS_SPEC="${METHODS:-$DEFAULT_METHODS}"
SEEDS_SPEC="${SEEDS:-$DEFAULT_SEEDS}"
STEPS="${STEPS:-$DEFAULT_STEPS}"
VALID_EVAL_FREQ="${VALID_EVAL_FREQ:-$DEFAULT_VALID_EVAL_FREQ}"
LOGGING_EVAL_FREQ="${LOGGING_EVAL_FREQ:-$DEFAULT_LOGGING_EVAL_FREQ}"
BATCH_SIZE="${BATCH_SIZE:-$DEFAULT_BATCH_SIZE}"
LEARNING_RATE="${LEARNING_RATE:-1e-5}"
PHASES="${PHASES:-5}"
INITIAL_FRACTION="${INITIAL_FRACTION:-0.2}"
PACING="${PACING:-linear}"
DIFFICULTY_NAME="${DIFFICULTY_NAME:-persistence_nmse}"
DIFFICULTY_AGGREGATION="${DIFFICULTY_AGGREGATION:-median}"
OUT_ROOT="${OUT_ROOT:-$DEFAULT_OUT_ROOT}"
REPORT_ROOT="${REPORT_ROOT:-$OUTPUTS_ROOT/reports/curriculum/$EXPERIMENT_MODE}"
SKIP_COMPLETED="${SKIP_COMPLETED:-$DEFAULT_SKIP_COMPLETED}"
RUN_CONFLICT_POLICY="${RUN_CONFLICT_POLICY:-overwrite_exact}"
FORCE_RUN="${FORCE_RUN:-false}"
TABLE_CONFIG_POLICY="${TABLE_CONFIG_POLICY:-distinct}"
TABLE_REPEAT_POLICY="${TABLE_REPEAT_POLICY:-selected}"
if [ "$EXPERIMENT_MODE" = test ]; then TABLE_PURPOSE="${TABLE_PURPOSE:-smoke}"; else TABLE_PURPOSE="${TABLE_PURPOSE:-publication}"; fi
EXPERIMENT_LAUNCH_ID="${EXPERIMENT_LAUNCH_ID:-${SLURM_JOB_ID:-manual_$(date -u '+%Y%m%dT%H%M%SZ')_$$}}"
export EXPERIMENT_LAUNCH_ID
ACTIVE_STAGE=""
ACTIVE_TASK=""

stage_start() {
  ACTIVE_STAGE="$1"
  log_section "stage $ACTIVE_STAGE started"
}

stage_complete() {
  log_section "stage $ACTIVE_STAGE completed status=success"
  ACTIVE_STAGE=""
}

task_start() {
  ACTIVE_TASK="$*"
  log "task $ACTIVE_TASK started"
}

task_complete() {
  local status="$1"
  log "task $ACTIVE_TASK completed status=$status"
  ACTIVE_TASK=""
}

curriculum_on_exit() {
  local status=$?
  trap - EXIT
  if [ -n "$ACTIVE_TASK" ]; then
    log_error "task $ACTIVE_TASK completed status=failed exit_code=$status"
  fi
  if [ -n "$ACTIVE_STAGE" ]; then
    log_error "stage $ACTIVE_STAGE completed status=failed exit_code=$status"
  fi
  if [ "$status" -ne 0 ]; then
    python -m pipeline.runs interrupt-launch --root "$OUT_ROOT" --launch-id "$EXPERIMENT_LAUNCH_ID" || true
  elif python -m pipeline.runs complete-launch --root "$OUT_ROOT" --launch-id "$EXPERIMENT_LAUNCH_ID" >/dev/null; then
    :
  else
    status=$?
  fi
  if [ "$status" -eq 0 ]; then
    log_section "workflow completed status=success exit_code=0"
  else
    log_error "workflow completed status=failed exit_code=$status"
  fi
  exit "$status"
}
trap curriculum_on_exit EXIT

read -r -a DATASET_LIST <<< "${DATASETS_SPEC//,/ }"
read -r -a SETTING_LIST <<< "${SETTINGS_SPEC//,/ }"
read -r -a MODEL_LIST <<< "${MODELS_SPEC//,/ }"
read -r -a METHOD_LIST <<< "${METHODS_SPEC//,/ }"
read -r -a SEED_LIST <<< "${SEEDS_SPEC//,/ }"
read -r -a STAGE_LIST <<< "${STAGES_SPEC//,/ }"
SEEDS_CSV="$(IFS=,; echo "${SEED_LIST[*]}")"

stage_requested() {
  local wanted="$1" stage
  for stage in "${STAGE_LIST[@]}"; do
    [ "$stage" = "$wanted" ] && return 0
  done
  return 1
}
for stage in "${STAGE_LIST[@]}"; do
  case "$stage" in
    train|tables) ;;
    *) log_error "STAGES must contain only train,tables (got $STAGES_SPEC)"; exit 2 ;;
  esac
done

resolve_dataset_dir() {
  local dataset="$1"
  local candidate
  if [ -n "${DATA_ROOT:-}" ]; then
    candidate="$DATA_ROOT/$dataset"
    [ -f "$candidate/$dataset.csv" ] || {
      log_error "missing $candidate/$dataset.csv"
      return 1
    }
    printf '%s\n' "$candidate"
    return
  fi
  for candidate in \
    "$ROOT/datasets/$dataset" \
    "$ROOT/../datasets/$dataset" \
    "$ROOT/../../../datasets/$dataset"; do
    if [ -f "$candidate/$dataset.csv" ]; then
      printf '%s\n' "$candidate"
      return
    fi
  done
  log_error "cannot find $dataset/$dataset.csv; set DATA_ROOT"
  return 1
}

run_training() {
  local dataset dataset_dir dataset_config setting lags horizon model method run_seeds seed
  local identity_root run_dir run_action run_signature purpose
  local -a allocation_args pending required_artifacts
  local total=$((${#DATASET_LIST[@]} * ${#SETTING_LIST[@]} * ${#MODEL_LIST[@]} * ${#METHOD_LIST[@]}))
  local current=0
  for dataset in "${DATASET_LIST[@]}"; do
    dataset_dir="$(resolve_dataset_dir "$dataset")"
    dataset_config="$dataset_dir/config.json"
    for setting in "${SETTING_LIST[@]}"; do
      if ! [[ "$setting" =~ ^[1-9][0-9]*:[1-9][0-9]*$ ]]; then
        log_error "invalid setting=$setting; expected L:H"
        exit 2
      fi
      lags="${setting%%:*}"
      horizon="${setting##*:}"
      for model in "${MODEL_LIST[@]}"; do
        for method in "${METHOD_LIST[@]}"; do
          current=$((current + 1))
          task_start "$current/$total configuration dataset=$dataset setting=$setting model=$model method=$method"
          identity_root="$OUT_ROOT/$dataset/${lags}_${horizon}/${model,,}/${method,,}/${DIFFICULTY_NAME,,}/${DIFFICULTY_AGGREGATION,,}/${PACING,,}/$PHASES/$INITIAL_FRACTION"
          if [ "$EXPERIMENT_MODE" = test ]; then purpose=smoke; else purpose=publication; fi
          allocation_args=(
            --identity-root "$identity_root" --project curriculum_learning --workflow curriculum
            --dataset "$dataset" --lookback "$lags" --horizon "$horizon" --backbone "$model"
            --model-config-order method,difficulty,aggregation,pacing,phases,initial_fraction
            --model-config "method=$method" --model-config "difficulty=$DIFFICULTY_NAME"
            --model-config "aggregation=$DIFFICULTY_AGGREGATION" --model-config "pacing=$PACING"
            --model-config "phases=$PHASES" --model-config "initial_fraction=$INITIAL_FRACTION"
            --pipeline-config "training.steps=$STEPS" --pipeline-config "training.batch_size=$BATCH_SIZE"
            --pipeline-config "training.learning_rate=$LEARNING_RATE"
            --pipeline-config "training.valid_eval_freq=$VALID_EVAL_FREQ"
            --pipeline-config "training.logging_eval_freq=$LOGGING_EVAL_FREQ"
            --pipeline-config "curriculum.difficulty_stride=$horizon" --pipeline-config "curriculum.quantiles=5"
            --pipeline-config "data.date_splits=0.6,0.2,0.2" --pipeline-config "data.eval_stride=$horizon"
            --runtime-config training.device=gpu --runtime-config "slurm.job_id=${SLURM_JOB_ID:-}"
            --purpose "$purpose" --mode "$EXPERIMENT_MODE" --display-name "${model}_${method}"
            --row-config method,difficulty,aggregation --column-config pacing,phases,initial_fraction
            --policy "$RUN_CONFLICT_POLICY" --skip-completed "$SKIP_COMPLETED"
            --force "$FORCE_RUN" --launch-id "$EXPERIMENT_LAUNCH_ID"
          )
          if [ "${dataset,,}" = weather ]; then
            allocation_args+=(--pipeline-config "data.missing_values=zero")
          fi
          for seed in "${SEED_LIST[@]}"; do allocation_args+=(--seed "$seed"); done
          if [ -f "$dataset_config" ]; then allocation_args+=(--input "dataset_config=$dataset_config"); fi
          if [ -n "${RUN_INDEX:-}" ]; then allocation_args+=(--run-index "$RUN_INDEX"); fi
          IFS=$'\t' read -r run_dir run_action run_signature < <(python -m pipeline.runs allocate "${allocation_args[@]}")
          if [ "$run_action" = skip ]; then
            log "skip complete configuration=$current/$total dataset=$dataset setting=$setting model=$model method=$method run=$run_dir"
            task_complete skipped
            continue
          fi
          run_seeds="$(python -m pipeline.runs pending-seeds --run-dir "$run_dir")"
          IFS=, read -ra pending <<< "$run_seeds"
          for seed in "${pending[@]}"; do python -m pipeline.runs status --run-dir "$run_dir" --status running --seed "$seed"; done
          log_section "configuration=$current/$total dataset=$dataset lags=$lags horizon=$horizon model=$model method=$method difficulty=$DIFFICULTY_NAME aggregation=$DIFFICULTY_AGGREGATION seeds=$run_seeds run=$run_dir computation_signature=$run_signature steps=$STEPS batch_size=$BATCH_SIZE phases=$PHASES initial_fraction=$INITIAL_FRACTION pacing=$PACING"
          srun --ntasks=1 python -m scripts.experiment \
            data.raw_path="$dataset_dir" data.name="$dataset" \
            data.sampling.eval_stride="$horizon" \
            task.lags="$lags" task.horizon="$horizon" \
            model.name="$model" model.path="$model" \
            training.batch_size="$BATCH_SIZE" training.steps="$STEPS" \
            training.lr="$LEARNING_RATE" \
            training.valid_eval_freq="$VALID_EVAL_FREQ" \
            training.logging_eval_freq="$LOGGING_EVAL_FREQ" \
            curriculum.method="$method" curriculum.difficulty.name="$DIFFICULTY_NAME" \
            curriculum.difficulty.aggregation="$DIFFICULTY_AGGREGATION" \
            curriculum.difficulty.stride="$horizon" \
            curriculum.schedule.phases="$PHASES" \
            curriculum.schedule.initial_fraction="$INITIAL_FRACTION" \
            curriculum.schedule.pacing="$PACING" \
            experiment.seeds="[$run_seeds]" \
            output.dir="$run_dir" output.name= \
            hydra.run.dir="$run_dir/hydra/$EXPERIMENT_LAUNCH_ID"
          required_artifacts=()
          for seed in "${pending[@]}"; do
            if [ ! -s "$run_dir/seed_$seed/results.json" ] || [ ! -s "$run_dir/seed_$seed/all_losses.pt" ]; then
              log_error "training completed without required results in $run_dir/seed_$seed"
              exit 1
            fi
            python -m pipeline.runs status --run-dir "$run_dir" --status ready --seed "$seed" \
              --artifact "seed_$seed/results.json" --artifact "seed_$seed/all_losses.pt"
          done
          for seed in "${SEED_LIST[@]}"; do
            required_artifacts+=(--artifact "seed_$seed/results.json" --artifact "seed_$seed/all_losses.pt")
          done
          python -m pipeline.runs ready --run-dir "$run_dir" "${required_artifacts[@]}"
          python -m pipeline.runs complete --run-dir "$run_dir" --launch-id "$EXPERIMENT_LAUNCH_ID"
          task_complete success
        done
      done
    done
  done
}

run_tables() {
  local model method split metric methods_csv pair table_settings
  local current=0
  local total=$((1 + ${#MODEL_LIST[@]} * 3))
  local -a table_methods table_selection_args
  table_selection_args=(--config-policy "$TABLE_CONFIG_POLICY" --repeat-policy "$TABLE_REPEAT_POLICY")
  if [ -n "${TABLE_PIPELINE_CONFIGS:-}" ]; then
    for pair in ${TABLE_PIPELINE_CONFIGS}; do table_selection_args+=(--pipeline-config "$pair"); done
  fi
  if [ -n "${TABLE_PURPOSE:-}" ]; then table_selection_args+=(--purpose "$TABLE_PURPOSE"); fi
  table_settings="$(IFS=,; echo "${SETTING_LIST[*]//:/_}")"
  log_section "tables input=$OUT_ROOT output=$REPORT_ROOT"
  current=$((current + 1))
  task_start "$current/$total table kind=summary"
  srun --ntasks=1 python -m scripts.summarize \
    "$OUT_ROOT" --output-dir "$REPORT_ROOT" "${table_selection_args[@]}"
  task_complete success
  for model in "${MODEL_LIST[@]}"; do
    table_methods=()
    for method in "${METHOD_LIST[@]}"; do
      table_methods+=("${model}_${method}")
    done
    methods_csv="$(IFS=,; echo "${table_methods[*]}")"
    for split in test1; do
      for metric in mse user_mean_mse w10_mse; do
        log "table model=$model split=$split metric=$metric"
        current=$((current + 1))
        task_start "$current/$total table model=$model split=$split metric=$metric"
        srun --ntasks=1 python -m scripts.report \
          "$OUT_ROOT" --split "$split" --metric "$metric" \
          --datasets "$(IFS=,; echo "${DATASET_LIST[*]}")" \
          --settings "$table_settings" \
          --methods "$methods_csv" --reference "${model}_uniform" \
          --show-std \
          "${table_selection_args[@]}" \
          --output "$REPORT_ROOT/results_${model}_${split}_${metric}.tex"
        task_complete success
      done
    done
  done
}

TABLE_REQUIRED_OUTPUTS=("$REPORT_ROOT/summary.json")
for model in "${MODEL_LIST[@]}"; do
  for metric in mse user_mean_mse w10_mse; do
    TABLE_REQUIRED_OUTPUTS+=("$REPORT_ROOT/results_${model}_test1_${metric}.tex")
  done
done

log_section "workflow start kind=curriculum experiment_mode=$EXPERIMENT_MODE stages=$STAGES_SPEC skip_completed=$SKIP_COMPLETED datasets=$DATASETS_SPEC settings=$SETTINGS_SPEC models=$MODELS_SPEC methods=$METHODS_SPEC seeds=$SEEDS_SPEC"
source "$ROOT/src/slurm/stage_train.sh"
source "$ROOT/src/slurm/stage_tables.sh"
log_section "workflow done kind=curriculum output=$OUT_ROOT"
