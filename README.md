# TrainingBench - PEFT Demonstration Research

**Publication-Ready PEFT Before/After Demonstrations**

A research project demonstrating the effectiveness of Parameter-Efficient Fine-Tuning (PEFT) on Llama models across five diverse domains. Built to run on consumer hardware ($4,000 machine) to prove that world-class AI fine-tuning is accessible without expensive cloud infrastructure.

---

## Project Overview

**Goal**: Create publishable before/after PEFT demonstrations showing dramatic improvements across 5 different subject matter disciplines.

**Target Models**:
- Llama 3.1 8B (primary - fits 24GB VRAM with QLoRA)
- Llama 3.1 70B (stretch goal - 4-bit quantization)

**Hardware**:
- NVIDIA RTX 3090 (24GB VRAM)
- Consumer-grade home server
- Total cost: ~$4,000

**Training Method**: QLoRA (Quantized Low-Rank Adaptation)
- 4-bit quantization for memory efficiency
- LoRA adapters for parameter-efficient training
- Full reproducibility on consumer hardware

---

## Five Demonstration Domains

### 1. Medical Clinical Note Summarization
**Dataset**: MIMIC-III / MIMIC-IV
**Task**: Summarize clinical discharge notes with proper medical terminology
**Before**: Generic, inaccurate medical summaries with hallucinated drug names
**After**: Accurate summaries using correct medical terms, diagnoses, and medications
**Media Angle**: Healthcare AI accessibility for smaller medical practices

**Metrics**:
- ROUGE-L score
- Medical terminology accuracy
- Factual consistency

---

### 2. Legal Contract Clause Analysis
**Dataset**: CUAD (Contract Understanding Atticus Dataset)
**Task**: Identify and classify contract clauses (indemnification, termination, liability, etc.)
**Before**: Vague, sometimes incorrect clause interpretations
**After**: Precise clause identification with key term extraction
**Media Angle**: Affordable legal AI for small firms and startups

**Metrics**:
- F1 score per clause type
- Precision/Recall
- Exact match accuracy

**Dataset Details**:
- 500+ contracts
- 13,000+ expert annotations
- 41 label categories
- Available: Hugging Face (theatticusproject/cuad-qa)
- License: CC-BY 4.0

---

### 3. Agricultural Pest & Disease Diagnosis
**Dataset**: CDDM (Crop Disease Detection Multimodal)
**Task**: Diagnose crop diseases from symptom descriptions
**Before**: Generic gardening advice
**After**: Specific pathogen identification with targeted treatment recommendations
**Media Angle**: Precision agriculture for farmers without expensive services

**Metrics**:
- Classification accuracy
- Treatment recommendation relevance
- Regional/seasonal appropriateness

**Dataset Details**:
- 137,000 images
- 1M+ question-answer pairs
- Disease identification to management practices
- Available: GitHub (CDDM dataset)

---

### 4. K-12 Math Tutoring with Step-by-Step Explanations
**Dataset**: GSM8K (Grade School Math 8K)
**Task**: Solve math word problems with pedagogical step-by-step explanations
**Before**: Incorrect reasoning, skipped steps, wrong answers
**After**: Clear step-by-step breakdowns with educational explanations
**Media Angle**: Education equity - free AI tutoring for underresourced schools

**Metrics**:
- Answer accuracy (%)
- Reasoning step completeness
- Explanation clarity (human eval)

**Dataset Details**:
- 8,500 high-quality math word problems
- Multi-step reasoning required
- Available: Hugging Face (openai/gsm8k)
- License: MIT
- **BEST STARTING POINT** - most documented, fastest setup

---

### 5. Cybersecurity Log Analysis & Threat Detection
**Dataset**: Trendyol Cybersecurity / Fenrir v2.0
**Task**: Parse security logs, identify threats, classify severity
**Before**: Generic log descriptions
**After**: Specific threat classification with severity levels and MITRE ATT&CK mapping
**Media Angle**: Enterprise-grade security for small businesses without expensive tools

**Metrics**:
- Threat detection accuracy
- False positive rate
- Classification precision per threat type

**Dataset Details**:
- Trendyol: 53,202 instruction-tuning examples, 200+ domains
- Fenrir v2.0: 84,000 rows covering detection, SIEM, IR playbooks
- Available: Hugging Face
- Includes refusal templates for responsible AI

---

## Project Structure

