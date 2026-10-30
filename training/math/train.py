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

import torch
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    TrainingArguments,
    Trainer,
    DataCollatorForLanguageModeling,
    BitsAndBytesConfig,
)
from peft import (
    LoraConfig,
    get_peft_model,
    prepare_model_for_kbit_training,
)
from datasets import load_from_disk
from tqdm import tqdm

# Add scripts directory to path for training tracker
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

# Try to import training tracker callback
try:
    from training_tracker_callback import TrainingTrackerCallback
    TRACKER_AVAILABLE = True
except ImportError:
    TRACKER_AVAILABLE = False
    print("⚠️  Training tracker not available, training will proceed without tracking")


def format_training_example(example):
    """
    Format GSM8K example as instruction-following training example.

    Returns a formatted prompt with the question and step-by-step solution.
    """
    question = example['question']
    answer = example['answer']

    # Extract step-by-step reasoning and final answer
    # GSM8K answers are in format: "step 1\nstep 2\n...#### final_answer"
    if "####" in answer:
        reasoning, final_answer = answer.split("####")
        reasoning = reasoning.strip()
        final_answer = final_answer.strip()
    else:
        reasoning = answer
        final_answer = ""

    # Format as Llama 3.1 chat format
    prompt = f"""<|begin_of_text|><|start_header_id|>system<|end_header_id|>

You are a helpful math tutor. Solve the following math problem step by step. Show your work and provide the final numerical answer clearly.
<|eot_id|><|start_header_id|>user<|end_header_id|>

{question}
<|eot_id|><|start_header_id|>assistant<|end_header_id|>

{reasoning}

Final Answer: {final_answer}<|eot_id|>"""

    return {"text": prompt}


def prepare_dataset(tokenizer, dataset_path, max_length=512, use_full_dataset=True, max_train_samples=None, max_eval_samples=None):
    """Load and prepare GSM8K dataset for training and evaluation."""
    print("Loading dataset...")

    if not dataset_path.exists():
        print(f"Error: Dataset not found at {dataset_path}")
        print("Please run: python scripts/download_gsm8k.py")
        sys.exit(1)

    dataset = load_from_disk(str(dataset_path))

    # Use training split
    train_data = dataset['train']

    # Use test split for evaluation if available
    eval_data = dataset.get('test', None)

    # Limit training samples
    if not use_full_dataset or max_train_samples:
        num_samples = max_train_samples if max_train_samples else 1000
        print(f"Using subset of {num_samples} training examples...")
        train_data = train_data.select(range(min(num_samples, len(train_data))))

    # Limit eval samples
    if eval_data and max_eval_samples:
        print(f"Using subset of {max_eval_samples} eval examples...")
        eval_data = eval_data.select(range(min(max_eval_samples, len(eval_data))))

    print(f"Training examples: {len(train_data)}")
    if eval_data:
        print(f"Evaluation examples: {len(eval_data)}")

    # Format examples
    print("Formatting examples...")
    train_data = train_data.map(
        format_training_example,
        remove_columns=train_data.column_names,
        desc="Formatting training examples",
    )

    if eval_data:
        eval_data = eval_data.map(
            format_training_example,
            remove_columns=eval_data.column_names,
            desc="Formatting eval examples",
        )

    # Tokenize
    print("Tokenizing examples...")

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
        remove_columns=["text"],
        desc="Tokenizing training data",
    )

    if eval_data:
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
    dataset_path=None,
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
    use_full_dataset=True,
    max_train_samples=None,
    max_eval_samples=None,
    use_tracking=True,
    run_name=None,
    extra_callbacks=None,   # TB-US-065: inject the DB-writing callback
):
    """
    Run QLoRA training on GSM8K.

    Args:
        model_name: Base model to fine-tune
        dataset_path: Path to dataset directory
        output_dir: Output directory for model and checkpoints
        num_epochs: Number of training epochs
        batch_size: Training batch size
        gradient_accumulation_steps: Gradient accumulation steps
        learning_rate: Learning rate
        lora_r: LoRA rank
        lora_alpha: LoRA alpha scaling factor
        lora_dropout: LoRA dropout rate
        max_length: Maximum sequence length
        warmup_steps: Warmup steps
        save_steps: Save checkpoint every N steps
        logging_steps: Log every N steps
        eval_steps: Evaluate every N steps. When None: falls back to
            per-epoch evaluation if the dataset provides an eval split,
            or skips evaluation entirely if it does not.
        use_full_dataset: Use full dataset or subset
        max_train_samples: Maximum training samples (None = all)
        max_eval_samples: Maximum eval samples (None = all)
        use_tracking: Enable training tracking
        run_name: Name for training run (for tracking)
    """
    # Set default paths if not provided
    if dataset_path is None:
        dataset_path = Path(__file__).parent.parent.parent / "datasets" / "math" / "data"
    if output_dir is None:
        output_dir = Path(__file__).parent.parent.parent / "models" / "fine-tuned" / "gsm8k_qlora"

    dataset_path = Path(dataset_path)
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

    # Prepare dataset
    train_dataset, eval_dataset = prepare_dataset(
        tokenizer, dataset_path, max_length,
        use_full_dataset, max_train_samples, max_eval_samples
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
        save_total_limit=3,
        fp16=True,
        optim="paged_adamw_8bit",
        report_to="none",   # TB-US-066 fix: tensorboard not installed; our own TB-US-065 DB callback writes progress to training_runs* tables.
        gradient_checkpointing=True,
        max_grad_norm=0.3,
        weight_decay=0.001,
        lr_scheduler_type="cosine",
        load_best_model_at_end=(eval_strategy == "steps"),
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
    default_dataset = Path(__file__).parent.parent.parent / "datasets" / "math" / "data"
    default_output = Path(__file__).parent.parent.parent / "models" / "fine-tuned" / "gsm8k_qlora"

    parser = argparse.ArgumentParser(description="Train QLoRA adapter for GSM8K")

    # Model configuration
    parser.add_argument("--model", default="meta-llama/Meta-Llama-3.1-8B-Instruct",
                        help="Base model name (default: Meta-Llama-3.1-8B-Instruct)")
    parser.add_argument("--dataset-path", type=str, default=str(default_dataset),
                        help="Path to dataset directory")
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
    parser.add_argument("--subset", action="store_true",
                        help="Use subset of 1000 examples for quick testing")
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
        tb_db_callback = TBDBTrainerCallback(run_id=args.run_id)
        print(f"[TB-US-065] Launched by TB; run_id={args.run_id}, "
              f"run_name={args.run_name}, output={args.output_dir}")

    # Run training
    try:
        _start_time = datetime.now()
        extra_callbacks = [tb_db_callback] if tb_db_callback else None
        success = train(
            model_name=args.model,
            dataset_path=args.dataset_path,
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
            use_full_dataset=not args.subset,
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
