#!/usr/bin/env python3
"""
Compare baseline vs fine-tuned model performance on GSM8K.

This script generates a detailed comparison report showing the improvement
from PEFT fine-tuning for publication.
"""

import json
from pathlib import Path
from datetime import datetime
import sys


RESULTS_DIR = Path(__file__).parent.parent.parent / "experiments" / "before_after"
PUBLICATION_DIR = Path(__file__).parent.parent.parent / "publication"


def load_latest_results(prefix):
    """Load the most recent results file with given prefix."""
    results_files = sorted(RESULTS_DIR.glob(f"{prefix}_*.json"), reverse=True)

    if not results_files:
        print(f"Error: No results found with prefix '{prefix}' in {RESULTS_DIR}")
        return None

    latest_file = results_files[0]
    print(f"Loading {prefix}: {latest_file.name}")

    with open(latest_file, 'r') as f:
        return json.load(f)


def analyze_improvements(baseline_results, finetuned_results):
    """Analyze specific improvements from fine-tuning."""
    # Find examples that were wrong in baseline but correct in fine-tuned
    baseline_wrong = {r['index']: r for r in baseline_results['results'] if not r['correct']}
    finetuned_correct = {r['index']: r for r in finetuned_results['results'] if r['correct']}

    improvements = []
    for idx in baseline_wrong:
        if idx in finetuned_correct:
            improvements.append({
                'index': idx,
                'question': baseline_wrong[idx]['question'],
                'ground_truth': baseline_wrong[idx]['ground_truth'],
                'baseline_prediction': baseline_wrong[idx]['predicted'],
                'finetuned_prediction': finetuned_correct[idx]['predicted'],
            })

    # Find examples that were correct in baseline but wrong in fine-tuned
    baseline_correct = {r['index']: r for r in baseline_results['results'] if r['correct']}
    finetuned_wrong = {r['index']: r for r in finetuned_results['results'] if not r['correct']}

    regressions = []
    for idx in baseline_correct:
        if idx in finetuned_wrong:
            regressions.append({
                'index': idx,
                'question': baseline_correct[idx]['question'],
                'ground_truth': baseline_correct[idx]['ground_truth'],
                'baseline_prediction': baseline_correct[idx]['predicted'],
                'finetuned_prediction': finetuned_wrong[idx]['predicted'],
            })

    return improvements, regressions


