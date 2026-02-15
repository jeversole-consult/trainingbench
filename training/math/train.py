#!/usr/bin/env python3
"""
QLoRA fine-tuning for GSM8K using Llama 3.1 8B.

This script fine-tunes the base Llama model on GSM8K using QLoRA (Quantized Low-Rank Adaptation)
for parameter-efficient training on consumer hardware.
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


# Configuration
BASE_MODEL = "meta-llama/Meta-Llama-3.1-8B-Instruct"
DATASET_PATH = Path(__file__).parent.parent.parent / "datasets" / "math" / "data"
OUTPUT_DIR = Path(__file__).parent.parent.parent / "models" / "fine-tuned" / "gsm8k_qlora"
LOGS_DIR = Path(__file__).parent.parent.parent / "experiments" / "logs"

# QLoRA hyperparameters (from README)
LORA_R = 16
LORA_ALPHA = 32
LORA_DROPOUT = 0.05
TARGET_MODULES = ["q_proj", "v_proj", "k_proj", "o_proj"]

# Training hyperparameters
BATCH_SIZE = 4
GRADIENT_ACCUMULATION_STEPS = 4
LEARNING_RATE = 2e-4
NUM_EPOCHS = 3
MAX_LENGTH = 512
WARMUP_STEPS = 100
SAVE_STEPS = 500
LOGGING_STEPS = 50

# Use full training set (7,473 examples) or subset for testing
USE_FULL_DATASET = True  # Set to False for quick testing with 1000 examples


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


def prepare_dataset(tokenizer):
    """Load and prepare GSM8K dataset for training."""
    print("Loading dataset...")

    if not DATASET_PATH.exists():
        print(f"Error: Dataset not found at {DATASET_PATH}")
        print("Please run: python scripts/download_gsm8k.py")
        sys.exit(1)

    dataset = load_from_disk(str(DATASET_PATH))

    # Use training split
    train_data = dataset['train']

    if not USE_FULL_DATASET:
        print("Using subset of 1000 examples for testing...")
        train_data = train_data.select(range(1000))

    print(f"Training examples: {len(train_data)}")

    # Format examples
    print("Formatting examples...")
    train_data = train_data.map(
        format_training_example,
        remove_columns=train_data.column_names,
        desc="Formatting training examples",
    )

    # Tokenize
    print("Tokenizing examples...")

    def tokenize_function(examples):
        return tokenizer(
            examples["text"],
            truncation=True,
            max_length=MAX_LENGTH,
            padding=False,
        )

    train_data = train_data.map(
        tokenize_function,
        batched=True,
        remove_columns=["text"],
        desc="Tokenizing",
    )

    return train_data


def create_qlora_model(model_name):
    """Create QLoRA-configured model."""
    print("=" * 80)
    print("Setting up QLoRA Configuration")
    print("=" * 80)
    print()
    print(f"Base model: {model_name}")
    print(f"LoRA rank (r): {LORA_R}")
    print(f"LoRA alpha: {LORA_ALPHA}")
    print(f"LoRA dropout: {LORA_DROPOUT}")
    print(f"Target modules: {TARGET_MODULES}")
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
        r=LORA_R,
        lora_alpha=LORA_ALPHA,
        lora_dropout=LORA_DROPOUT,
        target_modules=TARGET_MODULES,
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


def train():
    """Run QLoRA training on GSM8K."""
    print("=" * 80)
    print("GSM8K QLoRA Fine-Tuning")
    print("=" * 80)
    print()
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Create output directories
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    # Load tokenizer
    print("Loading tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)
    tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"

    # Prepare dataset
    train_dataset = prepare_dataset(tokenizer)

    # Create model
    model = create_qlora_model(BASE_MODEL)

    # Training arguments
    training_args = TrainingArguments(
        output_dir=str(OUTPUT_DIR),
        num_train_epochs=NUM_EPOCHS,
        per_device_train_batch_size=BATCH_SIZE,
        gradient_accumulation_steps=GRADIENT_ACCUMULATION_STEPS,
        learning_rate=LEARNING_RATE,
        warmup_steps=WARMUP_STEPS,
        logging_steps=LOGGING_STEPS,
        save_steps=SAVE_STEPS,
        save_total_limit=3,
        fp16=True,
        optim="paged_adamw_8bit",
        logging_dir=str(LOGS_DIR / "gsm8k"),
        report_to=["tensorboard"],
        gradient_checkpointing=True,
        max_grad_norm=0.3,
        weight_decay=0.001,
        lr_scheduler_type="cosine",
    )

    # Data collator
    data_collator = DataCollatorForLanguageModeling(
        tokenizer=tokenizer,
        mlm=False,
    )

    # Create trainer
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        data_collator=data_collator,
    )

    # Start training
    print("=" * 80)
    print("Starting Training")
    print("=" * 80)
    print()
    print(f"Training samples: {len(train_dataset)}")
    print(f"Epochs: {NUM_EPOCHS}")
    print(f"Batch size: {BATCH_SIZE}")
    print(f"Gradient accumulation: {GRADIENT_ACCUMULATION_STEPS}")
    print(f"Effective batch size: {BATCH_SIZE * GRADIENT_ACCUMULATION_STEPS}")
    print(f"Learning rate: {LEARNING_RATE}")
    print(f"Output directory: {OUTPUT_DIR}")
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
    print(f"Output directory: {OUTPUT_DIR}")
    print()

    # Save final model
    print("Saving final model...")
    trainer.save_model(str(OUTPUT_DIR / "final"))
    tokenizer.save_pretrained(str(OUTPUT_DIR / "final"))

    # Save training info
    training_info = {
        "base_model": BASE_MODEL,
        "dataset": "GSM8K",
        "training_examples": len(train_dataset),
        "epochs": NUM_EPOCHS,
        "batch_size": BATCH_SIZE,
        "learning_rate": LEARNING_RATE,
        "lora_r": LORA_R,
        "lora_alpha": LORA_ALPHA,
        "lora_dropout": LORA_DROPOUT,
        "target_modules": TARGET_MODULES,
        "duration_seconds": duration.total_seconds(),
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
    }

    info_file = OUTPUT_DIR / "training_info.json"
    with open(info_file, 'w') as f:
        json.dump(training_info, f, indent=2)

    print(f"Training info saved to: {info_file}")
    print()
    print("Next steps:")
    print("  1. Run evaluation: python training/math/evaluate.py")
    print("  2. Compare results with baseline")
    print()

    return True


if __name__ == "__main__":
    try:
        success = train()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTraining interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nError during training: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
