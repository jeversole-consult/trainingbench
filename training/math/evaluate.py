#!/usr/bin/env python3
"""
Evaluation script for fine-tuned GSM8K model.

This script evaluates the fine-tuned QLoRA model on GSM8K test set to establish
"after" metrics for comparison with baseline performance.
"""

import os
import sys
import json
import re
from pathlib import Path
from datetime import datetime

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel
from datasets import load_from_disk
from tqdm import tqdm


# Configuration
BASE_MODEL = "meta-llama/Meta-Llama-3.1-8B-Instruct"
PEFT_MODEL_PATH = Path(__file__).parent.parent.parent / "models" / "fine-tuned" / "gsm8k_qlora" / "final"
DATASET_PATH = Path(__file__).parent.parent.parent / "datasets" / "math" / "data"
RESULTS_DIR = Path(__file__).parent.parent.parent / "experiments" / "before_after"
MAX_SAMPLES = 100  # Evaluate on first 100 samples to match baseline
MAX_NEW_TOKENS = 512
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"


def extract_answer(text: str) -> str:
    """
    Extract numerical answer from model output or GSM8K answer format.

    GSM8K answers end with #### followed by the numerical answer.
    """
    # Try to find #### pattern (GSM8K format)
    match = re.search(r'####\s*(-?\d+(?:,\d{3})*(?:\.\d+)?)', text)
    if match:
        return match.group(1).replace(',', '')

    # Try to find Final Answer: pattern
    match = re.search(r'Final Answer:\s*(-?\d+(?:,\d{3})*(?:\.\d+)?)', text, re.IGNORECASE)
    if match:
        return match.group(1).replace(',', '')

    # Try to find last number in the text
    numbers = re.findall(r'-?\d+(?:,\d{3})*(?:\.\d+)?', text)
    if numbers:
        return numbers[-1].replace(',', '')

    return ""


def format_prompt(question: str) -> str:
    """Format question as instruction prompt for Llama model."""
    return f"""<|begin_of_text|><|start_header_id|>system<|end_header_id|>

You are a helpful math tutor. Solve the following math problem step by step. Show your work and provide the final numerical answer clearly.
<|eot_id|><|start_header_id|>user<|end_header_id|>

{question}
<|eot_id|><|start_header_id|>assistant<|end_header_id|>

"""


def evaluate_finetuned():
    """Run evaluation on fine-tuned model."""
    print("=" * 80)
    print("GSM8K Fine-Tuned Model Evaluation")
    print("=" * 80)
    print()
    print(f"Base model: {BASE_MODEL}")
    print(f"PEFT adapter: {PEFT_MODEL_PATH}")
    print(f"Device: {DEVICE}")
    print(f"Max samples: {MAX_SAMPLES}")
    print()

    # Check if model exists
    if not PEFT_MODEL_PATH.exists():
        print(f"Error: Fine-tuned model not found at {PEFT_MODEL_PATH}")
        print("Please run training first: python training/math/train.py")
        return False

    # Create results directory
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    # Load dataset
    print("Loading dataset...")
    if not DATASET_PATH.exists():
        print(f"Error: Dataset not found at {DATASET_PATH}")
        print("Please run: python scripts/download_gsm8k.py")
        return False

    dataset = load_from_disk(str(DATASET_PATH))
    test_data = dataset['test']

    # Limit samples to match baseline
    if MAX_SAMPLES:
        test_data = test_data.select(range(min(MAX_SAMPLES, len(test_data))))

    print(f"Evaluating on {len(test_data)} examples")
    print()

    # Load tokenizer
    print("Loading tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)

    # Load base model in 4-bit
    print("Loading base model...")
    model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL,
        torch_dtype=torch.float16,
        device_map="auto",
        load_in_4bit=True,
    )

    # Load PEFT adapter
    print("Loading PEFT adapter...")
    model = PeftModel.from_pretrained(model, str(PEFT_MODEL_PATH))

    print("Model loaded successfully!")
    print(f"Model memory footprint: {model.get_memory_footprint() / 1e9:.2f} GB")
    print()

    # Evaluation loop
    results = []
    correct = 0
    total = 0

    print("Running evaluation...")
    print("-" * 80)

    for idx, example in enumerate(tqdm(test_data, desc="Evaluating")):
        question = example['question']
        ground_truth_answer = extract_answer(example['answer'])

        # Format prompt
        prompt = format_prompt(question)

        # Generate response
        inputs = tokenizer(prompt, return_tensors="pt").to(DEVICE)

        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=MAX_NEW_TOKENS,
                temperature=0.7,
                do_sample=True,
                top_p=0.9,
                pad_token_id=tokenizer.eos_token_id,
            )

        # Decode response
        response = tokenizer.decode(outputs[0], skip_special_tokens=True)

        # Extract only the assistant's response (after the prompt)
        assistant_response = response.split("<|start_header_id|>assistant<|end_header_id|>")[-1].strip()

        # Extract predicted answer
        predicted_answer = extract_answer(assistant_response)

        # Check if correct
        is_correct = (predicted_answer == ground_truth_answer)
        if is_correct:
            correct += 1
        total += 1

        # Store result
        result = {
            "index": idx,
            "question": question,
            "ground_truth": ground_truth_answer,
            "predicted": predicted_answer,
            "full_response": assistant_response,
            "correct": is_correct,
        }
        results.append(result)

        # Print sample results
        if idx < 3 or (idx + 1) % 20 == 0:
            print()
            print(f"Example {idx + 1}:")
            print(f"  Question: {question[:100]}...")
            print(f"  Ground Truth: {ground_truth_answer}")
            print(f"  Predicted: {predicted_answer}")
            print(f"  Correct: {is_correct}")
            print(f"  Accuracy so far: {correct}/{total} = {100*correct/total:.1f}%")

    # Calculate final metrics
    accuracy = correct / total if total > 0 else 0

    print()
    print("=" * 80)
    print("Fine-Tuned Model Evaluation Complete")
    print("=" * 80)
    print()
    print(f"Total examples: {total}")
    print(f"Correct: {correct}")
    print(f"Incorrect: {total - correct}")
    print(f"Accuracy: {100*accuracy:.2f}%")
    print()

    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = RESULTS_DIR / f"finetuned_gsm8k_{timestamp}.json"

    summary = {
        "model": BASE_MODEL,
        "peft_adapter": str(PEFT_MODEL_PATH),
        "dataset": "GSM8K",
        "split": "test",
        "timestamp": timestamp,
        "total_examples": total,
        "correct": correct,
        "accuracy": accuracy,
        "max_samples": MAX_SAMPLES,
        "results": results,
    }

    with open(results_file, 'w') as f:
        json.dump(summary, f, indent=2)

    print(f"Results saved to: {results_file}")
    print()

    # Show some errors for analysis
    print("Sample errors for analysis:")
    print("-" * 80)
    errors = [r for r in results if not r['correct']][:3]
    for i, err in enumerate(errors, 1):
        print(f"\nError {i}:")
        print(f"  Question: {err['question'][:150]}...")
        print(f"  Expected: {err['ground_truth']}")
        print(f"  Got: {err['predicted']}")
        print(f"  Response: {err['full_response'][:200]}...")

    print()
    print("Next steps:")
    print("  Run comparison: python training/math/compare.py")
    print()

    return True


if __name__ == "__main__":
    success = evaluate_finetuned()
    sys.exit(0 if success else 1)
