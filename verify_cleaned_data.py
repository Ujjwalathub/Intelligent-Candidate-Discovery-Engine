"""
Verify Cleaned Dataset Quality
"""

import json
import os
from collections import Counter

# File paths
script_dir = os.path.dirname(os.path.abspath(__file__))
data_dir = os.path.join(script_dir, "[PUB] India_runs_data_and_ai_challenge", "India_runs_data_and_ai_challenge")
CLEANED_FILE = os.path.join(data_dir, "cleaned_candidates.jsonl")

print("=" * 70)
print("CLEANED DATASET VERIFICATION")
print("=" * 70)
print()

# Analyze cleaned dataset
candidates = []
with open(CLEANED_FILE, 'r', encoding='utf-8') as f:
    for line in f:
        candidates.append(json.loads(line.strip()))

print(f"Total valid candidates: {len(candidates):,}")
print()

# Check title distribution
print("TOP 20 CURRENT TITLES (Should be technical):")
print("-" * 70)
titles = [c.get('profile', {}).get('current_title', '') for c in candidates]
title_counts = Counter(titles)
for title, count in title_counts.most_common(20):
    print(f"{title:45s}: {count:4,}")

# Check company distribution
print()
print("\nTOP 20 CURRENT COMPANIES:")
print("-" * 70)
companies = [c.get('profile', {}).get('current_company', '') for c in candidates]
company_counts = Counter(companies)
for company, count in company_counts.most_common(20):
    print(f"{company:45s}: {count:4,}")

# Check if any service-only candidates slipped through
print()
print("\nSERVICE GIANT REPRESENTATION (should be mixed with other companies):")
print("-" * 70)
service_giants = ["Infosys", "Wipro", "TCS", "Accenture", "Cognizant", "Capgemini"]
for giant in service_giants:
    # Count candidates who have this giant in their career history
    count = sum(1 for c in candidates 
                if any(giant.lower() in job.get('company', '').lower() 
                      for job in c.get('career_history', [])))
    print(f"Candidates with {giant:15s} in career history: {count:4,}")

# Sample valid candidates
print()
print("\nSAMPLE VALID CANDIDATES:")
print("-" * 70)
for i in range(min(3, len(candidates))):
    c = candidates[i]
    profile = c.get('profile', {})
    print(f"\nCandidate {i+1}: {c.get('candidate_id')} - {profile.get('anonymized_name')}")
    print(f"  Title: {profile.get('current_title')}")
    print(f"  Company: {profile.get('current_company')}")
    print(f"  Experience: {profile.get('years_of_experience')} years")
    print(f"  Industry: {profile.get('current_industry')}")
    
    # Show career history companies
    companies = [job.get('company') for job in c.get('career_history', [])]
    print(f"  Career history: {', '.join(companies)}")
    
    # Show some skills
    skills = [s.get('name') for s in c.get('skills', [])[:5]]
    print(f"  Top skills: {', '.join(skills)}")

print()
print("=" * 70)
print("VERIFICATION COMPLETE")
print("=" * 70)
