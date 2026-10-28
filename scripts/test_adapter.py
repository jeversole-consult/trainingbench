#!/usr/bin/env python3
"""
Test a trained PEFT adapter with sample queries.

Adapted for TrainingBench - supports both math tutoring and general instruction-following formats.
"""

import os
import sys
import torch
from pathlib import Path
from typing import Optional, List, Dict


def test_adapter(
    adapter_path: str,
    test_queries: Optional[List[Dict]] = None,
    max_new_tokens: int = 512,
    temperature: float = 0.7,
    format_type: str = "math"
):
    """
    Test a trained PEFT adapter.

    Args:
        adapter_path: Path to the trained adapter
        test_queries: List of test queries (uses defaults if None)
        max_new_tokens: Maximum tokens to generate
        temperature: Sampling temperature
        format_type: Format type - "math" for GSM8K style, "instruction" for general format
    """
    print("=" * 80)
    print("Testing PEFT Adapter")
    print("=" * 80)
    print(f"\n📂 Adapter path: {adapter_path}")
    print(f"   Format: {format_type}")

    if not os.path.exists(adapter_path):
        print(f"\n❌ Error: Adapter not found at {adapter_path}")
        return

    # Check GPU
    if torch.cuda.is_available():
        print(f"✓ GPU: {torch.cuda.get_device_name(0)}")
    else:
        print("⚠️  No GPU detected - inference will be slow")

    # Import libraries
    print("\n📦 Loading libraries...")
    try:
        from peft import AutoPeftModelForCausalLM
        from transformers import AutoTokenizer
    except ImportError as e:
        print(f"❌ Error importing libraries: {e}")
        return

    # Load model and tokenizer
    print(f"\n🔄 Loading model from {adapter_path}...")
    print("   (This may take a minute...)")

    try:
        model = AutoPeftModelForCausalLM.from_pretrained(
            adapter_path,
            device_map="auto",
            torch_dtype=torch.float16
        )
        tokenizer = AutoTokenizer.from_pretrained(adapter_path)
        model.eval()
        print("✓ Model loaded successfully")
    except Exception as e:
        print(f"❌ Error loading model: {e}")
        return

    # Default test queries based on format type
    if test_queries is None:
        if format_type == "math":
            test_queries = [
                {
                    "question": "Janet's ducks lay 16 eggs per day. She eats three for breakfast every morning and bakes muffins for her friends every day with four. She sells the remainder at the farmers' market daily for $2 per fresh duck egg. How much in dollars does she make every day at the farmers' market?"
                },
                {
                    "question": "A robe takes 2 bolts of blue fiber and half that much white fiber. How many bolts in total does it take?"
                },
                {
                    "question": "Josh decides to try flipping a house. He buys a house for $80,000 and then puts in $50,000 in repairs. This increased the value of the house by 150%. How much profit did he make?"
                }
            ]
        else:
            # Instruction-following format
            test_queries = [
                {
                    "context": "PEFT (Parameter-Efficient Fine-Tuning) enables efficient adaptation of large language models by training only a small subset of parameters, typically 0.1-1% of the total. LoRA is a popular PEFT technique that adds trainable low-rank matrices to model layers.",
                    "question": "What is PEFT and how does it work?"
                }
            ]

    # Test the model
    print("\n" + "=" * 80)
    print("Running Test Queries")
    print("=" * 80)

    for i, query in enumerate(test_queries, 1):
        print(f"\n{'─' * 80}")
        print(f"Test Query {i}/{len(test_queries)}")
        print(f"{'─' * 80}")

        # Format input based on type
        if format_type == "math":
            question = query.get("question", "")
            input_text = f"""<|begin_of_text|><|start_header_id|>system<|end_header_id|>

You are a helpful math tutor. Solve the following math problem step by step. Show your work and provide the final numerical answer clearly.
<|eot_id|><|start_header_id|>user<|end_header_id|>

{question}
<|eot_id|><|start_header_id|>assistant<|end_header_id|>

"""
            print(f"\n📝 Question: {question}")
        else:
            # Instruction format
            context = query.get("context", "")
            question = query.get("question", "")
            input_text = f"""### Instruction:
Answer based on the provided context

### Input:
Context:
{context}

Question: {question}

### Response:
"""
            print(f"\n📝 Question: {question}")
            print(f"\n📄 Context: {context[:200]}...")

        # Generate
        print("\n🤖 Generating answer...")
        inputs = tokenizer(input_text, return_tensors="pt").to(model.device)

        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                temperature=temperature,
                do_sample=True,
                top_p=0.9,
                top_k=40,
                repetition_penalty=1.1
            )

        # Decode response
        full_response = tokenizer.decode(outputs[0], skip_special_tokens=True)

        # Extract just the response part
        if format_type == "math":
            # For math format, extract after assistant header
            if "<|start_header_id|>assistant<|end_header_id|>" in full_response:
                response = full_response.split("<|start_header_id|>assistant<|end_header_id|>")[-1].strip()
            else:
                response = full_response
        else:
            # For instruction format
            if "### Response:" in full_response:
                response = full_response.split("### Response:")[-1].strip()
            else:
                response = full_response

        print(f"\n💬 Response:\n{response}\n")

    print("=" * 80)
    print("✅ Testing complete!")
    print("=" * 80)


