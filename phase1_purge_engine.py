"""
Phase 1 Data Purge Engine
India Runs Hackathon - Track 1 (Data & AI Challenge)

This script filters 100,000 synthetic candidate profiles to remove:
- Honeypots (inconsistent data)
- Keyword stuffers (irrelevant domains)
- Service-company-only candidates
- API wrapper specialists without foundational skills
- Academic-only candidates

Outputs:
- cleaned_candidates.jsonl: Valid candidates only
- purge_log.csv: Log of rejected candidates with reasons
"""

import json
import csv
import re
from typing import Dict, List, Optional, Tuple

# ============================================================================
# FILTER CONFIGURATION
# ============================================================================

# Filter 2: Non-technical title blocklist
NON_TECHNICAL_TITLES = [
    "hr manager",
    "accountant",
    "business analyst",
    "mechanical engineer",
    "marketing manager",
    "customer support",
    "operations manager",
    "content writer",
    "graphic designer",
    "sales",
]

# Filter 3: Service company giants
SERVICE_GIANTS = [
    "infosys",
    "wipro",
    "tcs",
    "accenture",
    "cognizant",
    "capgemini",
]

# Filter 4: LLM wrapper skills vs foundational skills
WRAPPER_SKILLS = [
    "langchain",
    "openai",
]

FOUNDATIONAL_SKILLS = [
    "pytorch",
    "tensorflow",
    "sentence-transformers",
    "nlp",
    "machine learning",
    "vector database",
    "faiss",
    "pinecone",
    "transformers",
    "scikit-learn",
    "keras",
]

# Filter 5: Academic keywords
ACADEMIC_KEYWORDS = [
    "research assistant",
    "lab",
    "university",
    "academic",
    "phd student",
    "postdoc",
]

PRODUCTION_KEYWORDS = [
    "production",
    "deployment",
    "prod",
]

# ============================================================================
# FILTER FUNCTIONS
# ============================================================================

def filter_honeypot_consistency(candidate: Dict) -> Optional[str]:
    """
    Filter 1: The Honeypot / Consistency Filter
    
    Rule 1A: Expert skills with 0 duration
    Rule 1B: Career history duration exceeds stated experience
    
    Returns: Failure reason string if candidate fails, None if passes
    """
    # Rule 1A: Check for expert skills with 0 duration
    skills = candidate.get("skills", [])
    for skill in skills:
        proficiency = skill.get("proficiency", "").lower()
        duration_months = skill.get("duration_months", 0)
        
        if proficiency == "expert" and duration_months == 0:
            return f"Filter 1A: Expert skill '{skill.get('name')}' with 0 duration"
    
    # Rule 1B: Temporal consistency check
    career_history = candidate.get("career_history", [])
    total_career_months = sum(job.get("duration_months", 0) for job in career_history)
    total_career_years = total_career_months / 12.0
    
    stated_experience = candidate.get("profile", {}).get("years_of_experience", 0)
    allowed_experience = stated_experience + 2  # 2 years leeway
    
    if total_career_years > allowed_experience:
        return f"Filter 1B: Career history ({total_career_years:.1f} years) exceeds stated experience ({stated_experience} + 2 years leeway)"
    
    return None


def filter_keyword_stuffer(candidate: Dict) -> Optional[str]:
    """
    Filter 2: The Keyword Stuffer / Irrelevant Domain Filter
    
    Rule 2A: Check if current_title contains non-technical blocklisted terms
    
    Returns: Failure reason string if candidate fails, None if passes
    """
    current_title = candidate.get("profile", {}).get("current_title", "").lower()
    
    for blocked_title in NON_TECHNICAL_TITLES:
        if blocked_title in current_title:
            return f"Filter 2A: Non-technical title detected: '{candidate.get('profile', {}).get('current_title')}'"
    
    return None


def filter_service_company_only(candidate: Dict) -> Optional[str]:
    """
    Filter 3: The Service-Company-Only Filter
    
    Rule 3A: All companies in career history are service giants
    
    Returns: Failure reason string if candidate fails, None if passes
    """
    career_history = candidate.get("career_history", [])
    
    # If no career history, don't filter here (will be caught by Filter 5 if academic)
    if len(career_history) == 0:
        return None
    
    # Check if ALL companies are service giants
    all_service_giants = True
    for job in career_history:
        company = job.get("company", "").lower()
        if not any(giant in company for giant in SERVICE_GIANTS):
            all_service_giants = False
            break
    
    if all_service_giants:
        companies = [job.get("company") for job in career_history]
        return f"Filter 3A: All companies are service giants: {', '.join(companies)}"
    
    return None


def filter_api_wrapper(candidate: Dict) -> Optional[str]:
    """
    Filter 4: The API Wrapper Filter (Shallow Experience)
    
    Rule 4A: Has LLM wrapper skills but no foundational NLP/IR skills
    
    Returns: Failure reason string if candidate fails, None if passes
    """
    skills = candidate.get("skills", [])
    summary = candidate.get("profile", {}).get("summary", "").lower()
    
    # Get all skill names (lowercase)
    skill_names = [skill.get("name", "").lower() for skill in skills]
    
    # Check for wrapper skills in skills array or summary
    has_wrapper = False
    for wrapper in WRAPPER_SKILLS:
        if wrapper in skill_names or wrapper in summary:
            has_wrapper = True
            break
    
    # If no wrapper skills, pass this filter
    if not has_wrapper:
        return None
    
    # Check for foundational skills
    foundational_count = 0
    for foundational in FOUNDATIONAL_SKILLS:
        if foundational in skill_names or foundational in summary:
            foundational_count += 1
    
    # If has wrapper skills but no foundational skills, DROP
    if foundational_count == 0:
        return "Filter 4A: Has LLM wrapper skills (LangChain/OpenAI) but no foundational NLP/ML skills"
    
    return None


