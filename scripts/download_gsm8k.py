#!/usr/bin/env python3
"""
Download GSM8K dataset from Hugging Face Hub.

This script downloads the GSM8K (Grade School Math 8K) dataset and saves it
to the datasets/math directory for training and evaluation.
"""

import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from datasets import load_dataset


def download_gsm8k():
    """Download GSM8K dataset from Hugging Face Hub."""
    print("=" * 80)
    print("GSM8K Dataset Download")
    print("=" * 80)
    print()

    # Define save path
    save_dir = Path(__file__).parent.parent / "datasets" / "math" / "data"
    save_dir.mkdir(parents=True, exist_ok=True)

    print(f"Downloading GSM8K dataset from Hugging Face Hub...")
    print(f"Save directory: {save_dir}")
    print()

    try:
        # Load dataset from Hugging Face
        dataset = load_dataset("openai/gsm8k", "main")

        # Print dataset info
        print("Dataset loaded successfully!")
        print()
        print("Dataset splits:")
        for split_name, split_data in dataset.items():
            print(f"  {split_name}: {len(split_data)} examples")
        print()

        # Show sample
        print("Sample from training set:")
        print("-" * 80)
        sample = dataset['train'][0]
        print(f"Question: {sample['question']}")
        print()
        print(f"Answer: {sample['answer']}")
        print("-" * 80)
        print()

        # Save to disk
        print(f"Saving dataset to {save_dir}...")
        dataset.save_to_disk(str(save_dir))
        print("Dataset saved successfully!")
        print()

        # Verify saved dataset
        print("Verifying saved dataset...")
        from datasets import load_from_disk
        loaded_dataset = load_from_disk(str(save_dir))
        print(f"  Training examples: {len(loaded_dataset['train'])}")
        print(f"  Test examples: {len(loaded_dataset['test'])}")
        print()

        print("=" * 80)
        print("Download Complete!")
        print("=" * 80)
        print()
        print("Next steps:")
        print("  1. Run baseline evaluation: python training/math/baseline.py")
        print("  2. Preprocess data: python training/math/preprocess.py")
        print("  3. Run training: python training/math/train.py")
        print()

        return True

    except Exception as e:
        print(f"Error downloading dataset: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = download_gsm8k()
    sys.exit(0 if success else 1)
