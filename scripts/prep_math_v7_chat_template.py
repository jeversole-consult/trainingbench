#!/usr/bin/env python3
"""TB-US-078 Trial #5: build training set v7, chat-template-formatted.

Trial #4 (TB-US-077) regressed Instruct from 43% to 23% because
our raw-CoT training format deleted Instruct's native "guess +
reason + confirm-at-end" response structure. Trial #5 tests the
hypothesis that **chat-template-formatted training data**
(matching Instruct's SFT format) will preserve or improve on
bare Instruct.

Composition: 1000 random GSM8K train-split problems (seed=46,
distinct from prior sampling seeds). Each training example
formatted via `tokenizer.apply_chat_template()` with the TB
system prompt v3 + user question + assistant answer. Each
assistant turn ends with `#### N`.

Output file stores the TOKENIZED-STRING representation (the
chat-template result), not raw JSONL. This is a divergence from
v4/v5/v6 which stored `{question, answer}` dicts. Document the
format change in `instruct-chat-template-results.md`.

See docs/user-stories/tb-us-078.md and
docs/math-example/study-design.md Trial #5 pre-registration.
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
OUTPUT_PATH = REPO / "training-sets" / "math-example-v7-chat-template.jsonl"

BASE_MODEL = "meta-llama/Meta-Llama-3.1-8B-Instruct"
SAMPLE_N = 1000
SEED = 46


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
            "apply_chat_template(). Trial #5 depends on this."
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

    # Shuffle with seed=46; take first SAMPLE_N excluding holdout
    rng = random.Random(SEED)
    rng.shuffle(train)
    picked: list[dict] = []
    for ex in train:
        if ex["question"] in holdout_qs:
            continue
        picked.append(ex)
        if len(picked) >= SAMPLE_N:
            break
    assert len(picked) == SAMPLE_N, (
        f"got {len(picked)} unique picks; need {SAMPLE_N}"
    )

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
            # Apply chat template (returns full tokenized string)
            text = tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=False
            )
            if not sample_shown:
                print()
                print("--- sample #0 after chat template ---")
                print(text[:600])
                print("...")
                print(text[-300:])
                print("--- end sample ---")
                print()
                sample_shown = True
            row = {
                "sample_id": f"gsm8k_v7_{i:04d}",
                "question": ex["question"],
                "answer": ex["answer"],
                "text": text,  # the full chat-template string for training
            }
            f.write(json.dumps(row) + "\n")

    # Final disjointness sanity-check
    picked_qs = {ex["question"] for ex in picked}
    overlap = picked_qs & holdout_qs
    assert not overlap, f"ERROR: v7 overlaps holdout by {len(overlap)}"
    print(f"wrote {len(picked)} rows to {OUTPUT_PATH}")
    print(f"disjointness vs holdout: PASS (0 overlap)")


if __name__ == "__main__":
    main()
