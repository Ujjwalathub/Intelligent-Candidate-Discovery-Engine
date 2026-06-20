"""
Phase 3: Behavioral Multiplier & Submission Engine
India Runs Hackathon - Track 1 (Data & AI Challenge)

This module calculates behavioral multipliers based on platform engagement signals,
applies them to Phase 2 scores, selects the Top 100 candidates, and generates
LLM-powered justifications for the final submission.
"""

import json
import csv
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
import os

# Try to import the new google.genai package, fall back to the old one if not available
try:
    from google import genai
    USE_NEW_API = True
except ImportError:
    try:
        import google.generativeai as genai
        USE_NEW_API = False
    except ImportError:
        print("Warning: Neither google.genai nor google.generativeai packages found.")
        print("Install with: pip install google-genai")
        genai = None
        USE_NEW_API = False

# Configuration
# Determine the base directory
BASE_DIR = Path(__file__).parent
INPUT_FILE = BASE_DIR / "[PUB] India_runs_data_and_ai_challenge" / "India_runs_data_and_ai_challenge" / "phase2_ranked_candidates.jsonl"
OUTPUT_FILE = BASE_DIR / "final_submission.csv"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")  # Set your API key as environment variable

# Configure Gemini
model = None
if genai and GEMINI_API_KEY:
    try:
        if USE_NEW_API:
            client = genai.Client(api_key=GEMINI_API_KEY)
            model = "gemini-1.5-flash"
        else:
            genai.configure(api_key=GEMINI_API_KEY)
            model = genai.GenerativeModel('gemini-1.5-flash')
    except Exception as e:
        print(f"Warning: Failed to configure Gemini API: {e}")
        model = None
else:
    if not GEMINI_API_KEY:
        print("Warning: GEMINI_API_KEY not set. LLM reasoning will be skipped.")
    if not genai:
        print("Warning: Gemini API library not available. LLM reasoning will be skipped.")


def calculate_months_inactive(last_active_date: str, reference_date: str = "2026-06-20") -> int:
    """Calculate the number of months since last activity."""
    try:
        last_active = datetime.strptime(last_active_date, "%Y-%m-%d")
        reference = datetime.strptime(reference_date, "%Y-%m-%d")
        months = (reference.year - last_active.year) * 12 + (reference.month - last_active.month)
        return max(0, months)
    except:
        return 0


def calculate_behavioral_multiplier(redrob_signals: Dict[str, Any]) -> float:
    """
    Calculate the behavioral multiplier (M_beh) based on platform engagement signals.
    
    Rules:
    1. Start with base multiplier of 1.00
    2. Rule 1 (Active Status): IF open_to_work_flag == True, Add +0.15
    3. Rule 2 (Responsiveness): Add (recruiter_response_rate * 0.10)
    4. Rule 3 (Notice Period Penalty):
       - <= 30 days: No penalty (0.0)
       - > 60 AND <= 90: Subtract -0.20
       - > 90: Subtract -0.50
    5. Rule 4 (Stale Profile Penalty): 
       - IF months_inactive > 3, subtract -0.10 for each additional month (capped at -0.40)
    6. Boundary Guard: Ensure M_beh is between 0.10 and 1.50
    """
    multiplier = 1.00
    
    # Rule 1: Active Status
    if redrob_signals.get("open_to_work_flag", False):
        multiplier += 0.15
    
    # Rule 2: Responsiveness
    response_rate = redrob_signals.get("recruiter_response_rate", 0.0)
    multiplier += response_rate * 0.10
    
    # Rule 3: Notice Period Penalty
    notice_period = redrob_signals.get("notice_period_days", 0)
    if notice_period <= 30:
        pass  # No penalty
    elif 60 < notice_period <= 90:
        multiplier -= 0.20
    elif notice_period > 90:
        multiplier -= 0.50
    
    # Rule 4: Stale Profile Penalty
    last_active = redrob_signals.get("last_active_date", "2026-06-20")
    months_inactive = calculate_months_inactive(last_active)
    if months_inactive > 3:
        additional_months = months_inactive - 3
        penalty = min(additional_months * 0.10, 0.40)
        multiplier -= penalty
    
    # Boundary Guard
    multiplier = max(0.10, min(1.50, multiplier))
    
    return multiplier


def load_candidates(file_path: str) -> List[Dict[str, Any]]:
    """Load candidates from JSONL file."""
    candidates = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                candidates.append(json.loads(line))
    return candidates


