# TB-US-001: Add CLI arguments, evaluation, and run tracking to the GSM8K training pipeline

**Status**: In Progress
**Created**: 2026-06-06
**Author**: Jesse Eversole
**Commit hash(es)**: a908237 (implementation)

## Story

As a researcher running my first PEFT fine-tune on TrainingBench, I want
to drive `training/math/train.py` from the command line, see eval
metrics during training, and have each run logged automatically — so I
can vary hyperparameters and compare runs without editing source code
between experiments.

## Background

`training/math/train.py` was committed at project setup
(commit `d540c63`, "feat: Add complete GSM8K training pipeline with
QLoRA") as a single-purpose script. Every knob is a module-level
constant: `BASE_MODEL`, `DATASET_PATH`, `OUTPUT_DIR`, `LORA_R`,
`LORA_ALPHA`, `LORA_DROPOUT`, `BATCH_SIZE`, `GRADIENT_ACCUMULATION_STEPS`,
`LEARNING_RATE`, `NUM_EPOCHS`, `MAX_LENGTH`, `WARMUP_STEPS`, `SAVE_STEPS`,
`LOGGING_STEPS`, `USE_FULL_DATASET`. To compare two hyperparameter
sweeps you currently have to edit the file between runs.

The script also has no evaluation pass during training — it never looks
at the dataset's `test` split — and produces no record of a run beyond
the Trainer's own logs in stdout and `experiments/logs/`.

This story brings the pipeline up to the level a researcher would
expect from a CLI training tool: every meaningful knob exposed as a
flag, eval against the held-out split during training, and per-run
metadata captured to a structured log file so multiple runs can be
compared after the fact.

This is the first user story exercising the change-management
methodology for TrainingBench (see `docs/user-stories/template.md`).

## Requirements

- [x] R1: `training/math/train.py` accepts CLI arguments for every
      currently-hard-coded knob: base model, dataset path, output dir,
      LoRA rank / alpha / dropout / target modules, batch size,
      gradient accumulation, learning rate, number of epochs, max
      sequence length, warmup steps, save steps, logging steps, and
      a way to use a subset of the training data for smoke tests.
- [x] R2: Each CLI argument has a default that matches the value the
      original committed script used, so the existing behaviour is
      reproducible by running the script with no arguments.
- [x] R3: When the dataset directory contains a `test` split, the
      training loop evaluates against it on a configurable cadence.
      When there is no `test` split, training continues without
      evaluation rather than failing.
- [x] R4: CLI flags also cap eval samples (e.g. `--max-eval-samples`)
      so a quick smoke test doesn't pay for full-eval at every step.
- [x] R5: When `scripts/training_tracker_callback.py` is importable,
      training runs are recorded via the `TrainingTrackerCallback`
      under `--run-name`. When it is not importable, training proceeds
      without tracking and prints a single visible warning at startup
      — the pipeline does not hard-fail on a missing optional
      dependency.
- [x] R6: `scripts/training_tracker_callback.py` (the standalone-mode
      tracker callback) is tracked in git, since R5 depends on it.

## Acceptance Criteria

- [x] AC1: `python training/math/train.py --help` lists every CLI
      flag with a brief description and the same default the
      pre-refactor module constants had. *(Verified by inspection of
      the argparse definitions in main() against the constants in
      d540c63. Not yet exercised against an installed environment.)*
- [x] AC2: Running with no arguments produces the same training
      configuration as the pre-refactor script did (regression check
      against `d540c63`). *(Verified by inspection: every argparse
      default matches the original module constant.)*
- [ ] AC3: Running with `--max-train-samples 50 --max-eval-samples 25
      --num-epochs 1` completes a smoke train+eval loop quickly on the
      target hardware, with eval metrics printed at least once.
      *(Requires runtime verification with the training stack
      installed; not yet performed.)*
- [ ] AC4: Running with `--run-name <some-name>` produces a structured
      log file under the tracker's log directory containing at minimum
      run name, start time, end time, final metrics, and the resolved
      configuration. *(Requires runtime verification; not yet
      performed.)*
- [x] AC5: Renaming or removing `scripts/training_tracker_callback.py`
      temporarily reproduces the "tracker not available" warning and
      training still runs to completion. *(Structurally guaranteed by
      the try/except ImportError block at train.py lines 38-43 and the
      TRACKER_AVAILABLE gate at line 349. Not yet exercised end-to-end
      at runtime.)*

## Design Notes

- The CLI uses `argparse` (already in the standard library) rather
  than adding a dependency on `click`/`typer`. The training-pipeline
  audience is comfortable with argparse and avoiding a dependency
  matters for the OSS release.
- The tracker integration is intentionally a soft dependency — guarded
  by a `try/except ImportError`. The script remains useful for someone
  who only wants to fine-tune without any run-tracking layer.
- LoRA / training defaults are kept identical to the original script.
  Tuning the defaults themselves is out of scope; this story changes
  surface area, not policy.
- The `--use-full-dataset` flag is retained as a boolean for backward
  compatibility, even though `--max-train-samples N` makes it
  redundant.

## Out of Scope

- `scripts/test_adapter.py`: an adjacent tool for evaluating a trained
  adapter against a fixed set of sample queries. `train.py` only refers
  to it as a suggested next step in a print statement, so it is not a
  hard dependency. Track separately (candidate: TB-US-002).
- Generalising beyond the math/GSM8K domain. The same refactor pattern
  could be applied to other training scripts (`legal`, `medical`,
  `agriculture` once those exist), but this story is scoped to
  `training/math/train.py` only.
- Switching the dataset format or the prompt template format. The
  Llama-3 chat-format prompt and the GSM8K loader stay unchanged.
- Multi-GPU / DeepSpeed / FSDP. Single-GPU QLoRA stays the assumed
  deployment target for this script.

## Completion Notes

Implementation landed in commit `a908237`. R1-R6 all satisfied by code
review. AC1, AC2, and AC5 verified by inspection. AC3 and AC4 require
an environment with `torch`, `transformers`, `peft`, `bitsandbytes`,
and the GSM8K dataset installed; mark them when those runtime
verifications are done and promote Status to Completed.

## Related

- `training/math/train.py` — file refactored in `a908237`
- `scripts/training_tracker_callback.py` — soft dependency, first
  tracked in `a908237`
- Commit `d540c63` ("feat: Add complete GSM8K training pipeline with
  QLoRA") — the baseline this refactors
- Commit `a908237` — the implementation
- `docs/user-stories/template.md` — the story format
- `docs/user-stories/example.md` — the worked example
- TB-US-002 — the install story that will exercise this story's AC3
  and AC4 as a side effect of verifying the install
