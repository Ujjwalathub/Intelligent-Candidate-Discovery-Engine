"""
Phase 2: Hybrid Ranker Engine
India Runs Hackathon - Track 1 (Data & AI Challenge)

This module implements a hybrid scoring system that combines:
1. Semantic similarity using sentence transformers
2. Experience bell curve scoring
3. Geographic location scoring

Input: cleaned_candidates.jsonl (~70K-80K records)
Output: phase2_ranked_candidates.jsonl with scoring fields
"""

import json
import numpy as np
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Any
import math
from tqdm import tqdm

# ============================================================================
# Configuration Constants
# ============================================================================

# Target Job Description Query
JD_QUERY = (
    "Embeddings-based retrieval, Vector databases, FAISS, Pinecone, "
    "IR metrics evaluation, PyTorch, sentence-transformers, NLP, "
    "Machine Learning, production deployment"
)

# Scoring Weights
WEIGHT_SEMANTIC = 0.60
WEIGHT_EXPERIENCE = 0.25
WEIGHT_LOCATION = 0.15

# Experience Bell Curve Parameters
EXP_MEAN = 7.0  # Peak experience (years)
EXP_STD_DEV = 2.0  # Standard deviation

# Location Tiers
TIER1_LOCATIONS = ["Pune", "Noida", "pune", "noida"]
TIER2_LOCATIONS = ["Mumbai", "Hyderabad", "Bangalore", "Delhi NCR", "Gurgaon",
                   "mumbai", "hyderabad", "bangalore", "delhi ncr", "gurgaon"]

# Batch Processing
BATCH_SIZE = 512


# ============================================================================
# Module 2A: Semantic Retrieval Scoring
# ============================================================================

def create_candidate_document(candidate: Dict[str, Any]) -> str:
    """
    Concatenate candidate's headline, summary, skills, and current job description
    into a single document string for embedding.
    
    Args:
        candidate: Dictionary containing candidate data
        
    Returns:
        Concatenated document string
    """
    parts = []
    
    # Add headline
    if candidate.get('headline'):
        parts.append(candidate['headline'])
    
    # Add summary
    if candidate.get('summary'):
        parts.append(candidate['summary'])
    
    # Add skills (names only)
    if candidate.get('skills') and isinstance(candidate['skills'], list):
        skill_names = [skill.get('name', '') for skill in candidate['skills'] if isinstance(skill, dict)]
        if skill_names:
            parts.append(' '.join(skill_names))
    
    # Add current/most recent job description
    if candidate.get('experience') and isinstance(candidate['experience'], list) and len(candidate['experience']) > 0:
        most_recent_job = candidate['experience'][0]
        if isinstance(most_recent_job, dict) and most_recent_job.get('description'):
            parts.append(most_recent_job['description'])
    
    return ' '.join(parts)


def compute_semantic_scores(candidates: List[Dict[str, Any]], 
                            model: SentenceTransformer,
                            jd_query: str) -> np.ndarray:
    """
    Compute cosine similarity between candidate documents and JD query.
    
    Args:
        candidates: List of candidate dictionaries
        model: Loaded SentenceTransformer model
        jd_query: Target job description query string
        
    Returns:
        NumPy array of semantic scores (0.0 to 1.0)
    """
    print("Creating candidate documents...")
    candidate_docs = [create_candidate_document(cand) for cand in candidates]
    
    print("Encoding JD query...")
    jd_embedding = model.encode(jd_query, convert_to_tensor=False, show_progress_bar=False)
    
    print(f"Encoding {len(candidate_docs)} candidate documents in batches...")
    candidate_embeddings = model.encode(
        candidate_docs, 
        batch_size=BATCH_SIZE,
        convert_to_tensor=False,
        show_progress_bar=True
    )
    
    print("Computing cosine similarities...")
    # Normalize embeddings for cosine similarity
    jd_embedding_norm = jd_embedding / np.linalg.norm(jd_embedding)
    candidate_embeddings_norm = candidate_embeddings / np.linalg.norm(
        candidate_embeddings, axis=1, keepdims=True
    )
    
    # Compute cosine similarity
    similarities = np.dot(candidate_embeddings_norm, jd_embedding_norm)
    
    # Normalize to 0.0-1.0 range (cosine similarity is already in [-1, 1])
    # Map from [-1, 1] to [0, 1]
    normalized_scores = (similarities + 1) / 2
    
    return normalized_scores