def filter_academic_only(candidate: Dict) -> Optional[str]:
    """
    Filter 5: The Academic-Only Filter
    
    Rule 5A: Career history is empty OR all roles are academic AND no production mentions
    
    Returns: Failure reason string if candidate fails, None if passes
    """
    career_history = candidate.get("career_history", [])
    
    # If career history is empty, DROP
    if len(career_history) == 0:
        return "Filter 5A: No career history"
    
    # Check if all roles are academic
    all_academic = True
    career_text = ""
    
    for job in career_history:
        title = job.get("title", "").lower()
        company = job.get("company", "").lower()
        description = job.get("description", "").lower()
        career_text += f" {title} {company} {description}"
        
        # Check if this job is NOT academic
        is_academic = False
        for academic_keyword in ACADEMIC_KEYWORDS:
            if academic_keyword in title or academic_keyword in company or academic_keyword in description:
                is_academic = True
                break
        
        if not is_academic:
            all_academic = False
            break
    
    # If not all academic, pass this filter
    if not all_academic:
        return None
    
    # All roles are academic - check for production/deployment mentions
    has_production = False
    for prod_keyword in PRODUCTION_KEYWORDS:
        if prod_keyword in career_text:
            has_production = True
            break
    
    # If all academic and no production mentions, DROP
    if not has_production:
        return "Filter 5A: All roles are academic with no production/deployment experience"
    
    return None


# ============================================================================
# MAIN PURGE ENGINE
# ============================================================================

def process_candidate(candidate: Dict) -> Tuple[bool, Optional[str]]:
    """
    Process a single candidate through all filters.
    
    Returns: (is_valid, failure_reason)
        - is_valid: True if candidate passes all filters
        - failure_reason: String explaining why candidate was dropped (None if valid)
    """
    # Run filters in sequence
    filters = [
        filter_honeypot_consistency,
        filter_keyword_stuffer,
        filter_service_company_only,
        filter_api_wrapper,
        filter_academic_only,
    ]
    
    for filter_func in filters:
        failure_reason = filter_func(candidate)
        if failure_reason:
            return False, failure_reason
    
    return True, None


def run_purge_engine(input_file: str, output_file: str, log_file: str):
    """
    Main purge engine that processes all candidates.
    
    Args:
        input_file: Path to candidates.jsonl
        output_file: Path to cleaned_candidates.jsonl
        log_file: Path to purge_log.csv
    """
    print(f"Starting Phase 1 Data Purge Engine...")
    print(f"Input: {input_file}")
    print(f"Output: {output_file}")
    print(f"Log: {log_file}")
    print()
    
    valid_count = 0
    rejected_count = 0
    
    # Open output files
    with open(input_file, 'r', encoding='utf-8') as infile, \
         open(output_file, 'w', encoding='utf-8') as outfile, \
         open(log_file, 'w', newline='', encoding='utf-8') as logfile:
        
        # Setup CSV writer for log
        log_writer = csv.writer(logfile)
        log_writer.writerow(['candidate_id', 'anonymized_name', 'failure_reason'])
        
        # Process candidates line by line (streaming for memory efficiency)
        line_num = 0
        for line in infile:
            line_num += 1
            
            # Progress indicator every 10,000 records
            if line_num % 10000 == 0:
                print(f"Processed {line_num:,} candidates... (Valid: {valid_count:,}, Rejected: {rejected_count:,})")
            
            try:
                candidate = json.loads(line.strip())
            except json.JSONDecodeError as e:
                print(f"Warning: Failed to parse line {line_num}: {e}")
                continue
            
            # Process candidate through filters
            is_valid, failure_reason = process_candidate(candidate)
            
            if is_valid:
                # Write to cleaned output
                outfile.write(json.dumps(candidate, ensure_ascii=False) + '\n')
                valid_count += 1
            else:
                # Log rejection
                candidate_id = candidate.get('candidate_id', 'UNKNOWN')
                anonymized_name = candidate.get('profile', {}).get('anonymized_name', 'UNKNOWN')
                log_writer.writerow([candidate_id, anonymized_name, failure_reason])
                rejected_count += 1
    
    # Final statistics
    total_count = valid_count + rejected_count
    rejection_rate = (rejected_count / total_count * 100) if total_count > 0 else 0
    
    print()
    print("=" * 70)
    print("PURGE ENGINE COMPLETE")
    print("=" * 70)
    print(f"Total candidates processed:  {total_count:,}")
    print(f"Valid candidates:            {valid_count:,} ({valid_count/total_count*100:.1f}%)")
    print(f"Rejected candidates:         {rejected_count:,} ({rejection_rate:.1f}%)")
    print()
    print(f"Output file: {output_file}")
    print(f"Log file: {log_file}")
    print("=" * 70)


# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    import time
    import os
    
    # Get the directory where the script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(script_dir, "[PUB] India_runs_data_and_ai_challenge", "India_runs_data_and_ai_challenge")
    
    # File paths
    INPUT_FILE = os.path.join(data_dir, "candidates.jsonl")
    OUTPUT_FILE = os.path.join(data_dir, "cleaned_candidates.jsonl")
    LOG_FILE = os.path.join(data_dir, "purge_log.csv")
    
    # Run the purge engine
    start_time = time.time()
    run_purge_engine(INPUT_FILE, OUTPUT_FILE, LOG_FILE)
    elapsed_time = time.time() - start_time
    
    print(f"\nExecution time: {elapsed_time:.2f} seconds")
