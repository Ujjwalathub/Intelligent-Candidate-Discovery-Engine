# Phase 2: Hybrid Ranker Engine

## Overview

<cite index="1-2,1-3">The Phase 2 Hybrid Ranker Engine is the core intelligence of the Candidate Discovery pipeline. It takes the pre-filtered, safe candidate pool from Phase 1 and evaluates them against the nuanced requirements of the "Senior AI Engineer — Founding Team" job description.</cite>

<cite index="1-4">The objective is to assign a quantitative phase2_score to each candidate using a hybrid scoring model that combines dense semantic search (vector embeddings) with heuristic scoring for experience and location.</cite>

## Implementation

### Input
- `cleaned_candidates.jsonl` (~70,000 to 80,000 records from Phase 1)

### Output
- `phase2_ranked_candidates.jsonl` with added scoring fields:
  - `semantic_score` - Cosine similarity with JD query (0.0 to 1.0)
  - `experience_score` - Bell curve score for years of experience (0.0 to 1.0)
  - `location_score` - Geographic preference score (0.1 to 1.0)
  - `phase2_composite_score` - Weighted combination of all scores

## Scoring Components

### 1. Semantic Retrieval Scoring (60% weight)

<cite index="1-22">Concatenates each candidate's headline, summary, skills (names only), and the description of their current/most recent job into a single candidate_document string.</cite>

<cite index="1-24">Uses sentence-transformers/all-MiniLM-L6-v2 to embed the candidate_document and the Target JD Query String into dense vectors.</cite>

<cite index="1-25,1-26">Computes the Cosine Similarity between the candidate vector and the JD vector, then maps the cosine similarity to a 0.0 to 1.0 scale.</cite>

**Target JD Query:**
```
Embeddings-based retrieval, Vector databases, FAISS, Pinecone, 
IR metrics evaluation, PyTorch, sentence-transformers, NLP, 
Machine Learning, production deployment
```

### 2. Experience Bell Curve Scoring (25% weight)

<cite index="1-27">The JD explicitly states a preference for 5–9 years of experience, peaking at ~7 years.</cite>

<cite index="1-29,1-30">Applies a Gaussian (bell curve) function to the candidate's years_of_experience with mean (μ) = 7.0 and standard deviation (σ) = 2.0.</cite>

**Formula:**
```
S_exp = e^(-(x-μ)²/(2σ²))
```

<cite index="1-30,1-31">A candidate with 7.0 YoE gets a score of 1.0. A candidate with 2 YoE or 12 YoE gets a mathematically decayed score near 0.04.</cite>

### 3. Location & Geography Scoring (15% weight)

<cite index="1-32">The JD prefers Pune/Noida, accepts other major Indian tech hubs, and discourages candidates outside India due to visa constraints.</cite>

**Scoring Tiers:**

<cite index="1-34">- **Tier 1 (Score = 1.0):** location is in ["Pune", "Noida"] OR (country == "India" AND willing_to_relocate == True)</cite>

<cite index="1-35">- **Tier 2 (Score = 0.8):** location is in ["Mumbai", "Hyderabad", "Bangalore", "Delhi NCR", "Gurgaon"] AND willing_to_relocate == False</cite>

<cite index="1-36">- **Tier 3 (Score = 0.5):** Any other location where country == "India"</cite>

<cite index="1-37">- **Tier 4 (Score = 0.1):** country != "India" (Heavy penalty as per JD rules)</cite>

### 4. Composite Formula

<cite index="1-40">Formula: phase2_composite_score = (0.60 × S_sem) + (0.25 × S_exp) + (0.15 × S_loc)</cite>

<cite index="1-39">Semantic match is the most critical factor, followed by experience alignment, with location acting as a strong tie-breaker.</cite>

## Installation & Requirements

```bash
pip install sentence-transformers numpy tqdm
```

## Usage

### Run Phase 2 Ranker

```bash
python phase2_hybrid_ranker.py
```

This will:
1. Load `cleaned_candidates.jsonl`
2. Generate embeddings using sentence-transformers
3. Calculate semantic, experience, and location scores
4. Compute weighted composite scores
5. Sort candidates by composite score
6. Save to `phase2_ranked_candidates.jsonl`

### Verify Output

```bash
python verify_phase2_output.py
```

This validates the three acceptance criteria:
1. **Distribution Accuracy:** Top 1000 candidates fall within 5-9 YoE range
2. **Relevance:** Top 50 candidates show strong Vector DB/PyTorch/NLP experience
3. **Data Integrity:** No data loss, only new scoring fields added

## Performance Optimization

<cite index="1-41">To process ~80,000 records within Hackathon time limits on standard hardware, the embedding generation processes candidates in batches (batch size 256 or 512).</cite>

<cite index="1-42">Uses NumPy matrices or FAISS for the cosine similarity calculation to ensure it executes in milliseconds rather than looping in pure Python.</cite>

## Acceptance Criteria

<cite index="1-46">**1. Distribution Accuracy:** The top 1000 candidates outputted by this phase must uniformly fall within the 5-9 YoE range (validating the bell curve).</cite>

<cite index="1-48">**2. Relevance:** Manual inspection of the top 50 candidates should reveal strong experience in Vector DBs, PyTorch, and NLP over generic web development or basic ChatGPT wrapper skills.</cite>

<cite index="1-50">**3. Data Integrity:** No candidate data is lost or structurally altered between the input JSONL and output JSONL; only the new scoring fields are appended.</cite>

## Output Format

Each candidate record will contain all original fields plus:

```json
{
  "id": "...",
  "headline": "...",
  "summary": "...",
  "skills": [...],
  "experience": [...],
  "years_of_experience": 7.5,
  "location": "Pune",
  "country": "India",
  "willing_to_relocate": true,
  
  // New Phase 2 fields
  "semantic_score": 0.8234,
  "experience_score": 0.9692,
  "location_score": 1.0,
  "phase2_composite_score": 0.8646
}
```

## Next Steps

Phase 2 output feeds into **Phase 3** which applies behavioral/activity multipliers and generates the final top 100 candidates with LLM reasoning.

## Notes

- The semantic model (`all-MiniLM-L6-v2`) is lightweight and CPU-efficient for hackathon constraints
- Batch processing ensures scalability to 80K+ records
- All scores are normalized to [0.0, 1.0] range for consistent weighting
- Candidates are sorted in descending order by composite score