# ============================================================================
# Module 2B: Experience Bell Curve Scoring
# ============================================================================

def compute_experience_score(years_of_experience: float, 
                             mu: float = EXP_MEAN, 
                             sigma: float = EXP_STD_DEV) -> float:
    """
    Apply Gaussian bell curve function to years of experience.
    
    Formula: S_exp = e^(-(x-μ)²/(2σ²))
    
    Args:
        years_of_experience: Candidate's years of experience
        mu: Mean/peak value (default: 7.0)
        sigma: Standard deviation (default: 2.0)
        
    Returns:
        Experience score (0.0 to 1.0)
    """
    if years_of_experience is None or not isinstance(years_of_experience, (int, float)):
        return 0.0
    
    exponent = -((years_of_experience - mu) ** 2) / (2 * sigma ** 2)
    score = math.exp(exponent)
    
    return score


# ============================================================================
# Module 2C: Location & Geography Scoring
# ============================================================================

def compute_location_score(candidate: Dict[str, Any]) -> float:
    """
    Score candidate based on location and relocation willingness.
    
    Tier 1 (1.0): Pune/Noida OR (India + willing to relocate)
    Tier 2 (0.8): Major tech hubs + not willing to relocate
    Tier 3 (0.5): Other India locations
    Tier 4 (0.1): Outside India
    
    Args:
        candidate: Dictionary containing candidate data
        
    Returns:
        Location score (0.1 to 1.0)
    """
    location = candidate.get('location', '').strip()
    country = candidate.get('country', '').strip()
    willing_to_relocate = candidate.get('willing_to_relocate', False)
    
    # Tier 1: Pune/Noida OR (India + willing to relocate)
    if location in TIER1_LOCATIONS:
        return 1.0
    if country.lower() == 'india' and willing_to_relocate:
        return 1.0
    
    # Tier 2: Major tech hubs but not willing to relocate
    if location in TIER2_LOCATIONS and not willing_to_relocate:
        return 0.8
    
    # Tier 3: Other India locations
    if country.lower() == 'india':
        return 0.5
    
    # Tier 4: Outside India
    return 0.1


# ============================================================================
# Module 2D: Composite Score Calculation
# ============================================================================

def compute_composite_score(semantic_score: float,
                            experience_score: float,
                            location_score: float) -> float:
    """
    Combine three sub-scores using weighted coefficients.
    
    Formula: (0.60 × S_sem) + (0.25 × S_exp) + (0.15 × S_loc)
    
    Args:
        semantic_score: Semantic similarity score
        experience_score: Experience bell curve score
        location_score: Location tier score
        
    Returns:
        Composite score (0.0 to 1.0)
    """
    composite = (
        WEIGHT_SEMANTIC * semantic_score +
        WEIGHT_EXPERIENCE * experience_score +
        WEIGHT_LOCATION * location_score
    )
    return composite


# ============================================================================
# Main Processing Pipeline
# ============================================================================

def load_candidates(input_path: str) -> List[Dict[str, Any]]:
    """Load candidates from JSONL file."""
    print(f"Loading candidates from {input_path}...")
    candidates = []
    with open(input_path, 'r', encoding='utf-8') as f:
        for line in f:
            candidates.append(json.loads(line))
    print(f"Loaded {len(candidates)} candidates.")
    return candidates


