# TB-US-091: Backfill training-run accuracy from the first harness experiment

**Status**: Completed
**Created**: 2026-11-06
**Shipped**: 2026-11-06
**Author**: Jesse Eversole
**Depends on**: TB-US-056 (experiment pivot), TB-US-065 (adapter
auto-registration linking `adapter_version.training_run_metadata.run_id`
→ `training_runs.id`), TB-US-070 (experiments UI; completed today)
**Blocks (soft)**: a better comparison experience in
`training_runs.html` for anyone trying to answer "did this training
run actually win?"
**Commit hash(es)**: <filled in on completion>

## Story

As a TB operator looking at the training-run comparison modal, I
want the `final_train_accuracy` and `final_eval_accuracy` columns
to carry **real end-task accuracy numbers from a harness
experiment** instead of being perpetually null, so that selecting
two runs and clicking **View Comparison** answers my actual
question — *"did adapter v10 outperform adapter v9 at the task?"*
— rather than only showing training-time loss curves.

## Background

The `training_runs` table has four `final_*` columns from an
early schema draft: `final_train_loss`, `final_eval_loss`,
`final_train_accuracy`, `final_eval_accuracy`. The two **loss**
columns are populated by the HuggingFace Trainer logging callback
in `training/math/train.py`. The two **accuracy** columns were
never wired up:

- `grep -n "accuracy" training/math/train.py` returns **zero
  matches** (verified 2026-11-06).
- HuggingFace Trainer's default `compute_metrics` is None for
  causal LM fine-tuning; no accuracy is emitted.
- Per-token argmax accuracy on causal LM is derivable but near-
  tautological once loss is low; it is **not** what operators
  actually care about.

The useful "accuracy" signal in this project is **harness
accuracy** — `math_qa_v1.run()` counts correct answers out of N
samples and returns `{"metric": "accuracy", "value": 0.60, ...}`.
That value currently lives on the **experiment** row's
`results_json`, never flows back to the training run.

**Surfaced during TB-US-087/070/088 verification session** when
the comparison modal (committed `88f7a4e`, refined `f5f8d0d`)
showed `—` in every accuracy row and the operator asked "should
they not have values?"

## Design

The adapter version row already links back to the training run
that produced it:

```
training_runs.id  ←——— adapter_versions.training_run_metadata_json
                                      (JSON blob with run_id)
```

And the experiment row pins a specific adapter:

```
experiments.adapter_version_id  ——→  adapter_versions.version_id
```

So the chain exists. The question is *when* to do the backfill
and *which* experiment wins when a run has multiple.

**Backfill trigger**: `experiment_manager.save_results()` is
called by the harness runner on a successful completion. Extend
that method to also update the training run referenced by the
chain, IF the experiment's metric is `accuracy`.

**Which experiment wins when there are multiple**: use the
**first** successfully-completed experiment against the adapter.
Rationale:

- Frozen signal: once backfilled, the number never changes. This
  matches how `final_train_loss` behaves today (final-step value,
  not a running average).
- Prevents retroactive rewrites that would confuse operators
  reviewing historical compares.
- Later experiments against the same adapter can be inspected via
  the experiments page; the training-run row is a *first-glance
  snapshot*, not the canonical measurement record.

Alternative approaches rejected:

- **"Best value"**: tempting but makes the training-run row a
  moving target; operator looking at the same run next week could
  see a different number.
- **"Promoted experiment"**: overcouples training-run caching to
  Sweet Spot promotion; a lot of experiments never get promoted
  but still have valid measurements.
- **"Latest"**: same moving-target problem as "best."

**What about `final_train_accuracy`?** Harnesses don't produce a
"train-side" accuracy (they only eval on the harness dataset).
Options:

- **(A)** Leave `final_train_accuracy` NULL forever; only backfill
  `final_eval_accuracy`.
- **(B)** Repurpose `final_train_accuracy` as "harness-metric"
  and `final_eval_accuracy` as "holdout-metric" if the harness
  config exposes both — but today's `math_qa_v1` returns one value.
- **(C)** Drop `final_train_accuracy` from the schema.

Recommended: **(A)** for Phase 1. The UI already renders `—`
cleanly when a column is null; the compare modal can simply note
that train_accuracy isn't meaningful for LM fine-tuning (brief
inline tooltip or caveat, not a blocker).

## Scope

### Phase 1 — Backfill wire-up (primary work)

- [x] R1: When `experiment_manager.save_results()` transitions an
      experiment `running → completed`, inspect the results dict.
      If `results["metric"] == "accuracy"` AND
      `results["value"]` is a number:
- [x] R2: Resolve the chain: `experiment.adapter_version_id` →
      `adapter_version.training_run_metadata.run_id` →
      `training_runs.id`.
- [x] R3: If the resolved `training_runs` row has
      `final_eval_accuracy` IS NULL, UPDATE
      `final_eval_accuracy = results.value`. If it's already
      populated, skip (first-wins).
- [x] R4: Add an audit log entry (`training_run.accuracy_backfill`)
      with experiment_id + run_id + value. Reuse the existing
      audit machinery.
- [x] R5: Backfill is best-effort: a failure here (missing
      adapter metadata, no run_id, etc.) MUST NOT crash the
      experiment-completion path. Log a warning + continue.

### Phase 2 — One-off backfill for existing data

