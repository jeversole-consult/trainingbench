# GSM8K - Grade School Math Dataset

## Overview

GSM8K (Grade School Math 8K) is a dataset of 8,500 high-quality, linguistically diverse grade school math word problems. Each problem requires multi-step reasoning to solve.

## Dataset Details

- **Total Examples**: 8,500
  - Training: 7,473
  - Test: 1,027
- **Source**: OpenAI
- **License**: MIT
- **Format**: JSON with question/answer pairs
- **Difficulty**: Grade school level (elementary to middle school)

## Download

**Method 1: Hugging Face Hub** (Recommended)
```python
from datasets import load_dataset

dataset = load_dataset("openai/gsm8k", "main")
dataset.save_to_disk("./data")
```

**Method 2: Direct Download**
```bash
git clone https://github.com/openai/grade-school-math.git
```

**Method 3: Using Script**
```bash
python ../../scripts/download_gsm8k.py
```

## Data Format

```json
{
  "question": "Natalia sold clips to 48 of her friends in April, and then she sold half as many clips in May. How many clips did Natalia sell altogether in April and May?",
  "answer": "Natalia sold 48/2 = <<48/2=24>>24 clips in May.\nNatalia sold 48+24 = <<48+24=72>>72 clips altogether in April and May.\n#### 72"
}
```

## Example Problems

**Easy**:
- "Janet's ducks lay 16 eggs per day. She eats three for breakfast every morning and bakes muffins for her friends every day with four. She sells the remainder at the farmers' market daily for $2 per fresh duck egg. How much in dollars does she make every day at the farmers' market?"

**Medium**:
- "A robe takes 2 bolts of blue fiber and half that much white fiber. How many bolts in total does it take?"

**Hard**:
- "Josh decides to try flipping a house. He buys a house for $80,000 and then puts in $50,000 in repairs. This increased the value of the house by 150%. How much profit did he make?"

## Preprocessing

The dataset requires minimal preprocessing:
1. Extract question and answer
2. Parse step-by-step reasoning from answer
3. Extract final numerical answer (after ####)
4. Format for instruction tuning

## Instruction Format

```
### Instruction:
Solve the following math problem step by step. Show your work and explain each step.

### Input:
{question}

### Response:
{step_by_step_solution}
Final Answer: {numerical_answer}
```

## Baseline Performance

**Base Llama 3.1 8B**:
- Accuracy: ~15-25% (typical without fine-tuning)
- Common issues: Incorrect arithmetic, skipped steps, wrong reasoning

**Expected After Fine-Tuning**:
- Accuracy: 55-65% (QLoRA fine-tuned)
- Improvements: Correct step-by-step reasoning, fewer arithmetic errors

## Citations

```bibtex
@article{cobbe2021gsm8k,
  title={Training Verifiers to Solve Math Word Problems},
  author={Cobbe, Karl and Kosaraju, Vineet and Bavarian, Mohammad and Chen, Mark and Jun, Heewoo and Kaiser, Lukasz and Plappert, Matthias and Tworek, Jerry and Hilton, Jacob and Nakano, Reiichiro and Hesse, Christopher and Schulman, John},
  journal={arXiv preprint arXiv:2110.14168},
  year={2021}
}
```

## Training Hyperparameters (Recommended)

```python
# QLoRA Configuration
lora_r = 16
lora_alpha = 32
lora_dropout = 0.05
target_modules = ["q_proj", "v_proj", "k_proj", "o_proj"]

# Training
batch_size = 4
gradient_accumulation_steps = 4
learning_rate = 2e-4
num_epochs = 3
max_length = 512

# Quantization
load_in_4bit = True
bnb_4bit_quant_type = "nf4"
bnb_4bit_compute_dtype = "float16"
```

## Expected Training Time

- **GPU**: RTX 3090 (24GB)
- **Duration**: ~3-4 hours for 3 epochs
- **Memory**: ~18GB VRAM with QLoRA

## Status

- [ ] Dataset downloaded
- [ ] Data preprocessed
- [ ] Instruction format created
- [ ] Baseline evaluation complete
- [ ] Fine-tuning complete
- [ ] Final evaluation complete
- [ ] Before/after comparison documented