def save_ranked_candidates(candidates: List[Dict[str, Any]], output_path: str):
    """Save ranked candidates to JSONL file."""
    print(f"Saving ranked candidates to {output_path}...")
    with open(output_path, 'w', encoding='utf-8') as f:
        for candidate in candidates:
            f.write(json.dumps(candidate) + '\n')
    print(f"Saved {len(candidates)} candidates.")


def process_candidates(input_path: str, output_path: str):
    """
    Main processing function for Phase 2 Hybrid Ranker.
    
    Args:
        input_path: Path to cleaned_candidates.jsonl
        output_path: Path to save phase2_ranked_candidates.jsonl
    """
    print("=" * 80)
    print("Phase 2: Hybrid Ranker Engine")
    print("=" * 80)
    
    # Load candidates
    candidates = load_candidates(input_path)
    
    # Load sentence transformer model
    print("\nLoading sentence-transformers model (all-MiniLM-L6-v2)...")
    model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
    print("Model loaded successfully.")
    
    # Module 2A: Compute semantic scores
    print("\n" + "=" * 80)
    print("Module 2A: Computing Semantic Scores")
    print("=" * 80)
    semantic_scores = compute_semantic_scores(candidates, model, JD_QUERY)
    
    # Module 2B & 2C & 2D: Compute other scores and composite
    print("\n" + "=" * 80)
    print("Module 2B, 2C, 2D: Computing Experience, Location, and Composite Scores")
    print("=" * 80)
    
    for idx, candidate in enumerate(tqdm(candidates, desc="Scoring candidates")):
        # Semantic score (already computed)
        candidate['semantic_score'] = float(semantic_scores[idx])
        
        # Experience score
        yoe = candidate.get('years_of_experience', 0)
        candidate['experience_score'] = compute_experience_score(yoe)
        
        # Location score
        candidate['location_score'] = compute_location_score(candidate)
        
        # Composite score
        candidate['phase2_composite_score'] = compute_composite_score(
            candidate['semantic_score'],
            candidate['experience_score'],
            candidate['location_score']
        )
    
    # Sort by composite score (descending)
    print("\nSorting candidates by composite score...")
    candidates.sort(key=lambda x: x['phase2_composite_score'], reverse=True)
    
    # Save results
    save_ranked_candidates(candidates, output_path)
    
    # Display summary statistics
    print("\n" + "=" * 80)
    print("Summary Statistics")
    print("=" * 80)
    print(f"Total candidates processed: {len(candidates)}")
    print(f"\nTop 10 Composite Scores:")
    for i in range(min(10, len(candidates))):
        cand = candidates[i]
        print(f"  {i+1}. ID: {cand.get('id', 'N/A')}, "
              f"Score: {cand['phase2_composite_score']:.4f} "
              f"(Sem: {cand['semantic_score']:.4f}, "
              f"Exp: {cand['experience_score']:.4f}, "
              f"Loc: {cand['location_score']:.2f})")
    
    print(f"\nScore Distribution:")
    scores = [c['phase2_composite_score'] for c in candidates]
    print(f"  Mean: {np.mean(scores):.4f}")
    print(f"  Median: {np.median(scores):.4f}")
    print(f"  Std Dev: {np.std(scores):.4f}")
    print(f"  Min: {np.min(scores):.4f}")
    print(f"  Max: {np.max(scores):.4f}")
    
    print("\n" + "=" * 80)
    print("Phase 2 Complete!")
    print("=" * 80)


# ============================================================================
# Entry Point
# ============================================================================

if __name__ == "__main__":
    import os
    
    # Get the script directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Build paths relative to script location
    INPUT_FILE = os.path.join(script_dir, "[PUB] India_runs_data_and_ai_challenge", 
                              "India_runs_data_and_ai_challenge", "cleaned_candidates.jsonl")
    OUTPUT_FILE = os.path.join(script_dir, "[PUB] India_runs_data_and_ai_challenge", 
                               "India_runs_data_and_ai_challenge", "phase2_ranked_candidates.jsonl")
    
    process_candidates(INPUT_FILE, OUTPUT_FILE)
