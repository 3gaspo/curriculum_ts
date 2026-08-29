# Pending updates

- 2026-08-28: Established the current project tree as the initial `main`
  history of `3gaspo/curriculum_ts`, preserving `AGENTS.md` as ignored local
  configuration. Affected contracts: repository ownership and publication
  only. The dependency-free transfer/publication test passed two checks with
  the minimal shared Python. README, LaTeX, artifact contracts, and scientific
  rerun requirements are unchanged. Deferred integration: replace or attach
  the DGX checkout to this origin before its next code synchronization or run.

- 2026-08-28: Reconciled the five-view documentation contract by reducing the
  public README to a 107-line goal/setup/execution quickstart and leaving
  formulation, architecture, full Slurm coverage, protocol, and evidence in
  their designated views. The validator now enforces README ownership, owner
  links, the complete DGX-front catalog, and absence of stale LaTeX artifacts.
  Removed the erroneous literal `$outDir` build tree. The shared six-project
  documentation check passed; the current three-page guideline was rebuilt
  and visually inspected, and the two-page method note remains current. No
  scientific rerun or executive-summary change is required. Deferred
  integration: preview code sync on DGX, inspect every `*deleting` line, then
  perform the real sync.

Last successful maintenance: 2026-08-11 10:45 +02:00.

## Pending

- 2026-08-28: Made result transfer tiered: sync now defaults to aggregate
  lightweight analysis artifacts, `detailed` adds row-level/per-run
  diagnostics, and `full` explicitly retrieves binary recovery payloads;
  publication defaults to the same lightweight scope and offers non-binary
  `detailed` output. Affected contracts: both result-transfer scripts, README,
  and focused transfer checks. Git Bash syntax passed for both scripts, the
  two transfer-tier checks passed, all nine active publisher copies were
  byte-identical, and the existing Slurm/publisher checks passed. No
  scientific rerun or LaTeX update is required. Deferred integration: exercise
  each sync tier against Selena and inspect one detailed publication on DGX.

- 2026-08-27: Added a stable oversized-sample header recording the first UTC
  time and file-size reason that the associated artifact became stale on Git.
  Affected contracts: `publish_job.sh`, README publication guidance, and the
  shared focused publisher regressions. All five publisher checks passed; Git
  Bash syntax and byte parity passed for all nine active publisher copies. No
  scientific rerun or LaTeX change is required. Deferred integration: exercise
  one real oversized publication and inspect the generated header on DGX.

Maintenance 2026-08-27: direct CSV-loading, configuration, workflow, README,
guideline, status, and placeholder inspection confirmed the current contract
and no completed artifacts. The complementary result-table script exited
successfully in the thesis runtime. The three-page guideline compiled in two
clean passes and every rendered page passed visual inspection. Publisher Bash
syntax, byte parity, and the representative regression passed. The first real
Selena smoke/lifecycle and oversized publication remain pending.

- 2026-08-27: Hardened the thesis-standard publisher against GitHub's
  100 MB file limit. Before staging, each selected non-excluded file above
  100,000,000 bytes is excluded literally and represented by
  `<original>.sample.txt`; text samples contain source metadata and the first
  10% capped at 10,000,000 bytes, while binary samples retain metadata only.
  Affected contracts: publisher, README, shared publication guidance, and the
  five maintained publisher regressions where present. Git Bash syntax passed
  for all nine active copies, all five focused publisher checks passed, and
  both publisher and test copies are byte-identical. No scientific rerun,
  artifact migration, or LaTeX change is required. Deferred integration:
  exercise one real oversized log publication on DGX.

- 2026-08-26: Added QoS `an_preemptable` to the Selena curriculum front and
  aligned the shared scheduler contract, README, and focused workflow check.
  Both direct workflow tests passed. No scientific configuration, artifact
  contract, result, or rerun requirement changed. Deferred integration: mirror
  the updated DGX tree to Selena before the next overflow submission.

