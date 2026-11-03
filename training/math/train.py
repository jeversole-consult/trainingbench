#!/usr/bin/env python3
"""
QLoRA fine-tuning for GSM8K using Llama 3.1 8B.

This script fine-tunes the base Llama model on GSM8K using QLoRA (Quantized Low-Rank Adaptation)
for parameter-efficient training on consumer hardware.

Enhanced with CLI arguments, evaluation support, and training tracking.
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Optional

import torch
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    TrainingArguments,
    Trainer,
    DataCollatorForLanguageModeling,
    BitsAndBytesConfig,
    EarlyStoppingCallback,
)
from peft import (
    LoraConfig,
    get_peft_model,
    prepare_model_for_kbit_training,
)
from datasets import load_from_disk, Dataset
from tqdm import tqdm


# TB-US-078: default eval system prompt (used for formatting the GSM8K
# test split so eval-loss is on sequences comparable to the training-set
# version's `text` field). If future agents need different eval framing,
# add a CLI arg + launch-config key here.
DEFAULT_EVAL_SYSTEM_PROMPT_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "rag-seeds" / "math-example-v1" / "system-prompt.txt"
)

# Add scripts directory to path for training tracker
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

# Try to import training tracker callback
try:
    from training_tracker_callback import TrainingTrackerCallback
    TRACKER_AVAILABLE = True
except ImportError:
    TRACKER_AVAILABLE = False
    print("⚠️  Training tracker not available, training will proceed without tracking")


def _load_training_set_jsonl(path: Path) -> Dataset:
    """Load a training_set_version JSONL file into a HuggingFace Dataset.

    Each line must be a sample dict with at minimum a 'text' field — the
    fully-formed training string produced by the prep script (chat
    template already applied, system prompt baked in, assistant turn
    terminated). This function does NOT re-format; it tokenizes 'text'
    verbatim. Metadata fields (sample_id, question, answer) are carried
    through as columns but ignored by tokenization.
    """
    if not path.exists():
        print(f"Error: training-set JSONL not found at {path}")
        sys.exit(1)
    rows: list[dict] = []
    with path.open("r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as e:
                sys.exit(f"Error: malformed JSON at line {i+1} of {path}: {e}")
            if "text" not in obj:
                sys.exit(
                    f"Error: line {i+1} of {path} missing required 'text' "
                    f"field. Training-set-version JSONLs must contain a "
                    f"pre-formatted 'text' column (TB-US-078). Got keys: "
                    f"{sorted(obj.keys())}"
                )
            rows.append(obj)
    if not rows:
        sys.exit(f"Error: training-set JSONL at {path} is empty")
    return Dataset.from_list(rows)


def _format_eval_example_factory(tokenizer, system_prompt: str):
    """Return a map-fn that applies the Instruct chat template to one
    GSM8K eval example so eval-loss sequences are shaped like training.
    """
    def _fmt(example):
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": example["question"]},
            {"role": "assistant", "content": example["answer"]},
        ]
        text = tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=False
        )
        return {"text": text}
    return _fmt


def prepare_dataset(
    tokenizer,
    training_set_jsonl: Path,
    eval_dataset_hf_dir: Optional[Path],
    max_length: int = 512,
    max_train_samples: Optional[int] = None,
    max_eval_samples: Optional[int] = None,
):
    """Load training data from a training_set_version JSONL file + eval
    data from the GSM8K test split (HF Datasets dir).

    TB-US-078 wiring:
    - Training examples come from a registered training_set_version's
      sidecar JSONL. Each line's 'text' field is used verbatim.
    - Eval examples come from the GSM8K test split, chat-template-formatted
      inline with DEFAULT_EVAL_SYSTEM_PROMPT so eval-loss is comparable
      to training-loss. Eval is a reference measurement; it is NOT a
      training_set_version itself.
    - If `eval_dataset_hf_dir` is None, no eval dataset is returned (and
      early-stopping / load_best_model_at_end must be disabled upstream).
    """
    print("=" * 80)
    print("Loading dataset (TB-US-078 wiring)")
    print("=" * 80)
    print(f"Training JSONL: {training_set_jsonl}")
    print(f"Eval GSM8K dir: {eval_dataset_hf_dir}")
    print()

    # ---- Training set (JSONL from training_set_versions sidecar) ----
    train_data = _load_training_set_jsonl(Path(training_set_jsonl))
    print(f"Loaded {len(train_data)} training rows from JSONL")

    if max_train_samples and max_train_samples < len(train_data):
        print(f"Capping training set at max_train_samples={max_train_samples}")
        train_data = train_data.select(range(max_train_samples))

    # Log a sample so operators can confirm the 'text' field is what they
    # expect (chat-template-formatted, system prompt baked in, etc.).
    sample_text = train_data[0]["text"]
    print()
    print("--- training sample #0 (first 400 + last 200 chars) ---")
    print(sample_text[:400])
    print("...")
    print(sample_text[-200:])
    print("--- end sample ---")
    print()

    # ---- Eval set (GSM8K test, chat-template-formatted inline) ----
    eval_data: Optional[Dataset] = None
    if eval_dataset_hf_dir is not None:
        if not Path(eval_dataset_hf_dir).exists():
            print(f"Warning: eval dataset not found at {eval_dataset_hf_dir}; "
                  f"continuing WITHOUT eval (early stopping will be disabled)")
        else:
            hf_ds = load_from_disk(str(eval_dataset_hf_dir))
            eval_split = hf_ds.get("test")
            if eval_split is None:
                print(f"Warning: eval dataset at {eval_dataset_hf_dir} has no "
                      f"'test' split; continuing WITHOUT eval")
            else:
                if max_eval_samples and max_eval_samples < len(eval_split):
                    eval_split = eval_split.select(range(max_eval_samples))
                print(f"Loaded {len(eval_split)} eval rows from GSM8K test")
                # Load the system prompt that gets baked into each eval record
                if DEFAULT_EVAL_SYSTEM_PROMPT_PATH.exists():
                    eval_system_prompt = DEFAULT_EVAL_SYSTEM_PROMPT_PATH.read_text(
                        encoding="utf-8"
                    ).strip()
                    print(f"Eval system prompt loaded from "
                          f"{DEFAULT_EVAL_SYSTEM_PROMPT_PATH} "
                          f"({len(eval_system_prompt)} chars)")
                else:
                    eval_system_prompt = (
                        "You are a helpful math tutor. Solve the problem "
                        "step by step and end with #### <answer>."
                    )
                    print(f"Eval system prompt file missing; using built-in fallback")
                eval_data = eval_split.map(
                    _format_eval_example_factory(tokenizer, eval_system_prompt),
                    remove_columns=eval_split.column_names,
                    desc="Formatting eval examples",
                )

    # ---- Tokenize ----
    def tokenize_function(examples):
        return tokenizer(
            examples["text"],
            truncation=True,
            max_length=max_length,
            padding=False,
        )

    train_data = train_data.map(
        tokenize_function,
        batched=True,
        remove_columns=train_data.column_names,  # drops text + metadata
        desc="Tokenizing training data",
    )

    if eval_data is not None:
        eval_data = eval_data.map(
            tokenize_function,
            batched=True,
            remove_columns=["text"],
            desc="Tokenizing eval data",
        )

    return train_data, eval_data


def create_qlora_model(model_name, lora_r=16, lora_alpha=32, lora_dropout=0.05, target_modules=None):
    """Create QLoRA-configured model."""
    if target_modules is None:
        target_modules = ["q_proj", "v_proj", "k_proj", "o_proj"]

    print("=" * 80)
    print("Setting up QLoRA Configuration")
    print("=" * 80)
    print()
    print(f"Base model: {model_name}")
    print(f"LoRA rank (r): {lora_r}")
    print(f"LoRA alpha: {lora_alpha}")
    print(f"LoRA dropout: {lora_dropout}")
    print(f"Target modules: {target_modules}")
    print()

    # BitsAndBytes configuration for 4-bit quantization
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_use_double_quant=True,
    )

    # Load base model
    print("Loading base model...")
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        quantization_config=bnb_config,
        device_map="auto",
        trust_remote_code=True,
    )

    # Prepare for k-bit training
    model = prepare_model_for_kbit_training(model)

    # Configure LoRA
    lora_config = LoraConfig(
        r=lora_r,
        lora_alpha=lora_alpha,
        lora_dropout=lora_dropout,
        target_modules=target_modules,
        bias="none",
        task_type="CAUSAL_LM",
    )

    # Get PEFT model
    model = get_peft_model(model, lora_config)

    # Print trainable parameters
    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total_params = sum(p.numel() for p in model.parameters())
    trainable_percent = 100 * trainable_params / total_params

    print()
    print(f"Trainable parameters: {trainable_params:,}")
    print(f"Total parameters: {total_params:,}")
    print(f"Trainable: {trainable_percent:.2f}%")
    print(f"Model memory footprint: {model.get_memory_footprint() / 1e9:.2f} GB")
    print()

    return model


def train(
    model_name="meta-llama/Meta-Llama-3.1-8B-Instruct",
    training_set_jsonl=None,
    eval_dataset_path=None,
    output_dir=None,
    num_epochs=3,
    batch_size=4,
    gradient_accumulation_steps=4,
    learning_rate=2e-4,
    lora_r=16,
    lora_alpha=32,
    lora_dropout=0.05,
    lora_target_modules=None,
    max_length=512,
    warmup_steps=100,
    save_steps=500,
    logging_steps=50,
    eval_steps=None,
    max_train_samples=None,
    max_eval_samples=None,
    use_tracking=True,
    run_name=None,
    extra_callbacks=None,   # TB-US-065: inject the DB-writing callback
):
    """TB-US-078: QLoRA training on a registered training_set_version.

    Args:
        training_set_jsonl: Required. Path to a training_set_version's
            sidecar JSONL (`training/datasets/training_set_versions/v{N}.jsonl`).
            Each row's 'text' field is used verbatim.
        eval_dataset_path: Optional. HF Datasets dir providing a 'test'
            split for eval-loss (early stopping, load_best_model_at_end).
            Defaults to the GSM8K local dir. Set to None to disable eval.
        output_dir: Where to save adapter artifacts.
        eval_steps: When None, falls back to per-epoch evaluation if
            eval_dataset_path is set, or skips eval entirely if not.
        max_train_samples / max_eval_samples: cap sample counts (None = all).
    """
    # Required: training-set JSONL path
    if training_set_jsonl is None:
        print("Error: training_set_jsonl is required (TB-US-078). "
              "Pass --training-set-jsonl or launch via TB with a "
              "training_set_version_id.")
        sys.exit(1)
    training_set_jsonl = Path(training_set_jsonl)

    # Eval dataset defaults to the local GSM8K dir; None disables eval
    if eval_dataset_path is None:
        eval_dataset_path = Path(__file__).parent.parent.parent / "datasets" / "math" / "data"
    elif eval_dataset_path == "none":
        eval_dataset_path = None
    else:
        eval_dataset_path = Path(eval_dataset_path)
    if output_dir is None:
        output_dir = Path(__file__).parent.parent.parent / "models" / "fine-tuned" / "gsm8k_qlora"

    output_dir = Path(output_dir)
    logs_dir = Path(__file__).parent.parent.parent / "experiments" / "logs"

    print("=" * 80)
    print("GSM8K QLoRA Fine-Tuning")
    print("=" * 80)
    print()
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Model: {model_name}")
    print(f"Output: {output_dir}")
    print()

    # Check GPU
    if not torch.cuda.is_available():
        print("\n⚠️  WARNING: No GPU detected! Training will be very slow.")
        response = input("Continue anyway? (yes/no): ")
        if response.lower() != 'yes':
            print("Training cancelled.")
            return False
    else:
        print(f"✓ GPU detected: {torch.cuda.get_device_name(0)}")
        print(f"  VRAM available: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB\n")

    # Create output directories
    output_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)

    # Load tokenizer
    print("Loading tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"

    # Prepare dataset — TB-US-078: JSONL training + GSM8K eval
    train_dataset, eval_dataset = prepare_dataset(
        tokenizer=tokenizer,
        training_set_jsonl=training_set_jsonl,
        eval_dataset_hf_dir=eval_dataset_path,
        max_length=max_length,
        max_train_samples=max_train_samples,
        max_eval_samples=max_eval_samples,
    )

    # Create model
    model = create_qlora_model(
        model_name, lora_r, lora_alpha, lora_dropout,
        target_modules=lora_target_modules,
    )

    # Resolve eval cadence. --eval-steps is honored when the caller sets
    # it. Otherwise, if the dataset provides an eval split, fall back to
    # per-epoch evaluation so a smoke run (e.g. --epochs 1) still emits
    # at least one eval metric without needing an extra flag.
    if eval_dataset is None:
        eval_strategy = "no"
        eval_steps = None
    elif eval_steps:
        eval_strategy = "steps"
    else:
        eval_strategy = "epoch"
        eval_steps = None

    # Training arguments
    training_args = TrainingArguments(
        output_dir=str(output_dir),
        num_train_epochs=num_epochs,
        per_device_train_batch_size=batch_size,
        gradient_accumulation_steps=gradient_accumulation_steps,
        learning_rate=learning_rate,
        warmup_steps=warmup_steps,
        logging_steps=logging_steps,
        save_steps=save_steps,
        eval_strategy=eval_strategy,
        eval_steps=eval_steps,
        # TB-US-077: when eval runs, make save_strategy match eval_strategy.
        # Required by HF Trainer when load_best_model_at_end=True — the
        # eval + save intervals must align so there's a saved checkpoint
        # at each eval step to pick from. For eval_strategy="no" we
        # retain the default steps-based save (checkpointing is
        # independent of best-model selection in that case).
        save_strategy=eval_strategy if eval_strategy != "no" else "steps",
        save_total_limit=3,
        fp16=True,
        optim="paged_adamw_8bit",
        report_to="none",   # TB-US-066 fix: tensorboard not installed; our own TB-US-065 DB callback writes progress to training_runs* tables.
        gradient_checkpointing=True,
        max_grad_norm=0.3,
        weight_decay=0.001,
        lr_scheduler_type="cosine",
        # TB-US-077: load the best-eval-loss checkpoint at the end
        # (previously only when eval_strategy=="steps"). Combined with
        # EarlyStoppingCallback below, this means the saved adapter
        # is from the step with minimum eval_loss, not the final step.
        # Prevents Trial #3-style overfitting from shipping the last
        # (worst) checkpoint.
        load_best_model_at_end=(eval_strategy != "no"),
        metric_for_best_model="eval_loss",
        greater_is_better=False,
    )

    # Data collator
    data_collator = DataCollatorForLanguageModeling(
        tokenizer=tokenizer,
        mlm=False,
    )

    # Set up training tracker callback
    callbacks = []
    if use_tracking and TRACKER_AVAILABLE:
        if run_name is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            run_name = f"gsm8k_qlora_{timestamp}"

        tracker_callback = TrainingTrackerCallback(run_name=run_name)
        callbacks.append(tracker_callback)

    # TB-US-065: append the DB-writing callback injected by main() when
    # --run-id was passed.
    if extra_callbacks:
        callbacks.extend(extra_callbacks)

    # TB-US-077: Early stopping. Watches eval_loss; stops training if it
    # doesn't improve for `early_stopping_patience` evaluations.
    # Combined with load_best_model_at_end=True + metric_for_best_model=
    # "eval_loss", this means we SAVE the min-eval-loss checkpoint even
    # if training continues a bit past it.
    # Only applied when eval runs (eval_strategy != "no").
    if eval_strategy != "no":
        callbacks.append(EarlyStoppingCallback(early_stopping_patience=2))

    # Create trainer
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        data_collator=data_collator,
        callbacks=callbacks if callbacks else None,
    )

    # Start training
    print("=" * 80)
    print("Starting Training")
    print("=" * 80)
    print()
    print(f"Training samples: {len(train_dataset)}")
    if eval_dataset:
        print(f"Eval samples: {len(eval_dataset)}")
    print(f"Epochs: {num_epochs}")
    print(f"Batch size: {batch_size}")
    print(f"Gradient accumulation: {gradient_accumulation_steps}")
    print(f"Effective batch size: {batch_size * gradient_accumulation_steps}")
    print(f"Learning rate: {learning_rate}")
    if eval_strategy == "steps":
        print(f"Evaluation every: {eval_steps} steps")
    elif eval_strategy == "epoch":
        print("Evaluation: at end of each epoch")
    print(f"Output directory: {output_dir}")
    print()

    # Train
    start_time = datetime.now()
    trainer.train()
    end_time = datetime.now()
    duration = end_time - start_time

    print()
    print("=" * 80)
    print("Training Complete!")
    print("=" * 80)
    print()
    print(f"Duration: {duration}")
    print(f"Output directory: {output_dir}")
    print()

    # Save final model
    print("Saving final model...")
    trainer.save_model(str(output_dir / "final"))
    tokenizer.save_pretrained(str(output_dir / "final"))

    # Save training info
    training_info = {
        "base_model": model_name,
        "dataset": "GSM8K",
        "training_examples": len(train_dataset),
        "eval_examples": len(eval_dataset) if eval_dataset else 0,
        "epochs": num_epochs,
        "batch_size": batch_size,
        "learning_rate": learning_rate,
        "lora_r": lora_r,
        "lora_alpha": lora_alpha,
        "lora_dropout": lora_dropout,
        "target_modules": lora_target_modules or ["q_proj", "v_proj", "k_proj", "o_proj"],
        "duration_seconds": duration.total_seconds(),
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
    }

    info_file = output_dir / "training_info.json"
    with open(info_file, 'w') as f:
        json.dump(training_info, f, indent=2)

    print(f"Training info saved to: {info_file}")
    print()
    print("Next steps:")
    print("  1. Test adapter: python scripts/test_adapter.py --adapter-path", str(output_dir / "final"))
    print("  2. Run evaluation: python training/math/evaluate.py")
    print("  3. Compare results with baseline")
    print()

    return True


def main():
    """Main function with argument parsing."""
    import argparse

    # Set default paths relative to script location
    default_eval_dataset = Path(__file__).parent.parent.parent / "datasets" / "math" / "data"
    default_output = Path(__file__).parent.parent.parent / "models" / "fine-tuned" / "gsm8k_qlora"

    parser = argparse.ArgumentParser(description="Train QLoRA adapter for GSM8K")

    # Model configuration
    parser.add_argument("--model", default="meta-llama/Meta-Llama-3.1-8B-Instruct",
                        help="Base model name (default: Meta-Llama-3.1-8B-Instruct)")
    parser.add_argument("--training-set-jsonl", type=str, default=None,
                        help="TB-US-078: path to a training_set_version sidecar "
                             "JSONL. Required unless --run-id supplies it via the "
                             "TB launch config (as _training_set_jsonl).")
    parser.add_argument("--eval-dataset-path", type=str, default=str(default_eval_dataset),
                        help="HF Datasets dir with a 'test' split for eval-loss. "
                             "Pass 'none' to disable eval entirely.")
    parser.add_argument("--output-dir", type=str, default=str(default_output),
                        help="Output directory for model and checkpoints")

    # Training hyperparameters
    parser.add_argument("--epochs", type=int, default=3, help="Number of epochs (default: 3)")
    parser.add_argument("--batch-size", type=int, default=4, help="Batch size (default: 4)")
    parser.add_argument("--gradient-accum", type=int, default=4,
                        help="Gradient accumulation steps (default: 4)")
    parser.add_argument("--lr", type=float, default=2e-4, help="Learning rate (default: 2e-4)")
    parser.add_argument("--max-length", type=int, default=512,
                        help="Max sequence length (default: 512)")
    parser.add_argument("--warmup-steps", type=int, default=100, help="Warmup steps (default: 100)")

    # LoRA hyperparameters
    parser.add_argument("--lora-r", type=int, default=16, help="LoRA rank (default: 16)")
    parser.add_argument("--lora-alpha", type=int, default=32, help="LoRA alpha (default: 32)")
    parser.add_argument("--lora-dropout", type=float, default=0.05,
                        help="LoRA dropout (default: 0.05)")
    parser.add_argument("--lora-target-modules", nargs='+',
                        default=["q_proj", "v_proj", "k_proj", "o_proj"],
                        help="LoRA target module names, space-separated "
                             "(default: q_proj v_proj k_proj o_proj)")

    # Logging and saving
    parser.add_argument("--save-steps", type=int, default=500,
                        help="Save checkpoint every N steps (default: 500)")
    parser.add_argument("--logging-steps", type=int, default=50,
                        help="Log every N steps (default: 50)")
    parser.add_argument("--eval-steps", type=int, default=None,
                        help="Evaluate every N steps (default: None = no evaluation)")

    # Dataset options
    parser.add_argument("--max-train-samples", type=int, default=None,
                        help="Maximum number of training samples to use")
    parser.add_argument("--max-eval-samples", type=int, default=None,
                        help="Maximum number of evaluation samples to use")

    # Training tracking
    parser.add_argument("--no-tracking", action="store_true",
                        help="Disable training tracking")
    parser.add_argument("--run-name", type=str, default=None,
                        help="Name for this training run (for tracking)")

    # TB-US-065: if --run-id is provided, this run was launched by TB's
    # `POST /training/runs/launch`. Load config from the DB row + write
    # progress to the tracker DB during the run + auto-register the
    # trained adapter on completion.
    parser.add_argument("--run-id", type=int, default=None,
                        help="Internal: TB launch flow passes this to tie the "
                             "subprocess back to a training_runs row (TB-US-065)")

    args = parser.parse_args()

    # TB-US-065: if --run-id is set, override CLI args with the DB row's
    # launch-time hyperparameters.
    tb_db_callback = None
    tb_run_config = None
    if args.run_id is not None:
        try:
            from tb_db_callback import (
                TBDBTrainerCallback, mark_run_completed, mark_run_failed,
                load_run_config,
            )
        except ImportError:
            # tb_db_callback.py lives next to train.py; make sure cwd / path works
            import sys as _sys
            _sys.path.insert(0, str(Path(__file__).parent))
            from tb_db_callback import (
                TBDBTrainerCallback, mark_run_completed, mark_run_failed,
                load_run_config,
            )
        tb_run_config = load_run_config(args.run_id)
        # Override CLI args with DB-provided hyperparameters
        hp = tb_run_config
        if "epochs" in hp:
            args.epochs = int(hp["epochs"])
        if "batch_size" in hp:
            args.batch_size = int(hp["batch_size"])
        if "gradient_accumulation_steps" in hp:
            args.gradient_accum = int(hp["gradient_accumulation_steps"])
        if "learning_rate" in hp:
            args.lr = float(hp["learning_rate"])
        if "lora_rank" in hp:
            args.lora_r = int(hp["lora_rank"])
        if "lora_alpha" in hp:
            args.lora_alpha = int(hp["lora_alpha"])
        if "lora_dropout" in hp:
            args.lora_dropout = float(hp["lora_dropout"])
        # TB-US-082: forward target-modules from launch config so trials
        # can vary which parameters LoRA touches (e.g., attention-only vs.
        # attention+MLP). Accept list or space-separated string.
        if "lora_target_modules" in hp:
            tm = hp["lora_target_modules"]
            if isinstance(tm, str):
                tm = tm.split()
            args.lora_target_modules = list(tm)
        # TB-US-066 bugfix 2026-10-24: dataset-sampling + logging/save/warmup
        # cadence were missing from the override block, so short-test runs
        # defaulted to the full GSM8K training set. Added here.
        if "max_train_samples" in hp:
            args.max_train_samples = int(hp["max_train_samples"])
        if "max_eval_samples" in hp:
            args.max_eval_samples = int(hp["max_eval_samples"])
        if "max_length" in hp:
            args.max_length = int(hp["max_length"])
        if "warmup_steps" in hp:
            args.warmup_steps = int(hp["warmup_steps"])
        if "logging_steps" in hp:
            args.logging_steps = int(hp["logging_steps"])
        if "save_steps" in hp:
            args.save_steps = int(hp["save_steps"])
        if "eval_steps" in hp:
            args.eval_steps = int(hp["eval_steps"]) if hp["eval_steps"] else None
        if hp.get("_base_model"):
            args.model = hp["_base_model"]
        if hp.get("_adapter_output_path"):
            args.output_dir = hp["_adapter_output_path"]
        if hp.get("_run_name"):
            args.run_name = hp["_run_name"]
        # TB-US-078: training-set-version sidecar JSONL path, resolved
        # by the launch endpoint from training_set_version_id
        if hp.get("_training_set_jsonl"):
            args.training_set_jsonl = hp["_training_set_jsonl"]
        if hp.get("_eval_dataset_path"):
            args.eval_dataset_path = hp["_eval_dataset_path"]
        tb_db_callback = TBDBTrainerCallback(run_id=args.run_id)
        print(f"[TB-US-065] Launched by TB; run_id={args.run_id}, "
              f"run_name={args.run_name}, output={args.output_dir}")

    # Run training
    try:
        _start_time = datetime.now()
        extra_callbacks = [tb_db_callback] if tb_db_callback else None
        success = train(
            model_name=args.model,
            training_set_jsonl=args.training_set_jsonl,
            eval_dataset_path=args.eval_dataset_path,
            output_dir=args.output_dir,
            num_epochs=args.epochs,
            batch_size=args.batch_size,
            gradient_accumulation_steps=args.gradient_accum,
            learning_rate=args.lr,
            lora_r=args.lora_r,
            lora_alpha=args.lora_alpha,
            lora_dropout=args.lora_dropout,
            lora_target_modules=args.lora_target_modules,
            max_length=args.max_length,
            warmup_steps=args.warmup_steps,
            save_steps=args.save_steps,
            logging_steps=args.logging_steps,
            eval_steps=args.eval_steps,
            max_train_samples=args.max_train_samples,
            max_eval_samples=args.max_eval_samples,
            use_tracking=not args.no_tracking,
            run_name=args.run_name,
            extra_callbacks=extra_callbacks,
        )
        # TB-US-065 R7: mark run completed + auto-register adapter
        if args.run_id is not None and success:
            duration = int((datetime.now() - _start_time).total_seconds())
            mark_run_completed(
                run_id=args.run_id,
                duration_seconds=duration,
                adapter_output_path=args.output_dir,
            )
            # Auto-register adapter via AdapterVersionManager (TB-US-063).
            try:
                import sys as _sys
                _sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))
                from api.adapter_version_manager import AdapterVersionManager
                from api.agent_manager import AgentManager
                agent_id = tb_run_config.get("_agent_id") if tb_run_config else None
                ts_version_id = tb_run_config.get("_training_set_version_id") if tb_run_config else None
                if agent_id is not None:
                    agent_row = AgentManager().get_by_id(agent_id)
                    agent_slug = agent_row["name"] if agent_row else f"agent-{agent_id}"
                    # TB-US-065 bugfix 2026-10-25: HF Trainer saves the final
                    # adapter to <output_dir>/final/, not <output_dir>/.
                    # Fall back to output_dir if final/ doesn't exist (older
                    # train scripts / custom checkpointing).
                    final_dir = Path(args.output_dir) / "final"
                    source_dir = final_dir if final_dir.exists() else Path(args.output_dir)
                    adapter_row = AdapterVersionManager().register_existing_adapter(
                        agent_id=agent_id,
                        agent_slug=agent_slug,
                        source_dir=source_dir,
                        base_model=args.model,
                        created_by="training-run",
                        training_set_version_id=ts_version_id,
                        training_run_metadata={
                            "run_id": args.run_id,
                            "run_name": args.run_name,
                            "duration_seconds": duration,
                            "epochs": args.epochs,
                            "lora_rank": args.lora_r,
                            "lora_alpha": args.lora_alpha,
                            "learning_rate": args.lr,
                            "batch_size": args.batch_size,
                        },
                    )
                    print(f"[TB-US-065] Auto-registered adapter_version_id={adapter_row['version_id']}")
                else:
                    print("[TB-US-065] Skipping auto-register: no agent_id in run config")
            except Exception as e:
                import traceback as _tb
                print(f"[TB-US-065] Auto-register failed (non-fatal; adapter files still on disk): {e}")
                _tb.print_exc()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTraining interrupted by user.")
        # TB-US-065 R7: mark failed on cancel so DB reflects reality
        if args.run_id is not None:
            try:
                mark_run_failed(run_id=args.run_id, error_message="KeyboardInterrupt (SIGINT/SIGTERM)")
            except Exception:
                pass
        sys.exit(130)
    except Exception as e:
        print(f"\n\nError during training: {e}")
        import traceback
        traceback.print_exc()
        # TB-US-065 R7: capture traceback into training_runs.notes
        if args.run_id is not None:
            try:
                mark_run_failed(
                    run_id=args.run_id,
                    error_message=f"{type(e).__name__}: {e}\n{traceback.format_exc()}",
                )
            except Exception:
                pass
        sys.exit(1)


if __name__ == "__main__":
    main()
