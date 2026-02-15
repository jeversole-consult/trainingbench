# GSM8K Training Pipeline

Complete training pipeline for fine-tuning Llama 3.1 8B on GSM8K math problems using QLoRA.

## Quick Start

### 1. Download Dataset

```bash
python scripts/download_gsm8k.py
```

Downloads GSM8K (7,473 training + 1,027 test examples) from Hugging Face.

### 2. Run Baseline Evaluation

```bash
python training/math/baseline.py
```

Evaluates base Llama 3.1 8B model on 100 test examples to establish "before" metrics.

**Expected Results**:
- Accuracy: ~15-25%
- Duration: ~30-45 minutes on RTX 3090

### 3. Train QLoRA Model

```bash
python training/math/train.py
```

Fine-tunes model using QLoRA with hyperparameters from README:
- LoRA rank: 16
- LoRA alpha: 32
- Learning rate: 2e-4
- Epochs: 3
- Batch size: 4 (effective 16 with gradient accumulation)

**Expected Training Time**:
- ~3-4 hours on RTX 3090 (24GB VRAM)
- ~18GB VRAM with 4-bit quantization

### 4. Evaluate Fine-Tuned Model

```bash
python training/math/evaluate.py
```

Evaluates fine-tuned model on same 100 test examples for comparison.

**Expected Results**:
- Accuracy: ~55-65%
- Improvement: +30-40 percentage points

### 5. Generate Comparison Report

```bash
python training/math/compare.py
```

Generates detailed before/after comparison report for publication:
- Summary statistics
- Sample improvements
- Regression analysis
- Publication-ready tables

## Files

- `baseline.py` - Baseline evaluation on untrained model
- `train.py` - QLoRA fine-tuning script
- `evaluate.py` - Fine-tuned model evaluation
- `compare.py` - Before/after comparison report

## Output Directories

- `models/fine-tuned/gsm8k_qlora/` - Trained model and adapter
- `experiments/before_after/` - Evaluation results (JSON)
- `experiments/logs/` - TensorBoard training logs
- `publication/tables/` - Publication-ready summaries

## Hardware Requirements

- **GPU**: NVIDIA RTX 3090 (24GB) or equivalent
- **RAM**: 32GB recommended
- **Storage**: ~50GB for dataset + models

## Configuration

Edit hyperparameters at the top of each script:

- `baseline.py`: MAX_SAMPLES (default: 100)
- `train.py`: LORA_R, LORA_ALPHA, NUM_EPOCHS, BATCH_SIZE
- `evaluate.py`: MAX_SAMPLES (should match baseline)

## TensorBoard

View training progress:

```bash
tensorboard --logdir experiments/logs/gsm8k
```

## Publication Output

The pipeline generates:
1. JSON results files with full predictions
2. Markdown summary tables
3. Before/after comparison data
4. Sample improvements for paper

All ready for inclusion in publication demonstrating PEFT effectiveness.