- 2026-08-26: Standardized the validated Selena transfer/publication flow.
  `sync_results_to_dgx.sh` now runs on DGX and pulls the isolated Selena trees;
  unscoped publication includes paired `logs_selena/` and lightweight
  `outputs_selena/` under the existing heavy-payload exclusions, while numeric
  job-ID mode remains standard-log-only. Affected contracts: result helper,
  publisher, focused workflow/publisher regressions, README, shared guidance,
  and cluster handoff. Bash syntax passed for all 15 maintained scripts, all
  five publisher checks and the curriculum workflow checks passed, and the
  nine publisher copies plus five suffix-result helpers are each byte-identical.
  The README changed; the guideline's all-log/lightweight-output wording remains
  accurate, so LaTeX/PDF files are unchanged. No scientific rerun or migration
  is required. Deferred integration: exercise
  one real pull and unscoped publication after a Selena test job.

- 2026-08-26: Added the matching Selena curriculum front and made runtime
  roots explicit. `LOGS_ROOT` and `OUTPUTS_ROOT` default to `logs/` and
  `outputs/` but remain overridable; the Selena front selects `logs_selena/`
  and `outputs_selena/` without changing stages or scientific configuration.
  Code sync protects both artifact namespaces plus cluster-local dependency
  state, and result sync returns only the Selena-named trees without deletion.
  Affected contracts: runner, DGX/Selena fronts, sync pair, ignored
  placeholders, workflow regression, README, local/shared guidance, cluster
  handoff, and experiment-guideline source/PDF. Git Bash syntax and both
  focused workflow tests passed; two LaTeX passes produced three pages, all
  visually inspected without clipping or overlap. No scientific rerun or
  artifact migration is required. Deferred integration: submit one Selena
  test front and exercise both sync directions on the real clusters.

- 2026-08-17: Simplify `publish_job.sh`: a numeric job ID now selects only its
  exact stdout/stderr pair, while an omitted ID stages the `logs/` and
  lightweight `outputs/` parent trees directly. Publisher, focused contract
  test, README, and shared guidance changed. The project publisher contract
  test and Git Bash syntax passed, and all nine copies have matching SHA-256
  hashes. No scientific rerun or artifact migration is required. Deferred
  maintenance: reconcile and render the experiment guideline; retain the
  existing real-cluster publisher integration check.

- 2026-08-16: Adopt the thesis-standard `publish_job.sh`: source the proxy and
  fast-forward pull `origin/main` before artifact selection, staging, or commit,
  then publish only the lightweight selected paths. Affected contracts:
  publisher, focused contract test, README, and shared experiment guidance.
  Checks passed: Bash syntax for all nine standard copies, matching SHA-256
  hashes, and the curriculum publisher contract test. No scientific rerun or
  artifact migration is required. Deferred maintenance: reconcile
  `latex/experiment_guideline.tex` and exercise one real cluster publish with a
  remote update present.

- 2026-08-12: Synchronize Adaptation's terminal lifecycle: remove automatic
  publisher submission, add the manual root `publish_job.sh`, restrict overall
  manifests to `not_run|running|interrupted|completed`, and allow tables to
  consume seed-ready artifacts only from their own active launch. Affected
  files/contracts: manifest helper, curriculum runner, summary/table readers,
  publisher files, focused tests, README, and parent experiment guidance.
  Checks passed: 13 focused lifecycle/publisher/Slurm/summary/table tests and
  Bash syntax for the runner and manual publisher. No scientific rerun or
  artifact migration is required. Deferred maintenance: reconcile and render
  `latex/experiment_guideline.tex`; cluster-check one successful and one
  failed/cancelled launch, then run the manual publisher once.
  Maintenance 2026-08-13: direct inspection confirmed the four-state overall
  manifest, seed-only `ready`, same-launch table/summary selection, and final
  exit promotion. Schedule, Torch curriculum, and dataset-configuration tests
  passed in the shared thesis runtime. The README and guideline now describe
  the exact lifecycle and manual publisher; two pdfLaTeX passes completed
  without warnings and all three rendered pages passed visual inspection. The
  previously successful lifecycle/publisher/Slurm/result tests were not
  repeated because the three complementary checks cover different boundaries.
  Remaining blocker: observe one successful and one failed/cancelled cluster
  launch, then run `publish_job.sh` once.

- 2026-08-13: Complete every successful curriculum configuration immediately,
  preserve it across later workflow failure, interrupt only unfinished runs,
  and retain per-seed artifact lists. Affected contracts: shared manifest
  helper, runner, tests, README, and experiment guideline. Checks passed: 11
  lifecycle tests, publisher and workflow contracts, Python AST parsing, Bash
  syntax, clean LaTeX compilation, and visual inspection of all three PDF
  pages. No artifact migration, scientific rerun, or schema bump is required.
  Remaining cluster work: exercise successful and failed/cancelled launches and
  run the manual publisher once.

