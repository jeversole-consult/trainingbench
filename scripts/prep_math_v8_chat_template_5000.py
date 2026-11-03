#!/usr/bin/env python3
"""TB-US-080 Trial #6 (Candidate A): build training set v8, 5000 samples.

Scale-up of TB-US-079's v7 (1000 samples). Same chat-template
formatting discipline; different sampling seed (47 vs. 46); 5x more
rows. Overlap with v7 ALLOWED (both are random samples from the same
GSM8K train split; expected overlap ≈ 1000 × 5000 / |train| ≈ 670
rows); this keeps the sampling procedure simple and the v7-vs-v8
comparison about size, not specific examples.

Format: tokenizer.apply_chat_template with messages = [system, user,
assistant], assistant turn ends with `#### N`. This is byte-identical
to v7's recipe except the random sample.

See docs/user-stories/tb-us-080.md pre-registered Candidate A.
"""
from __future__ import annotations

import json
import random
from pathlib import Path

from datasets import load_from_disk
from transformers import AutoTokenizer


REPO = Path(__file__).resolve().parent.parent
GSM8K_PATH = REPO / "datasets" / "math" / "data"
HOLDOUT_PATH = REPO / "backend" / "harnesses" / "data" / "math_eval_200_holdout.jsonl"
PROMPT_PATH = REPO / "rag-seeds" / "math-example-v1" / "system-prompt.txt"
OUTPUT_PATH = REPO / "training-sets" / "math-example-v8-chat-template-5000.jsonl"
V7_PATH = REPO / "training-sets" / "math-example-v7-chat-template.jsonl"

BASE_MODEL = "meta-llama/Meta-Llama-3.1-8B-Instruct"
SAMPLE_N = 5000
SEED = 47


def load_questions(path: Path) -> set[str]:
    out: set[str] = set()
    if not path.exists():
        return out
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                out.add(json.loads(line)["question"])
    return out


def main() -> None:
    print(f"loading tokenizer for {BASE_MODEL} (for chat template)...")
    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)
    if not tokenizer.chat_template:
        raise SystemExit(
            "ERROR: tokenizer has no chat_template; cannot apply "
            "apply_chat_template(). v8 depends on this."
        )
    print(f"  chat_template present: {len(tokenizer.chat_template)} chars")

    system_prompt = PROMPT_PATH.read_text(encoding="utf-8").strip()
    print(f"  system prompt v3 loaded: {len(system_prompt)} chars")

    print(f"loading GSM8K...")
    ds = load_from_disk(str(GSM8K_PATH))
    train = list(ds["train"])
    print(f"  {len(train)} train rows")

    holdout_qs = load_questions(HOLDOUT_PATH)
    print(f"  holdout qs: {len(holdout_qs)}")

    v7_qs = load_questions(V7_PATH)
    print(f"  v7 qs: {len(v7_qs)} (overlap allowed; informational only)")

    # Shuffle with seed=47; take first SAMPLE_N excluding holdout
    rng = random.Random(SEED)
    rng.shuffle(train)
    picked: list[dict] = []
    seen_qs: set[str] = set()
    for ex in train:
        if ex["question"] in holdout_qs:
            continue
        if ex["question"] in seen_qs:
            continue
        seen_qs.add(ex["question"])
        picked.append(ex)
        if len(picked) >= SAMPLE_N:
            break
    assert len(picked) == SAMPLE_N, (
        f"got {len(picked)} unique picks; need {SAMPLE_N}"
    )

    # Overlap stats vs v7 (informational)
    picked_qs = {ex["question"] for ex in picked}
    overlap_v7 = picked_qs & v7_qs
    print(f"  v8 ∩ v7 = {len(overlap_v7)} rows "
          f"(expected ≈ {int(SAMPLE_N * len(v7_qs) / len(train))} by random)")

    # Format each as chat template, emit as JSONL with a 'text' field
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    sample_shown = False
    with OUTPUT_PATH.open("w", encoding="utf-8") as f:
        for i, ex in enumerate(picked):
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": ex["question"]},
                {"role": "assistant", "content": ex["answer"]},
            ]
            text = tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=False
            )
            if not sample_shown:
                print()
                print("--- sample #0 after chat template ---")
                print(text[:400])
                print("...")
                print(text[-200:])
                print("--- end sample ---")
                print()
                sample_shown = True
            row = {
                "sample_id": f"gsm8k_v8_{i:04d}",
                "question": ex["question"],
                "answer": ex["answer"],
                "text": text,
            }
            f.write(json.dumps(row) + "\n")

    # Final disjointness sanity-check vs holdout
    overlap_ho = picked_qs & holdout_qs
    assert not overlap_ho, f"ERROR: v8 overlaps holdout by {len(overlap_ho)}"
    print(f"wrote {len(picked)} rows to {OUTPUT_PATH}")
    print(f"disjointness vs holdout: PASS (0 overlap)")
    print(f"overlap vs v7: {len(overlap_v7)} rows (allowed; informational)")


if __name__ == "__main__":
    main()