def interactive_mode(adapter_path: str, format_type: str = "math"):
    """
    Interactive testing mode.

    Args:
        adapter_path: Path to the adapter
        format_type: Format type - "math" or "instruction"
    """
    print("\n🎮 Interactive Mode")
    print(f"Format: {format_type}")
    print("Type 'quit' or 'exit' to stop\n")

    # Load model
    from peft import AutoPeftModelForCausalLM
    from transformers import AutoTokenizer

    print("Loading model...")
    model = AutoPeftModelForCausalLM.from_pretrained(
        adapter_path,
        device_map="auto",
        torch_dtype=torch.float16
    )
    tokenizer = AutoTokenizer.from_pretrained(adapter_path)
    model.eval()
    print("✓ Model ready\n")

    while True:
        if format_type == "math":
            # Math tutoring format
            print("Enter math question (or 'quit'):")
            question = input("> ").strip()
            if question.lower() in ['quit', 'exit']:
                break

            input_text = f"""<|begin_of_text|><|start_header_id|>system<|end_header_id|>

You are a helpful math tutor. Solve the following math problem step by step. Show your work and provide the final numerical answer clearly.
<|eot_id|><|start_header_id|>user<|end_header_id|>

{question}
<|eot_id|><|start_header_id|>assistant<|end_header_id|>

"""
        else:
            # Instruction format
            print("Enter context (or 'quit'):")
            context = input("> ").strip()
            if context.lower() in ['quit', 'exit']:
                break

            print("\nEnter question:")
            question = input("> ").strip()
            if question.lower() in ['quit', 'exit']:
                break

            input_text = f"""### Instruction:
Answer based on the provided context

### Input:
Context:
{context}

Question: {question}

### Response:
"""

        # Generate
        inputs = tokenizer(input_text, return_tensors="pt").to(model.device)

        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=512,
                temperature=0.7,
                do_sample=True
            )

        full_response = tokenizer.decode(outputs[0], skip_special_tokens=True)

        # Extract response
        if format_type == "math":
            if "<|start_header_id|>assistant<|end_header_id|>" in full_response:
                response = full_response.split("<|start_header_id|>assistant<|end_header_id|>")[-1].strip()
            else:
                response = full_response
        else:
            if "### Response:" in full_response:
                response = full_response.split("### Response:")[-1].strip()
            else:
                response = full_response

        print(f"\n💬 Response:\n{response}\n")
        print("─" * 80 + "\n")

    print("Goodbye!")


def main():
    """Main function with argument parsing."""
    import argparse

    parser = argparse.ArgumentParser(description="Test PEFT adapter")
    parser.add_argument("--adapter-path", required=True, help="Path to trained adapter")
    parser.add_argument("--interactive", action="store_true", help="Interactive testing mode")
    parser.add_argument("--max-tokens", type=int, default=512, help="Max tokens to generate")
    parser.add_argument("--temperature", type=float, default=0.7, help="Sampling temperature")
    parser.add_argument("--format", choices=["math", "instruction"], default="math",
                        help="Format type: 'math' for GSM8K style, 'instruction' for general")

    args = parser.parse_args()

    if args.interactive:
        interactive_mode(args.adapter_path, format_type=args.format)
    else:
        test_adapter(
            adapter_path=args.adapter_path,
            max_new_tokens=args.max_tokens,
            temperature=args.temperature,
            format_type=args.format
        )


if __name__ == "__main__":
    main()