Maintenance 2026-08-16: no source, configuration, artifact, documentation, or
cluster-handoff file changed after the previous pass. Direct inspection again
found completed-only reuse, seed-ready state restricted to the owning launch,
and the manual publisher contract. The already successful schedule, Torch
curriculum, dataset-configuration, and PDF checks were not repeated because
there is no changed integration boundary. Live successful/failed launch
observations and one manual publisher run remain the sole blocker; no
scientific rerun is required.

Maintenance 2026-08-17: direct inspection found no new source, artifact, or
cluster-status change and reconfirmed completed-only reuse and same-launch ready
selection. The README was current; the experiment guideline was reconciled with
the canonical proxy-first, fast-forward-pull publisher. Bash syntax passed for
all nine byte-identical copies. Three pdfLaTeX passes completed with a clean
log, and all three rendered guideline pages passed visual inspection. The prior
schedule, Torch, dataset, and lifecycle checks were not repeated because those
boundaries did not change. Live successful/failed launch observations and one
real publisher run remain the blockers; no scientific rerun is required.

Maintenance 2026-08-18: direct inspection confirmed that the shared manifest
helper is byte-identical to the canonical schema-1 copies and that this project
has no upstream selector or synchronized run requiring migration; the already
successful 13 focused manifest tests therefore close that standalone entry.
The README was current, and the experiment guideline was corrected to describe
exact-log job publication and unscoped lightweight-tree publication. Git Bash
syntax passed for all nine byte-identical publishers. Curriculum/Torch/data
tests were not repeated because those boundaries did not change.
Three pdfLaTeX passes completed with a clean log, and all three rendered
guideline pages passed visual inspection. Live successful/failed launch
observations and one real publisher run remain the
blockers; no scientific rerun is required.

Maintenance 2026-08-19: direct inspection found no source, configuration,
artifact, or cluster-status change. The README and guideline remain current,
and all nine publisher copies remain byte-identical at SHA-256
`0A9E87E51517B9F5816BB92CDE726B9E383AB6B8A70DC251FEF429BF7B53B45C`.
Curriculum/Torch/data, lifecycle, Bash-syntax, and PDF checks were not repeated
because no corresponding boundary changed. Live successful and failed or
cancelled launch observations plus one real publisher run remain the blockers;
no scientific rerun is required.

Maintenance 2026-08-20: direct timestamp, source, artifact, and cluster-handoff
inspection found no change after the previous pass. The README and guideline
remain current, and the publisher remains byte-identical across all nine
projects at SHA-256
`0A9E87E51517B9F5816BB92CDE726B9E383AB6B8A70DC251FEF429BF7B53B45C`.
Curriculum/Torch/data, lifecycle, Bash-syntax, and PDF checks were deliberately
skipped because no corresponding integration boundary changed. Live successful
and failed or cancelled launch observations plus one real publisher run remain
the blockers; no scientific rerun is required.

Maintenance 2026-08-23: direct inspection confirmed the shared nested
selection and deterministic latest-run behavior, and the helper plus focused
test file are byte-identical to the other four maintained copies. The
complementary synthetic `src/tests/test_results_table.py` consumer passed in
the shared thesis runtime, covering manifest discovery through table rendering.
README selection documentation is current; no protocol, LaTeX, result claim,
artifact migration, or rerun changed. The selector entry is resolved, while
the first cluster workflow, live lifecycle observations, and publisher check
remain pending.

Maintenance 2026-08-24: direct package, import, configuration, Slurm, test,
artifact, and handoff inspection confirmed the isolated curriculum treatment,
cohesive transferred owners, and absence of compatibility paths. As
complementary coverage, the relocated packages plus both experiment and report
script modules imported together in the shared thesis runtime. The attempted
Hydra CLI front was inapplicable because Hydra is absent from that documented
runtime; no experiment started. README and LaTeX remain current, and the
reorganization and guidance entries are resolved without a rerun. The first
cluster workflow, live lifecycle observations, and publisher check remain
pending.

## 2026-08-24 — TimeTensors-aligned data boundaries and pinned backbones