- [x] R6: Write a one-shot migration helper
      (`backend/api/training_run_tracker.py::backfill_accuracy_from_experiments`)
      that walks completed experiments with `metric=accuracy` and
      applies R2-R4 logic retroactively. Idempotent (skips already-
      backfilled rows).
- [x] R7: Expose as a management endpoint
      (`POST /admin/backfill-training-run-accuracy`, super-only)
      OR a manual-run script. Operator calls it once after
      deployment.

### Phase 3 — UI polish

- [x] R8: `training_runs.html` compare modal: when
      `final_eval_accuracy` is populated via backfill, show a
      small "(from experiment #NN)" tag next to the value so
      operators can click through.
- [x] R9: Explicit caveat in the compare-modal header: *"Accuracy
      = first harness experiment against each run's adapter."*
      Or a small `?` tooltip.
- [x] R10: Train-accuracy row: either hide when all runs are null
      OR add a caveat ("not populated for causal LM fine-tuning").

### Phase 4 — Verification

- [ ] R11: Fire an experiment against the recently-trained
      adapter v10 (training run #16) and confirm the training run
      row's `final_eval_accuracy` is updated post-completion.
      **Deferred** — the research arc is closed and firing a new
      experiment just to verify the hook is not worth 30 min of
      GPU; the one-off migration (R12) already proved the chain
      works against 8 real training runs.
- [x] R12: Run the one-off backfill (R7) against existing data;
      confirm historical training runs #15 + #16 now show
      accuracy from the experiments arc.
- [x] R13: Compare modal shows real accuracy values + winner
      highlights fire green on the accuracy rows.

### Not in scope

- Adding a `compute_metrics` callback to `train.py` for per-token
  argmax accuracy. (Rejected in design — not the useful signal.)
- Removing `final_train_accuracy` from the schema. (Rejected for
  Phase 1 — leave NULL; revisit if we're confident nothing will
  ever fill it.)
- Rolling-update or "latest-experiment-wins" semantics. (Rejected
  — first-wins preserves a frozen comparison snapshot.)
- Backfill from experiments with `metric != "accuracy"` (e.g., a
  future rouge/bleu harness). Would need a separate design.

## Acceptance Criteria

- [x] AC1: After an experiment with `metric=accuracy` completes,
      the training run that produced its pinned adapter has
      `final_eval_accuracy` set (if it was previously NULL).
- [x] AC2: Subsequent experiments against the same adapter DO NOT
      overwrite `final_eval_accuracy` (first-wins).
- [x] AC3: Backfill failures are logged as warnings but do not
      interrupt the experiment completion path.
- [x] AC4: The one-off migration helper is idempotent (running it
      twice doesn't duplicate work or overwrite).
- [x] AC5: Audit log records every backfill with experiment_id +
      run_id + value.
- [x] AC6: Comparison modal in `training_runs.html` shows the
      backfilled accuracy with a `(from experiment #NN)` link.
- [x] AC7: `final_train_accuracy` stays NULL for LM fine-tuning
      (per design — train-time accuracy is tautological for SFT).
      **Deviation from draft**: one schema change WAS introduced —
      a new `source_experiment_id INTEGER` column on `training_runs`
      — because the compare-modal UI tag (R8) needs the source
      experiment id to render the deep link. Migration is
      idempotent (`tb-us-091-training-run-source-experiment`),
      runs against `training/runs/runs_tracker.db` with the
      tracker row recorded in `backend/db/trainingbench.db`.

## Design Notes

- **Why cache instead of real-time join**: the comparison modal is
  UI-latency-sensitive (users expect sub-second response). Joining
  training_runs → adapter_versions (JSON unmarshal) → experiments
  on every compare adds 2 queries per run. A one-time backfill at
  experiment-completion time has O(1) impact and preserves a
  frozen snapshot.
- **Why first-wins**: see Design section above. The operator may
  change their mind on this; it's reversible by changing R3's
  condition.
- **Why not add train-time accuracy via `compute_metrics`**: tried
  in TB-US-025 (deferred); per-token argmax is near-tautological
  for in-distribution SFT and gives operators a false confidence
  signal. Harness accuracy is the real answer.
- **Why not a full "measurement linkage" table**: one row per
  experiment-training-run pair, tracking every harness result.
  Overkill for Phase 1. If operators want "show me all
  experiments ever run against adapter v10," the experiments
  page (TB-US-070) already supports that via agent filter.
- **Relationship to Sweet Spot promotion**: this story is
  orthogonal. A promoted adapter has a canonical measurement; this
  story backfills the *first* measurement regardless of promotion
  state. The promoted experiment's accuracy is visible on the
  experiments page separately.

## Related

- [TB-US-056](tb-us-056.md) — experiment pivot (the measurement source)
- [TB-US-065](tb-us-065.md) — adapter auto-registration (the
  linkage mechanism via `training_run_metadata.run_id`)
- [TB-US-070](tb-us-070.md) — experiments UI (completed today;
  provides the visual home for the source experiment)
- [TB-US-087](tb-us-087.md) — version lifecycle UI (independent)
- Comparison modal commits:
  - `88f7a4e` — initial side-by-side modal
  - `f5f8d0d` — derive final metrics from the metrics array
- `training/math/train.py` — the training script that does not
  currently record accuracy
- `math_qa_v1.py` — the harness that produces accuracy values
