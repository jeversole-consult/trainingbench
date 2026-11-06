#!/usr/bin/env python3
"""TB-US-085 Trial #9: analyze 4-draw multi-seed results for adapter v10.

Adapter v10 = rank 32 at attn+MLP (otherwise identical to v9).
E36-E39 pinned to adapter v10 × harness v5 (holdout).

Extends scripts/tb_us_082_analysis.py with Trial #9 rows.
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
    if not r: return None
    state, rj = r
    d = json.loads(rj) if rj else {}
    if not d: return None
    n = d.get('n_samples', 0); k = d.get('correct_count', 0); v = d.get('value', 0)
    priority_counts = {p: 0 for p in PRIORITIES}
    priority_correct = {p: 0 for p in PRIORITIES}
    hash_buckets = {0: 0, 1: 0, 2: 0, 3: 0}
    for s in d.get('per_sample', []):
        ans = s.get('actual_answer', '')
        p = classify_priority(ans)
        priority_counts[p] += 1
        if s.get('correct'): priority_correct[p] += 1
        h = min(count_hashes(ans), 3)
        hash_buckets[h] += 1
    dual_plus = hash_buckets[2] + hash_buckets[3]
    return {
        'eid': eid, 'label': label, 'state': state, 'n': n, 'k': k, 'v': v,
        'priority_counts': priority_counts, 'priority_correct': priority_correct,
        'hash_buckets': hash_buckets,
        'dual_hash_pct': dual_plus * 100 / n if n else 0,
        'within_p1_strict_pct': (priority_correct['P1_strict'] * 100 / priority_counts['P1_strict'])
                                if priority_counts['P1_strict'] else 0,
    }


def print_result(r):
    print(f"=== E{r['eid']}  {r['label']} ===")
    print(f"  Score: {r['k']} / {r['n']}  ({r['v']*100:.1f}%)")
    print(f"  Harness-priority breakdown:")
    for p in PRIORITIES:
        cn = r['priority_counts'][p]; ck = r['priority_correct'][p]
        if cn > 0:
            print(f"    {p:<22} count={cn:3d}  correct={ck:3d}/{cn:<3d} ({ck*100/cn:4.1f}%)")
    print(f"  Dual-#### retention: {r['dual_hash_pct']:.1f}%")
    print(f"  Within-P1-strict accuracy: {r['within_p1_strict_pct']:.1f}%")
    print()


def main():
    print("TB-US-085 Trial #9 — pattern analysis + full-series comparison")
    print("=" * 76); print()

    print("--- Trial #9 adapter v10 (rank 32 attn+MLP) results ---")
    draws = []
    for eid, label in [(36, 'adapter-v10 holdout replicate-1'),
                       (37, 'adapter-v10 holdout replicate-2'),
                       (38, 'adapter-v10 holdout replicate-3'),
                       (39, 'adapter-v10 holdout replicate-4')]:
        r = analyze(eid, label)
        if r: print_result(r); draws.append(r)

    print("=" * 76)
    print("Adapter v10 holdout multi-seed statistics:")
    print("=" * 76)
    vals = [r['v']*100 for r in draws]
    duals = [r['dual_hash_pct'] for r in draws]
    withinp1 = [r['within_p1_strict_pct'] for r in draws]
    mean = statistics.mean(vals); sd = statistics.stdev(vals)
    print(f"  Holdout draws: {vals}")
    print(f"  Mean: {mean:.2f}%")
    print(f"  SD:   {sd:.3f}pt")
    print(f"  Range: {min(vals):.1f} – {max(vals):.1f} (spread {max(vals)-min(vals):.1f}pt)")
    print(f"  Dual-#### retention mean: {statistics.mean(duals):.1f}%")
    print(f"  Within-P1-strict accuracy mean: {statistics.mean(withinp1):.1f}%")

    # Compare to v9 (from Trial #8)
    V9_MEAN = 53.75; V9_SD = 2.78
    diff = mean - V9_MEAN
    pooled_sd = ((sd**2 + V9_SD**2) / 2) ** 0.5
    print()
    print(f"  vs. Adapter v9 (Trial #8, rank 16 attn+MLP):")
    print(f"    v9 mean 53.75% (SD 2.78pt); v10 mean {mean:.2f}% (SD {sd:.2f}pt)")
    print(f"    Difference: +{diff:.2f}pt  Pooled SD: {pooled_sd:.2f}pt")
    print(f"    |diff|/pooled-SD = {abs(diff)/pooled_sd:.2f}×")
    if abs(diff)/pooled_sd < 1:
        verdict = "INDISTINGUISHABLE"
    elif abs(diff)/pooled_sd < 2:
        verdict = "MARGINAL SIGNAL"
    else:
        verdict = "REAL SIGNAL"
    print(f"    Verdict: {verdict}")

    print()
    print("=" * 76)
    print("Full series 5-row comparison (holdout; multi-seed mean):")
    print("=" * 76)
    print(f"{'Setup':<42}{'Holdout accuracy':<28}")
    print(f"{'-'*42}{'-'*28}")
    print(f"{'Bare Instruct':<42}{'86/200 (43%) [single draw]':<28}")
    print(f"{'Adapter v5 (Trial #4, raw-CoT, rank 32)':<42}{'46/200 (23%) [single draw]':<28}")
    print(f"{'Adapter v7 (Trial #5, attn-only, rank 16)':<42}{'42.00% ± 2.65pt (4 draws)':<28}")
    print(f"{'Adapter v8 (Trial #6, attn-only, 5000)':<42}{'41.62% ± 2.56pt (4 draws)':<28}")
    print(f"{'Adapter v9 (Trial #8, +MLP, rank 16)':<42}{'53.75% ± 2.78pt (4 draws)':<28}")
    print(f"{'Adapter v10 (Trial #9, +MLP, rank 32)':<42}{mean:.2f}% ± {sd:.2f}pt (4 draws)")


if __name__ == '__main__':
    main()