def calculate_grand_scores(candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Calculate grand_score for all candidates using the behavioral multiplier."""
    for candidate in candidates:
        phase2_score = candidate.get("phase2_composite_score", 0.0)
        redrob_signals = candidate.get("redrob_signals", {})
        
        # Calculate behavioral multiplier
        behavioral_multiplier = calculate_behavioral_multiplier(redrob_signals)
        
        # Calculate grand score
        grand_score = phase2_score * behavioral_multiplier
        
        # Add to candidate record
        candidate["behavioral_multiplier"] = behavioral_multiplier
        candidate["grand_score"] = grand_score
    
    return candidates


def sort_and_select_top_100(candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Sort candidates by grand_score (descending) and select top 100."""
    # Sort by grand_score (descending), then by candidate_id (alphabetically ascending) for deterministic tie-breaking
    sorted_candidates = sorted(
        candidates,
        key=lambda x: (-x["grand_score"], x["candidate_id"])  # Negative score for descending, candidate_id for ascending
    )
    
    # Select top 100
    top_100 = sorted_candidates[:100]
    
    # Assign ranks
    for i, candidate in enumerate(top_100, start=1):
        candidate["rank"] = i
    
    return top_100


def generate_llm_reasoning(candidate: Dict[str, Any], retry_count: int = 3) -> str:
    """
    Generate LLM-powered reasoning for a candidate.
    Implements exponential backoff for rate limiting.
    """
    if not model:
        # Fallback reasoning if API key not set
        profile = candidate.get("profile", {})
        return f"{profile.get('current_title', 'Candidate')} with {profile.get('years_of_experience', 0):.1f} years of experience in AI/ML."
    
    # Extract candidate information
    profile = candidate.get("profile", {})
    skills = candidate.get("skills", [])
    career_history = candidate.get("career_history", [])
    
    # Get top AI-relevant skills
    ai_keywords = ["PyTorch", "Vector", "Embeddings", "LLM", "RAG", "FAISS", "Pinecone", 
                   "Weaviate", "NLP", "Machine Learning", "AI", "Deep Learning", 
                   "Sentence Transformers", "Information Retrieval", "LangChain"]
    
    top_skills = []
    for skill in skills:
        skill_name = skill.get("name", "")
        if any(keyword.lower() in skill_name.lower() for keyword in ai_keywords):
            top_skills.append(skill_name)
    
    # Get current/recent role
    current_role = profile.get("current_title", "Professional")
    years_exp = profile.get("years_of_experience", 0)
    
    # Build top career role
    top_career_role = ""
    if career_history and len(career_history) > 0:
        top_career_role = career_history[0].get("title", "")
    
    # Create profile summary
    skills_summary = ", ".join(top_skills[:5]) if top_skills else "AI/ML skills"
    profile_summary = f"Title: {current_role}, Years of Experience: {years_exp:.1f}, Key Skills: {skills_summary}, Recent Role: {top_career_role}"
    
    # Create prompt
    prompt = f"""You are an expert technical recruiter. Based on this candidate profile: {profile_summary}, write a concise, punchy 2-sentence justification for why this candidate is a top match for a Senior AI Engineer role focused on Vector Databases and PyTorch. Do not hallucinate skills they do not have. Output ONLY the reasoning text."""
    
    # Try with exponential backoff
    for attempt in range(retry_count):
        try:
            if USE_NEW_API:
                # New API
                response = client.models.generate_content(
                    model=model,
                    contents=prompt
                )
                reasoning = response.text.strip()
            else:
                # Old API
                response = model.generate_content(prompt)
                reasoning = response.text.strip()
            return reasoning
        except Exception as e:
            if attempt < retry_count - 1:
                wait_time = (2 ** attempt) * 1  # Exponential backoff: 1s, 2s, 4s
                print(f"API error for {candidate['candidate_id']}: {e}. Retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                print(f"Failed to generate reasoning for {candidate['candidate_id']} after {retry_count} attempts.")
                # Fallback reasoning
                return f"{current_role} with {years_exp:.1f} years of experience. Strong background in {skills_summary}."
    
    return f"{current_role} with {years_exp:.1f} years of experience."


def generate_reasoning_for_top_100(top_100: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Generate LLM reasoning for each candidate in the top 100."""
    print("Generating LLM reasoning for Top 100 candidates...")
    
    for i, candidate in enumerate(top_100, start=1):
        print(f"Processing {i}/100: {candidate['candidate_id']}")
        reasoning = generate_llm_reasoning(candidate)
        candidate["reasoning"] = reasoning
        
        # Rate limiting: sleep briefly between API calls
        if model and i < len(top_100):  # Don't sleep after the last one
            time.sleep(0.5)  # 500ms between requests
    
    print("Reasoning generation complete.")
    return top_100


def export_to_csv(top_100: List[Dict[str, Any]], output_file: str):
    """Export the top 100 candidates to CSV in the required format."""
    # Sort once more by (score descending, candidate_id ascending) to ensure proper ordering
    # This is important because float rounding might cause issues
    top_100_sorted = sorted(top_100, key=lambda x: (-x["grand_score"], x["candidate_id"]))
    
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        
        # Write header
        writer.writerow(["candidate_id", "rank", "score", "reasoning"])
        
        # Write data rows (re-assign ranks based on sorted order)
        for i, candidate in enumerate(top_100_sorted, start=1):
            writer.writerow([
                candidate["candidate_id"],
                i,  # Use the new rank based on proper sorting
                f"{candidate['grand_score']:.4f}",
                candidate.get("reasoning", "")
            ])
    
    print(f"Submission exported to {output_file}")


def validate_submission(output_file: str, top_100: List[Dict[str, Any]]):
    """Validate the submission file against acceptance criteria."""
    print("\n=== Validation Report ===")
    
    # Check 1: File exists and has correct number of rows
    with open(output_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        row_count = len(lines)
        print(f"✓ Row count: {row_count} (expected: 101 including header)")
    
    # Check 2: Score consistency (descending order)
    scores = [c["grand_score"] for c in top_100]
    is_descending = all(scores[i] >= scores[i+1] for i in range(len(scores)-1))
    print(f"✓ Score ordering: {'PASS' if is_descending else 'FAIL'} (rank 1 highest, rank 100 lowest)")
    print(f"  Rank 1 score: {scores[0]:.4f}")
    print(f"  Rank 100 score: {scores[-1]:.4f}")
    
    # Check 3: Reasoning quality (no template placeholders)
    has_placeholders = any("Insert" in c.get("reasoning", "") or "{" in c.get("reasoning", "") for c in top_100)
    print(f"✓ Reasoning quality: {'FAIL - Contains placeholders' if has_placeholders else 'PASS'}")
    
    # Check 4: No duplicate candidate IDs
    candidate_ids = [c["candidate_id"] for c in top_100]
    has_duplicates = len(candidate_ids) != len(set(candidate_ids))
    print(f"✓ Unique candidates: {'FAIL - Duplicates found' if has_duplicates else 'PASS'}")
    
    print("=== Validation Complete ===\n")


def main():
    """Main execution pipeline for Phase 3."""
    print("=" * 60)
    print("Phase 3: Behavioral Multiplier & Submission Engine")
    print("=" * 60)
    
    # Step 1: Load candidates
    print("\n[1/6] Loading Phase 2 candidates...")
    candidates = load_candidates(INPUT_FILE)
    print(f"Loaded {len(candidates)} candidates")
    
    # Step 2: Calculate grand scores
    print("\n[2/6] Calculating behavioral multipliers and grand scores...")
    candidates = calculate_grand_scores(candidates)
    print(f"Calculated grand scores for {len(candidates)} candidates")
    
    # Step 3: Sort and select Top 100
    print("\n[3/6] Sorting and selecting Top 100 candidates...")
    top_100 = sort_and_select_top_100(candidates)
    print(f"Selected Top 100 candidates")
    print(f"  Top candidate: {top_100[0]['candidate_id']} (score: {top_100[0]['grand_score']:.4f})")
    print(f"  100th candidate: {top_100[99]['candidate_id']} (score: {top_100[99]['grand_score']:.4f})")
    
    # Step 4: Generate LLM reasoning
    print("\n[4/6] Generating LLM reasoning for Top 100...")
    top_100 = generate_reasoning_for_top_100(top_100)
    
    # Step 5: Export to CSV
    print("\n[5/6] Exporting to CSV...")
    export_to_csv(top_100, OUTPUT_FILE)
    
    # Step 6: Validate
    print("\n[6/6] Validating submission...")
    validate_submission(OUTPUT_FILE, top_100)
    
    print("\n" + "=" * 60)
    print("Phase 3 Complete!")
    print(f"Final submission saved to: {OUTPUT_FILE}")
    print("=" * 60)


if __name__ == "__main__":
    main()
