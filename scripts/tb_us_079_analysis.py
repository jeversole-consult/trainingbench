#!/usr/bin/env python3
"""TB-US-079 Phase 4: pattern analysis across all Trial #5 experiments.

Compares adapter v7 (Trial #5) vs. adapter v5 (Trial #4) vs. bare Instruct
on three signals:

1. Harness scoring: X/200 correct
2. Harness-priority breakdown: at which regex priority did the extracted
   answer get caught? (P1_strict = `#### N`; P1_unit = `#### $N`;
   P2_final_answer; P3_trailing_number; none)
3. #### occurrence counts per output (0, 1, 2, 3+). 2+ = dual-####
   "guess-reason-confirm" structure (Instruct's SFT behavior).

Reads from `backend/db/trainingbench.db` experiments table.
"""
from __future__ import annotations

import json
import re
import sqlite3
import sys

# Replicate the patched harness regex priorities (TB-US-076)
P1_STRICT = re.compile(r'####\s*([-+]?\d[\d,.]*)')
P1_UNIT = re.compile(r'####\s*(\$|[A-Za-z%])')
P2 = re.compile(r'(?:final\s*answer|answer\s*is|^answer)[:=]?\s*\$?([-+]?\d[\d,.]*)',
                re.IGNORECASE | re.MULTILINE)
P3 = re.compile(r'(?<![\d.])([-+]?\d+(?:\.\d+)?)')
HASH_ANY = re.compile(r'####\s*\$?[-+]?[\d]|####\s*[A-Za-z]')

PRIORITIES = ['P1_strict', 'P1_unit_prefix', 'P2_final_answer', 'P3_trailing_number', 'none']


def classify_priority(ans: str) -> str:
    if P1_STRICT.search(ans):
        return 'P1_strict'
    elif P1_UNIT.search(ans):
        return 'P1_unit_prefix'
    elif P2.search(ans):
        return 'P2_final_answer'
    elif P3.search(ans):
        return 'P3_trailing_number'
    else:
        return 'none'


def count_hashes(ans: str) -> int:
    return len(HASH_ANY.findall(ans))


def analyze(eid: int, label: str):
    with sqlite3.connect('backend/db/trainingbench.db') as c:
        r = c.execute(
            'SELECT state, results_json FROM experiments WHERE experiment_id=?',
            (eid,),
        ).fetchone()
    if not r:
        print(f"E{eid} not found")
        return None
    state, rj = r
    d = json.loads(rj) if rj else {}
    if not d:
        print(f"E{eid} ({label}) state={state} — no results")
        return None

    n = d.get('n_samples', 0)
    k = d.get('correct_count', 0)
    v = d.get('value', 0)
    priority_counts = {p: 0 for p in PRIORITIES}
    priority_correct = {p: 0 for p in PRIORITIES}
    hash_buckets = {0: 0, 1: 0, 2: 0, 3: 0}
    hash_correct = {0: 0, 1: 0, 2: 0, 3: 0}

    for s in d.get('per_sample', []):
        ans = s.get('actual_answer', '')
        p = classify_priority(ans)
        priority_counts[p] += 1
        if s.get('correct'):
            priority_correct[p] += 1
        h = min(count_hashes(ans), 3)
        hash_buckets[h] += 1
        if s.get('correct'):
            hash_correct[h] += 1

    print(f"=== E{eid}  {label}  (state={state}) ===")
    print(f"  Harness score: {k} / {n}  ({v*100:.1f}%)")
    print(f"  Harness-priority breakdown:")
    for p in PRIORITIES:
        c_n = priority_counts[p]
        c_k = priority_correct[p]
        if c_n > 0:
            print(f"    {p:<22} count={c_n:3d}  correct={c_k:3d}/{c_n:<3d} ({c_k*100/c_n:4.1f}%)")
    print(f"  '####' occurrences per output (dual-#### = 2+):")
    for h in [0, 1, 2, 3]:
        c_n = hash_buckets[h]
        c_k = hash_correct[h]
        label_h = f"{h}" if h < 3 else "3+"
        if c_n > 0:
            print(f"    {label_h} ####: count={c_n:3d}  correct={c_k:3d}/{c_n:<3d} ({c_k*100/c_n:4.1f}%)")
    dual_plus = hash_buckets[2] + hash_buckets[3]
    print(f"  Dual-#### retention: {dual_plus}/{n} ({dual_plus*100/n:.1f}%)")
    print()
    return {
        'eid': eid,
        'label': label,
        'score': f"{k}/{n} ({v*100:.1f}%)",
        'dual_hash_pct': dual_plus * 100 / n if n else 0,
        'priority_counts': priority_counts,
        'priority_correct': priority_correct,
        'hash_buckets': hash_buckets,
    }


def main():
    print("TB-US-079 Trial #5 pattern analysis")
    print("=" * 70)
    print()
    print("Prior-trial baselines (for comparison):")
    print("-" * 70)
    analyze(17, 'adapter-v5 baseline-test (Trial #4)')
    analyze(18, 'adapter-v5 holdout (Trial #4)')
    analyze(19, 'bare-Instruct baseline-test (Trial #4 control)')

    print("Trial #5 (adapter v7, chat-template-formatted) results:")
    print("-" * 70)
    rows = [
        (20, 'adapter-v7 baseline-test (E_in_v7)'),
        (21, 'adapter-v7 holdout (E_holdout_v7) — primary H5b/H5c'),
        (22, 'bare-Instruct holdout (E_bare_holdout) — fills labeling-correction gap'),
    ]
    results = {}
    for eid, label in rows:
        results[eid] = analyze(eid, label)

    print("=" * 70)
    print("Trial #5 four-cell comparison (score, dual-#### retention):")
    print("=" * 70)
    def cell(eid):
        r = results.get(eid)
        if not r:
            return '    pending'
        return f"{r['score']:<14} dual={r['dual_hash_pct']:.1f}%"
    print(f"{'':<35}{'baseline-test':<30}{'holdout':<30}")
    bare_bt = "86/200 (43.0%) dual=45.5%  (E19 Trial #4)"
    bare_ho = cell(22)
    v5_bt   = "38/200 (19.0%) dual=23.5%  (E17 Trial #4)"
    v5_ho   = "46/200 (23.0%) dual=20.0%  (E18 Trial #4)"
    v7_bt   = cell(20)
    v7_ho   = cell(21)
    print(f"{'Bare Instruct':<35}{bare_bt:<40}{bare_ho:<30}")
    print(f"{'Adapter v5 (Trial #4)':<35}{v5_bt:<40}{v5_ho:<30}")
    print(f"{'Adapter v7 (Trial #5)':<35}{v7_bt:<40}{v7_ho:<30}")


if __name__ == '__main__':
    main()