- Behavior and affected contracts: split the local TimeTensors-derived data
  implementation into matching core, sampling, frames, I/O, split, statistic,
  and loader owners without importing the sibling repository. Replaced flat
  DLinear/PatchTST files with the pinned source-adapted packages shared by their
  active consumers.
- Focused checks and outcomes: Python compilation, curriculum sampler tests,
  package/data-layout guards, a synthetic loader build, and direct DLinear and
  PatchTST forwards passed. Hash comparison confirmed exact external snapshots.
- Deferred integration: no prepared Hydra/OmegaConf environment or remote
  training run was used. The first cluster curriculum smoke remains required.
- README/LaTeX and reruns: README and local guidance document the new owners and
  external provenance; reconcile the guideline during maintenance. No completed
  curriculum result exists, so all future DLinear/PatchTST runs naturally use
  the current contract.

Maintenance 2026-08-25: direct package, data-boundary, workflow, artifact,
documentation, and handoff inspection found no completed curriculum result and
confirmed the TimeTensors-aligned owners and pinned backbones. The complementary
`src/tests/test_dataset_config.py` check passed (1 test), covering shared and
project override precedence after the data split. The full smoke was not run
because the documented runtime lacks Hydra and OmegaConf; it would not add a
dependency-light boundary. The README was already current. The guideline now
records the implementation path, exact external provenance, and experiment
pipeline; two pdfLaTeX passes produced a clean three-page PDF and all pages
passed visual inspection. The empty archive-only entry is resolved and removed.
The first cluster smoke, live lifecycle observations, and publisher check remain
pending.

Maintenance 2026-08-26: direct assertion, orchestrator/stage, README,
guideline, handoff, and placeholder inspection confirmed that the new
single-task checks match the existing three stage launches. Dependency-light
compilation of `src/tests/test_slurm_workflow.py` passed as complementary
coverage; the focused workflow and workspace-wide Bash checks were not
repeated. The assertion-only entry is resolved. The first cluster smoke, live
lifecycle observations, and publisher check remain pending.

## 2026-08-27 — Direct CSV loading and replacement exclusions

- Behavior and affected contracts: Curriculum Learning now reads the selected
  CSV into memory, never creates or consumes dataset `.pt` caches, applies
  scoped/run `drop_users` by replacement, and no longer disables scheduler
  requeue in its Selena front.
- Focused checks completed: dataset-config, Slurm workflow, and five-step
  end-to-end curriculum smoke checks passed; changed Python compiled and all
  active experiment Bash/Slurm syntax passed.
- Deferred integration: run the first real Selena smoke and observe the live
  lifecycle; no remote training was launched locally.
- README/LaTeX and reruns: README, guidance, and guideline source document
  direct CSV loading and replacement precedence; re-render during maintenance.
  No completed result exists, so the first cluster run naturally uses the new
  contract.

## 2026-08-28 — Report-only default artifact transfer

- Behavior and affected contracts: lightweight result sync and publication now
  select logs plus only `outputs*/reports/`, without traversing run or
  diagnostics trees. Detailed/full tiers retain explicit deeper transfer. The
  curriculum table stage now writes aggregate artifacts to
  `outputs/reports/curriculum/<mode>/`.
- Focused check completed: the shared transfer-tier contract check passed in
  all six active experiment repositories (13 tests total), including anchored
  report filtering and publisher path selection.
- Deferred integration: exercise one real DGX pull and manual publisher run;
  no synchronization, commit, or push was performed locally.
- README/LaTeX and reruns: README and guideline source describe the compact
  report hierarchy; re-render the guideline during maintenance. Existing
  training does not require rerunning, but regenerate curriculum reports in
  their new path before lightweight transfer.

## 2026-08-29 — Terminal Slurm completion records

- Behavior and affected contracts: every curriculum configuration and table
  subtask now records a terminal success, skipped, or failed state; both stages
  record terminal states; and the exit trap always records the authoritative
  workflow status after launch-manifest finalization.
- Focused check completed: `src/tests/test_slurm_workflow.py` passed (3 tests)
  in the shared thesis runtime.
- Deferred integration: observe the new markers in one successful and one
  failed cluster job; no experiment was launched locally.
- README/LaTeX and reruns: public and scientific behavior are unchanged, so no
  documentation update or result rerun is required. Historical logs remain
  valid but naturally do not gain terminal markers retroactively.