def generate_report():
    """Generate detailed comparison report."""
    print("=" * 80)
    print("GSM8K Before/After Comparison Report")
    print("=" * 80)
    print()

    # Load results
    baseline = load_latest_results("baseline_gsm8k")
    finetuned = load_latest_results("finetuned_gsm8k")

    if not baseline or not finetuned:
        print("Error: Could not load both baseline and fine-tuned results")
        print(f"Results directory: {RESULTS_DIR}")
        return False

    print()
    print("=" * 80)
    print("Summary Statistics")
    print("=" * 80)
    print()

    # Calculate metrics
    baseline_acc = baseline['accuracy']
    finetuned_acc = finetuned['accuracy']
    improvement = finetuned_acc - baseline_acc
    improvement_pct = (improvement / baseline_acc * 100) if baseline_acc > 0 else 0

    print(f"Dataset: GSM8K (Grade School Math)")
    print(f"Test samples: {baseline['total_examples']}")
    print()
    print(f"BASELINE (Before Fine-Tuning)")
    print(f"  Model: {baseline['model']}")
    print(f"  Correct: {baseline['correct']}/{baseline['total_examples']}")
    print(f"  Accuracy: {100*baseline_acc:.2f}%")
    print()
    print(f"FINE-TUNED (After QLoRA)")
    print(f"  Model: {finetuned['model']} + QLoRA adapter")
    print(f"  Correct: {finetuned['correct']}/{finetuned['total_examples']}")
    print(f"  Accuracy: {100*finetuned_acc:.2f}%")
    print()
    print(f"IMPROVEMENT")
    print(f"  Absolute: +{100*improvement:.2f} percentage points")
    print(f"  Relative: +{improvement_pct:.1f}%")
    print()

    # Analyze specific improvements
    improvements, regressions = analyze_improvements(baseline, finetuned)

    print("=" * 80)
    print("Detailed Analysis")
    print("=" * 80)
    print()
    print(f"Examples improved (wrong → correct): {len(improvements)}")
    print(f"Examples regressed (correct → wrong): {len(regressions)}")
    print(f"Net improvement: {len(improvements) - len(regressions)} examples")
    print()

    # Show sample improvements
    if improvements:
        print("=" * 80)
        print("Sample Improvements (Baseline Wrong → Fine-Tuned Correct)")
        print("=" * 80)
        print()

        for i, imp in enumerate(improvements[:5], 1):
            print(f"Example {i}:")
            print(f"  Question: {imp['question'][:150]}...")
            print(f"  Ground Truth: {imp['ground_truth']}")
            print(f"  Baseline Predicted: {imp['baseline_prediction']} ✗")
            print(f"  Fine-Tuned Predicted: {imp['finetuned_prediction']} ✓")
            print()

    # Show sample regressions
    if regressions:
        print("=" * 80)
        print("Sample Regressions (Baseline Correct → Fine-Tuned Wrong)")
        print("=" * 80)
        print()

        for i, reg in enumerate(regressions[:3], 1):
            print(f"Example {i}:")
            print(f"  Question: {reg['question'][:150]}...")
            print(f"  Ground Truth: {reg['ground_truth']}")
            print(f"  Baseline Predicted: {reg['baseline_prediction']} ✓")
            print(f"  Fine-Tuned Predicted: {reg['finetuned_prediction']} ✗")
            print()

    # Save comparison report
    PUBLICATION_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = PUBLICATION_DIR / f"gsm8k_comparison_{timestamp}.json"

    comparison_data = {
        "timestamp": timestamp,
        "dataset": "GSM8K",
        "baseline": {
            "accuracy": baseline_acc,
            "correct": baseline['correct'],
            "total": baseline['total_examples'],
            "file": baseline.get('timestamp', 'unknown'),
        },
        "finetuned": {
            "accuracy": finetuned_acc,
            "correct": finetuned['correct'],
            "total": finetuned['total_examples'],
            "file": finetuned.get('timestamp', 'unknown'),
        },
        "improvement": {
            "absolute": improvement,
            "relative_percent": improvement_pct,
            "examples_improved": len(improvements),
            "examples_regressed": len(regressions),
            "net_improvement": len(improvements) - len(regressions),
        },
        "sample_improvements": improvements[:10],
        "sample_regressions": regressions[:5],
    }

    with open(report_file, 'w') as f:
        json.dump(comparison_data, f, indent=2)

    print("=" * 80)
    print("Report Saved")
    print("=" * 80)
    print()
    print(f"Comparison report saved to: {report_file}")
    print()

    # Generate publication-ready summary
    summary_file = PUBLICATION_DIR / "tables" / "gsm8k_results.md"
    summary_file.parent.mkdir(parents=True, exist_ok=True)

    with open(summary_file, 'w') as f:
        f.write("# GSM8K Results: Before/After QLoRA Fine-Tuning\n\n")
        f.write("## Summary Table\n\n")
        f.write("| Metric | Baseline | Fine-Tuned | Improvement |\n")
        f.write("|--------|----------|------------|-------------|\n")
        f.write(f"| Accuracy | {100*baseline_acc:.2f}% | {100*finetuned_acc:.2f}% | +{100*improvement:.2f}pp |\n")
        f.write(f"| Correct | {baseline['correct']}/{baseline['total_examples']} | {finetuned['correct']}/{finetuned['total_examples']} | +{finetuned['correct']-baseline['correct']} |\n")
        f.write(f"| Relative Improvement | - | - | +{improvement_pct:.1f}% |\n")
        f.write("\n")
        f.write("## Configuration\n\n")
        f.write(f"- **Base Model**: Llama 3.1 8B Instruct\n")
        f.write(f"- **Training Method**: QLoRA (4-bit quantization)\n")
        f.write(f"- **Dataset**: GSM8K (Grade School Math)\n")
        f.write(f"- **Test Examples**: {baseline['total_examples']}\n")
        f.write("\n")
        f.write("## Key Findings\n\n")
        f.write(f"- Fine-tuning improved performance by **{100*improvement:.2f} percentage points**\n")
        f.write(f"- **{len(improvements)}** examples improved (wrong → correct)\n")
        f.write(f"- **{len(regressions)}** examples regressed (correct → wrong)\n")
        f.write(f"- **Net gain**: {len(improvements) - len(regressions)} examples\n")

    print(f"Publication summary saved to: {summary_file}")
    print()
    print("=" * 80)
    print("✓ Comparison Complete")
    print("=" * 80)

    return True


if __name__ == "__main__":
    success = generate_report()
    sys.exit(0 if success else 1)
