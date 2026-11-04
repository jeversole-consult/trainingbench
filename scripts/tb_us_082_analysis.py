#!/usr/bin/env python3
"""TB-US-082 Phase 4: pattern analysis across Trial #8 experiments.

Extends scripts/tb_us_080_analysis.py with:
- Trial #8 holdout multi-seed draws (E31-E34) → mean, SD, range
- Trial #8 baseline-test (E35)
- Full 5-row series comparison
"""
from __future__ import annotations

import json
import re
import sqlite3
import statistics
import sys

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
        return None
    state, rj = r
    d = json.loads(rj) if rj else {}
    if not d:
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

    dual_plus = hash_buckets[2] + hash_buckets[3]
    return {
        'eid': eid, 'label': label, 'state': state,
        'n': n, 'k': k, 'v': v,
        'priority_counts': priority_counts, 'priority_correct': priority_correct,
        'hash_buckets': hash_buckets, 'hash_correct': hash_correct,
        'dual_hash_pct': dual_plus * 100 / n if n else 0,
        'within_p1_strict_pct': (priority_correct['P1_strict'] * 100 / priority_counts['P1_strict']) if priority_counts['P1_strict'] else 0,
    }


def print_result(r):
    print(f"=== E{r['eid']}  {r['label']} ===")
    print(f"  Harness score: {r['k']} / {r['n']}  ({r['v']*100:.1f}%)")
    print(f"  Harness-priority breakdown:")
    for p in PRIORITIES:
        c_n = r['priority_counts'][p]
        c_k = r['priority_correct'][p]
        if c_n > 0:
            pct = c_k*100/c_n if c_n else 0
            print(f"    {p:<22} count={c_n:3d}  correct={c_k:3d}/{c_n:<3d} ({pct:4.1f}%)")
    print(f"  Dual-#### retention: {r['dual_hash_pct']:.1f}%")
    print(f"  Within-P1-strict accuracy: {r['within_p1_strict_pct']:.1f}%")
    print()


def main():
    print("TB-US-082 Trial #8 — pattern analysis + series comparison")
    print("=" * 72)
    print()

    # Trial #8 — all 5 experiments
    print("--- Trial #8 adapter v9 (MLP-expanded LoRA) results ---")
    v9_draws = []
    for eid, label in [
        (31, 'adapter-v9 holdout replicate-1'),
        (32, 'adapter-v9 holdout replicate-2'),
        (33, 'adapter-v9 holdout replicate-3'),
        (34, 'adapter-v9 holdout replicate-4'),
    ]:
        r = analyze(eid, label)
        if r:
            print_result(r)
            v9_draws.append(r)
    r_bt = analyze(35, 'adapter-v9 baseline-test (E_in_v9)')
    if r_bt:
        print_result(r_bt)

    # Summary statistics
    print("=" * 72)
    print("Adapter v9 holdout multi-seed statistics:")
    print("=" * 72)
    v9_vals = [r['v']*100 for r in v9_draws]
    v9_dual = [r['dual_hash_pct'] for r in v9_draws]
    v9_withinp1 = [r['within_p1_strict_pct'] for r in v9_draws]
    print(f"  Holdout draws: {v9_vals}")
    print(f"  Mean: {statistics.mean(v9_vals):.2f}%")
    print(f"  SD:   {statistics.stdev(v9_vals):.3f}pt")
    print(f"  Range: {min(v9_vals):.1f} – {max(v9_vals):.1f} (spread {max(v9_vals)-min(v9_vals):.1f}pt)")
    print(f"  Dual-#### retention mean: {statistics.mean(v9_dual):.1f}%")
    print(f"  Within-P1-strict accuracy mean: {statistics.mean(v9_withinp1):.1f}%")
    print()
    print(f"  Baseline-test (E35, single draw): {r_bt['v']*100:.1f}%")
    print(f"    (dual-#### {r_bt['dual_hash_pct']:.1f}%; within-P1 {r_bt['within_p1_strict_pct']:.1f}%)")

    # 4-cell comparison across the full series (prior means for v7/v8 from Trial #7)
    print()
    print("=" * 72)
    print("Full series 4-cell comparison (baseline-test / holdout, score + dual-#### retention):")
    print("=" * 72)
    print(f"{'Setup':<36}{'baseline-test':<30}{'holdout':<30}")
    print(f"{'-'*36}{'-'*30}{'-'*30}")
    print(f"{'Bare Instruct':<36}{'86/200 (43%) dual~45%':<30}{'86/200 (43%) dual~45%':<30}")
    print(f"{'Adapter v5 (Trial #4, raw-CoT)':<36}{'38/200 (19%) dual=23%':<30}{'46/200 (23%) dual=20%':<30}")
    print(f"{'Adapter v7 (Trial #5, attn-only)':<36}{'88/200 (44%) dual=63%':<30}{'42.00% mean (4) dual~61%':<30}")
    print(f"{'Adapter v8 (Trial #6, 5000 samp)':<36}{'75/200 (38%) dual=74%':<30}{'41.62% mean (4) dual~75%':<30}")
    bt_str = f"{r_bt['k']}/{r_bt['n']} ({r_bt['v']*100:.1f}%) dual={r_bt['dual_hash_pct']:.0f}%"
    ho_str = f"{statistics.mean(v9_vals):.2f}% mean (4) dual~{statistics.mean(v9_dual):.0f}%"
    print(f"{'Adapter v9 (Trial #8, +MLP)':<36}{bt_str:<30}{ho_str:<30}")


if __name__ == '__main__':
    main()