```
trainingbench/
├── datasets/              # Training data for each domain
│   ├── medical/          # MIMIC-III/IV data
│   ├── legal/            # CUAD contracts
│   ├── agriculture/      # CDDM crop disease data
│   ├── math/             # GSM8K problems
│   └── security/         # Cybersecurity logs
│
├── models/               # Model storage
│   ├── base/            # Base Llama models
│   └── fine-tuned/      # PEFT adapters for each domain
│
├── training/            # Training scripts per domain
│   ├── medical/
│   ├── legal/
│   ├── agriculture/
│   ├── math/            # START HERE
│   └── security/
│
├── experiments/         # Results and analysis
│   ├── before_after/   # Side-by-side comparisons
│   ├── metrics/        # Quantitative results
│   └── logs/           # Training logs
│
├── notebooks/          # Jupyter notebooks for analysis
│
├── publication/        # Publication materials
│   ├── figures/       # Charts and graphs
│   ├── tables/        # Metric comparisons
│   └── drafts/        # Article drafts
│
└── scripts/           # Utility scripts
```

---

## Training Pipeline

### Phase 1: Setup (Per Domain)
1. Download dataset
2. Preprocess and format for instruction tuning
3. Create train/validation/test splits
4. Document dataset statistics

### Phase 2: Baseline Evaluation
1. Load base Llama model (quantized)
2. Run test set through base model
3. Collect "before" outputs
4. Calculate baseline metrics

### Phase 3: Fine-Tuning
1. Configure QLoRA hyperparameters
2. Train PEFT adapter
3. Monitor training metrics
4. Save adapter checkpoints

### Phase 4: Evaluation
1. Load fine-tuned model
2. Run same test set
3. Collect "after" outputs
4. Calculate post-training metrics

### Phase 5: Analysis
1. Compare before/after side-by-side
2. Generate visualization
3. Document improvements
4. Prepare publication materials

---

## Recommended Order

1. **Math (GSM8K)** - Start here
   - Fastest dataset setup
   - Most documented training process
   - Clear success metrics
   - Reproducible results

2. **Legal (CUAD)** - Second
   - Immediately downloadable
   - Clean dataset
   - Strong practical value

3. **Cybersecurity** - Third
   - Ready-to-go format
   - Hot topic for media

4. **Medical** - Fourth
   - Requires access approval (few days)
   - Most impressive results

5. **Agriculture** - Fifth
   - May require data curation

---

## Hardware Requirements

**Minimum** (for 8B models):
- GPU: 16GB VRAM (RTX 4080, A4000)
- RAM: 32GB system RAM
- Storage: 500GB SSD

**Recommended** (current setup):
- GPU: 24GB VRAM (RTX 3090, RTX 4090, A5000)
- RAM: 64GB+ system RAM
- Storage: 1TB+ NVMe SSD

**For 70B models**:
- Same as recommended
- 4-bit quantization required
- Longer training times

---

## Key Technologies

- **Models**: Llama 3.1 8B/70B
- **Fine-Tuning**: QLoRA (4-bit + LoRA)
- **Framework**: Hugging Face Transformers + PEFT
- **Training**: DeepSpeed/Accelerate
- **Datasets**: Hugging Face Hub + Public Research Data
- **Tracking**: Weights & Biases (optional)

---

## Publication Strategy

**Target Audiences**:
- AI/ML media outlets
- Domain-specific publications (healthcare, legal, agriculture, education, security)
- Technical blogs and research communities

**Key Messages**:
1. World-class AI fine-tuning is accessible on consumer hardware
2. $4,000 machine achieves results comparable to cloud-based solutions
3. Open-source models + PEFT = democratized AI
4. Practical applications across critical domains

**Deliverables**:
- Side-by-side before/after examples
- Quantitative metrics (accuracy, F1, ROUGE)
- Training time and cost comparisons
- Reproducible methodology
- Open-source code and documentation

---

## Getting Started

### Quick Start (Math Domain)

```bash
cd /home/jeversole/trainingbench

# 1. Set up environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. Download GSM8K dataset
python scripts/download_gsm8k.py

# 3. Run baseline evaluation
python training/math/baseline.py

# 4. Fine-tune model
python training/math/train.py

# 5. Evaluate fine-tuned model
python training/math/evaluate.py

# 6. Generate comparison
python training/math/compare.py
```

---

## Version

- **Version**: 0.1.0 (Initial Setup)
- **Created**: 2026-02-14
- **Status**: Setup Phase

---

## License

Research project - License TBD based on dataset requirements and publication plans.

---

## Contact

Project maintained for PEFT research and publication demonstrations.
