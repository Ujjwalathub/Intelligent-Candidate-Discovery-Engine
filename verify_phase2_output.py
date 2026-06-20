"""
Verification Script for Phase 2 Output
Validates acceptance criteria from the PRD:
1. Distribution Accuracy: Top 1000 candidates fall within 5-9 YoE range
2. Relevance: Top 50 candidates have strong Vector DB, PyTorch, NLP experience
3. Data Integrity: No data loss, only new scoring fields added
"""

import json
import numpy as np
from collections import Counter
from typing import List, Dict, Any


def load_jsonl(filepath: str) -> List[Dict[str, Any]]:
    """Load JSONL file."""
    records = []
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            records.append(json.loads(line))
    return records


def verify_distribution_accuracy(candidates: List[Dict[str, Any]], top_n: int = 1000):
    """
    Acceptance Criterion 1: Top N candidates should fall within 5-9 YoE range.
    """
    print("=" * 80)
    print(f"Criterion 1: Distribution Accuracy (Top {top_n} candidates)")
    print("=" * 80)
    
    top_candidates = candidates[:top_n]
    yoe_values = [c.get('years_of_experience', 0) for c in top_candidates]
    
    # Count how many fall in 5-9 range
    in_range = sum(1 for yoe in yoe_values if 5 <= yoe <= 9)
    percentage = (in_range / len(top_candidates)) * 100
    
    print(f"Candidates in 5-9 YoE range: {in_range}/{len(top_candidates)} ({percentage:.1f}%)")
    
    # YoE distribution
    yoe_distribution = Counter(yoe_values)
    print(f"\nYears of Experience Distribution (Top {top_n}):")
    for yoe in sorted(yoe_distribution.keys()):
        count = yoe_distribution[yoe]
        bar = '█' * (count // 10)
        print(f"  {yoe:2.0f} years: {count:4d} {bar}")
    
    # Statistics
    print(f"\nStatistics:")
    print(f"  Mean YoE: {np.mean(yoe_values):.2f}")
    print(f"  Median YoE: {np.median(yoe_values):.2f}")
    print(f"  Std Dev: {np.std(yoe_values):.2f}")
    print(f"  Min YoE: {np.min(yoe_values):.2f}")
    print(f"  Max YoE: {np.max(yoe_values):.2f}")
    
    if percentage >= 70:
        print(f"\n✓ PASS: {percentage:.1f}% of top candidates are in target range")
    else:
        print(f"\n✗ WARNING: Only {percentage:.1f}% in target range (expected >70%)")
    
    return percentage >= 70


def verify_relevance(candidates: List[Dict[str, Any]], top_n: int = 50):
    """
    Acceptance Criterion 2: Top N candidates should have relevant skills.
    """
    print("\n" + "=" * 80)
    print(f"Criterion 2: Relevance Check (Top {top_n} candidates)")
    print("=" * 80)
    
    # Keywords to look for
    relevant_keywords = [
        'vector', 'embedding', 'faiss', 'pinecone', 'pytorch', 
        'nlp', 'natural language', 'machine learning', 'ml', 'ai',
        'deep learning', 'transformer', 'bert', 'retrieval',
        'information retrieval', 'search', 'semantic'
    ]
    
    top_candidates = candidates[:top_n]
    matches = 0
    
    print(f"\nSample of Top {min(10, top_n)} Candidates:")
    print("-" * 80)
    
    for idx, cand in enumerate(top_candidates[:10]):
        # Combine searchable text
        searchable_text = ' '.join([
            cand.get('headline', ''),
            cand.get('summary', ''),
            ' '.join([s.get('name', '') for s in cand.get('skills', []) if isinstance(s, dict)])
        ]).lower()
        
        # Check for keyword matches
        matched_keywords = [kw for kw in relevant_keywords if kw in searchable_text]
        has_relevant_skills = len(matched_keywords) > 0
        
        if has_relevant_skills:
            matches += 1
        
        print(f"\n{idx+1}. ID: {cand.get('id', 'N/A')}")
        print(f"   Score: {cand.get('phase2_composite_score', 0):.4f}")
        print(f"   YoE: {cand.get('years_of_experience', 0)}")
        print(f"   Headline: {cand.get('headline', 'N/A')[:80]}")
        if matched_keywords:
            print(f"   Matched Keywords: {', '.join(matched_keywords[:5])}")
        else:
            print(f"   Matched Keywords: None")
    
    # Overall statistics
    print("\n" + "-" * 80)
    relevance_percentage = (matches / len(top_candidates)) * 100
    print(f"\nCandidates with relevant keywords: {matches}/{len(top_candidates)} ({relevance_percentage:.1f}%)")
    
    if relevance_percentage >= 60:
        print(f"✓ PASS: {relevance_percentage:.1f}% have relevant experience")
    else:
        print(f"✗ WARNING: Only {relevance_percentage:.1f}% show relevant experience")
    
    return relevance_percentage >= 60


def verify_data_integrity(input_path: str, output_path: str):
    """
    Acceptance Criterion 3: No data loss, only new fields added.
    """
    print("\n" + "=" * 80)
    print("Criterion 3: Data Integrity")
    print("=" * 80)
    
    input_candidates = load_jsonl(input_path)
    output_candidates = load_jsonl(output_path)
    
    print(f"Input candidates: {len(input_candidates)}")
    print(f"Output candidates: {len(output_candidates)}")
    
    # Check count
    count_match = len(input_candidates) == len(output_candidates)
    if count_match:
        print("✓ Record count matches")
    else:
        print(f"✗ Record count mismatch!")
        return False
    
    # Check for new scoring fields
    required_fields = ['semantic_score', 'experience_score', 'location_score', 'phase2_composite_score']
    sample_output = output_candidates[0]
    
    print(f"\nNew scoring fields present:")
    all_fields_present = True
    for field in required_fields:
        present = field in sample_output
        status = "✓" if present else "✗"
        print(f"  {status} {field}")
        all_fields_present = all_fields_present and present
    
    if not all_fields_present:
        print("✗ Missing required scoring fields!")
        return False
    
    # Check that original fields are preserved (sample check)
    sample_input = input_candidates[0]
    original_fields = set(sample_input.keys())
    output_fields = set(sample_output.keys())
    
    missing_fields = original_fields - output_fields
    if missing_fields:
        print(f"\n✗ Original fields missing: {missing_fields}")
        return False
    else:
        print(f"\n✓ All original fields preserved")
    
    # Check score ranges
    print(f"\nScore Ranges:")
    all_scores_valid = True
    for field in required_fields:
        scores = [c.get(field, 0) for c in output_candidates]
        min_score = np.min(scores)
        max_score = np.max(scores)
        valid = 0 <= min_score <= 1 and 0 <= max_score <= 1
        status = "✓" if valid else "✗"
        print(f"  {status} {field}: [{min_score:.4f}, {max_score:.4f}]")
        all_scores_valid = all_scores_valid and valid
    
    if not all_scores_valid:
        print("✗ Some scores outside valid range [0.0, 1.0]!")
        return False
    
    print("\n✓ PASS: Data integrity verified")
    return True


def main():
    """Run all verification checks."""
    import os
    
    # Get the script directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Build paths relative to script location
    input_file = os.path.join(script_dir, "[PUB] India_runs_data_and_ai_challenge", 
                              "India_runs_data_and_ai_challenge", "cleaned_candidates.jsonl")
    output_file = os.path.join(script_dir, "[PUB] India_runs_data_and_ai_challenge", 
                               "India_runs_data_and_ai_challenge", "phase2_ranked_candidates.jsonl")
    
    print("Loading Phase 2 output...")
    candidates = load_jsonl(output_file)
    
    # Run verification checks
    check1 = verify_distribution_accuracy(candidates, top_n=1000)
    check2 = verify_relevance(candidates, top_n=50)
    check3 = verify_data_integrity(input_file, output_file)
    
    # Final summary
    print("\n" + "=" * 80)
    print("VERIFICATION SUMMARY")
    print("=" * 80)
    print(f"1. Distribution Accuracy: {'PASS ✓' if check1 else 'FAIL ✗'}")
    print(f"2. Relevance Check: {'PASS ✓' if check2 else 'FAIL ✗'}")
    print(f"3. Data Integrity: {'PASS ✓' if check3 else 'FAIL ✗'}")
    
    if check1 and check2 and check3:
        print("\n🎉 All acceptance criteria met!")
    else:
        print("\n⚠️  Some acceptance criteria need attention")


if __name__ == "__main__":
    main()
