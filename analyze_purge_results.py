"""
Analyze Phase 1 Purge Results
"""

import csv
import json
from collections import Counter

import os

# File paths
script_dir = os.path.dirname(os.path.abspath(__file__))
data_dir = os.path.join(script_dir, "[PUB] India_runs_data_and_ai_challenge", "India_runs_data_and_ai_challenge")
LOG_FILE = os.path.join(data_dir, "purge_log.csv")
CLEANED_FILE = os.path.join(data_dir, "cleaned_candidates.jsonl")

print("=" * 70)
print("PHASE 1 PURGE ENGINE - RESULTS ANALYSIS")
print("=" * 70)
print()

# Analyze rejection reasons
print("Loading purge log...")
rejection_reasons = []
with open(LOG_FILE, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        # Extract just the filter name (Filter 1A, Filter 2A, etc.)
        reason = row['failure_reason']
        filter_name = reason.split(':')[0]
        rejection_reasons.append(filter_name)

# Count rejections by filter
rejection_counts = Counter(rejection_reasons)
total_rejected = sum(rejection_counts.values())

print(f"\nREJECTION BREAKDOWN (Total Rejected: {total_rejected:,})")
print("-" * 70)
for filter_name, count in sorted(rejection_counts.items()):
    percentage = (count / total_rejected * 100) if total_rejected > 0 else 0
    print(f"{filter_name:20s}: {count:7,} ({percentage:5.1f}%)")

# Count cleaned candidates
print("\nCounting valid candidates...")
valid_count = 0
with open(CLEANED_FILE, 'r', encoding='utf-8') as f:
    for line in f:
        valid_count += 1

total_candidates = total_rejected + valid_count
print()
print("=" * 70)
print("FINAL STATISTICS")
print("=" * 70)
print(f"Total candidates:     {total_candidates:7,}")
print(f"Valid candidates:     {valid_count:7,} ({valid_count/total_candidates*100:5.1f}%)")
print(f"Rejected candidates:  {total_rejected:7,} ({total_rejected/total_candidates*100:5.1f}%)")
print("=" * 70)

# Show sample rejections for each filter
print("\nSAMPLE REJECTIONS BY FILTER:")
print("-" * 70)
with open(LOG_FILE, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    samples_shown = {}
    for row in reader:
        reason = row['failure_reason']
        filter_name = reason.split(':')[0]
        if filter_name not in samples_shown:
            print(f"\n{filter_name}:")
            print(f"  Candidate: {row['anonymized_name']} ({row['candidate_id']})")
            print(f"  Reason: {reason}")
            samples_shown[filter_name] = True
            if len(samples_shown) >= 5:
                break

print()
