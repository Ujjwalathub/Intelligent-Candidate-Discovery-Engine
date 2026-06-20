# Phase 3: Behavioral Multiplier & Submission Engine

## Overview

Phase 3 is the final stage of the Candidate Discovery pipeline for the India Runs Hackathon. It applies behavioral multipliers based on platform engagement signals to Phase 2 scores, selects the Top 100 candidates, and generates LLM-powered justifications for the final submission.

## Objective

<cite index="1-4">Calculate a behavioral_multiplier based on platform engagement signals, apply it to the phase2_composite_score to yield a final grand_score, isolate the Top 100 candidates, and dynamically generate LLM-powered justifications for the final hackathon submission CSV.</cite>

## Key Features

### 1. Behavioral Multiplier Calculation

<cite index="1-20">The engine starts every candidate with a base multiplier of 1.00.</cite> It then applies the following rules:

#### <cite index="1-21">Rule 1 (Active Status): IF open_to_work_flag == True, Add +0.15</cite>

#### <cite index="1-22,1-23">Rule 2 (Responsiveness): Add (recruiter_response_rate * 0.10). (E.g., an 80% response rate adds 0.08).</cite>

#### Rule 3 (Notice Period Penalty - Critical):
<cite index="1-25,1-26,1-27">
- IF notice_period_days <= 30: No penalty (Add 0.0)
- IF notice_period_days > 60 AND <= 90: Subtract -0.20
- IF notice_period_days > 90: Subtract -0.50 (Massive penalty as per JD availability requirements)
</cite>

#### <cite index="1-28,1-29">Rule 4 (Stale Profile Penalty): Calculate months since last_active_date. IF months > 3, subtract -0.10 for every additional month of inactivity (capped at -0.40).</cite>

#### <cite index="1-30">Boundary Guard: Ensure M_beh never drops below 0.10 and never exceeds 1.50</cite>

### 2. Grand Score Calculation

<cite index="1-31">Formula: grand_score = phase2_composite_score × M_beh</cite>

<cite index="1-32,1-33">The dataset is sorted descending by grand_score, then truncated to retain strictly the top 100 rows.</cite>

### 3. LLM Reasoning Generation

<cite index="1-34,1-35">The hackathon spec requires a custom 1-2 sentence reasoning explaining why the candidate fits the Founding Team AI Engineer role. Hallucinated templates are penalized.</cite>

<cite index="1-36,1-37">The system iterates through the Top 100 list and constructs a prompt for each candidate containing their skills, years_of_experience, and top career_history role.</cite>

<cite index="1-38,1-39,1-40,1-41">Prompt Engineering: "You are an expert technical recruiter. Based on this candidate profile: {profile_summary}, write a concise, punchy 2-sentence justification for why this candidate is a top match for a Senior AI Engineer role focused on Vector Databases and PyTorch. Do not hallucinate skills they do not have. Output ONLY the reasoning text."</cite>

<cite index="1-42">Prompts are sent asynchronously to the LLM API, handling rate limits via exponential backoff.</cite>

### 4. Output Format

<cite index="1-43">The Top 100 records are mapped to the schema:
- candidate_id: String (e.g., "CAND_1048592")
- rank: Integer (1 to 100)
- score: Float (rounded to 4 decimal places, must be strictly non-increasing)
- reasoning: String (the LLM output)
</cite>

## Input/Output

### Input
<cite index="1-15,1-16">
- Input 1: phase2_ranked_candidates.jsonl (contains phase2_composite_score)
- Input 2: redrob_signals embedded within each candidate profile
</cite>

### Output
<cite index="1-17">final_submission.csv containing exactly 101 rows (1 header + 100 candidates) with columns: candidate_id, rank, score, reasoning</cite>

## Setup Instructions

### 1. Install Dependencies

```bash
pip install google-generativeai
```

### 2. Set API Key

Set your Gemini API key as an environment variable:

```bash
# Windows (Command Prompt)
set GEMINI_API_KEY=your_api_key_here

# Windows (PowerShell)
$env:GEMINI_API_KEY="your_api_key_here"

# Linux/Mac
export GEMINI_API_KEY=your_api_key_here
```

### 3. Run the Script

```bash
python phase3_behavioral_multiplier.py
```

## Implementation Details

### Non-Functional Requirements

<cite index="1-45">API Rate Limiting: The script implements exponential backoff and sleep functions to prevent hitting API rate limits when generating the 100 reasonings.</cite>

<cite index="1-46">Deterministic Sorting: If two candidates have the exact same grand_score, the script breaks the tie deterministically (e.g., sorting secondarily by candidate_id alphabetically) to ensure consistent outputs.</cite>

### Acceptance Criteria

<cite index="1-50">1. Submission Format: The output CSV perfectly mimics the provided sample_submission.csv and successfully passes the validate_submission.py script provided by the organizers.</cite>

<cite index="1-52">2. Score Consistency: Row 1 (rank 1) has the highest score, and Row 100 (rank 100) has the lowest score in the file.</cite>

<cite index="1-54">3. Reasoning Quality: The reasoning column contains unique, context-aware text (no repetitive boilerplate or template variables like "Insert Name Here").</cite>

## Execution Flow

```
1. Load Phase 2 candidates from JSONL file
2. Calculate behavioral multipliers for all candidates
3. Calculate grand_score = phase2_score × behavioral_multiplier
4. Sort by grand_score (descending) with deterministic tie-breaking
5. Select Top 100 candidates
6. Generate LLM reasoning for each of the Top 100
7. Export to CSV in required format
8. Validate submission against acceptance criteria
```

## Output Example

```csv
candidate_id,rank,score,reasoning
CAND_0028793,1,0.3513,Search Engineer with 7.2 years building production ML systems. Expert in embeddings, vector search (FAISS, Pinecone), and RAG implementation with proven experience shipping semantic search and NLP features.
CAND_0011162,2,0.3352,Recommendation Systems Engineer with 5.8 years specializing in ML-powered ranking and retrieval. Advanced expertise in FAISS, Vector Search, LangChain, and embeddings with hands-on experience in learning-to-rank systems.
...
```

## Validation

The script includes built-in validation that checks:
- ✓ Correct number of rows (101 including header)
- ✓ Score ordering (descending from rank 1 to 100)
- ✓ Reasoning quality (no template placeholders)
- ✓ Unique candidate IDs (no duplicates)

## Notes

- The script processes only the Top 100 through the LLM API to save time and costs
- Exponential backoff is implemented for API rate limiting (1s, 2s, 4s delays)
- 500ms delay between API requests for rate limit compliance
- Fallback reasoning is provided if the API key is not set or API calls fail
- All scores are rounded to 4 decimal places as required

## Troubleshooting

**Issue**: API rate limit errors
**Solution**: The script automatically implements exponential backoff. If issues persist, increase the base sleep time in the `generate_reasoning_for_top_100()` function.

**Issue**: Missing API key
**Solution**: Ensure the `GEMINI_API_KEY` environment variable is set before running the script.

**Issue**: File not found error
**Solution**: Verify that `phase2_ranked_candidates.jsonl` exists in the correct path: `[PUB] India_runs_data_and_ai_challenge/India_runs_data_and_ai_challenge/`
