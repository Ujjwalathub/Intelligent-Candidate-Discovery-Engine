🏗️ Architecture: The 3-Phase Pipeline

This engine processes data in three distinct, sequential phases:

Phase 1: The Purge (Trap Evasion & Data Cleaning)

Before any AI modeling occurs, the system aggressively filters the raw candidates.jsonl dataset to avoid automatic disqualification.

Honeypot Detection: Drops physically impossible profiles (e.g., claiming "expert" skills with 0 months duration, or job history length exceeding stated years of experience).

Service-Company Trap: Filters out candidates whose entire career history consists exclusively of major IT service firms, adhering strictly to the Job Description (JD).

Wrapper Trap: Eliminates candidates whose only AI experience is API wrappers (LangChain/OpenAI) without underlying fundamentals (PyTorch/NLP).

Phase 2: The Hybrid Ranker (Semantic + Heuristic Scoring)

The surviving clean pool is scored against the JD ("Senior AI Engineer — Founding Team") using a weighted hybrid model:

Semantic Vector Search (60%): Uses all-MiniLM-L6-v2 to embed candidate summaries, headlines, and job histories into vectors, computing cosine similarity against the JD.

Experience Bell Curve (25%): Applies a Gaussian (bell curve) function peaking at 7 years of experience. Heavily rewards the 5–9 year sweet spot while decaying candidates with too much or too little experience.

Location Tiering (15%): Rewards candidates in Tier-1 locations (Pune/Noida) or those willing to relocate within India, penalizing non-Indian residents due to visa constraints.

Phase 3: The Behavioral Multiplier & LLM Reasoning

Transforms the mathematically ranked list into a list of hirable humans.

Signal Multiplier: Modifies the Phase 2 composite score based on Redrob engagement signals (boosts for open_to_work, penalties for >90-day notice_period or stale profiles).

LLM Justification: Extracts the Top 100 candidates and calls the Gemini 1.5 Flash API to generate a punchy, 2-sentence justification explaining exactly why the candidate fits the role.

⚙️ Installation & Setup

Prerequisites

Python 3.9+

A valid Gemini API Key (for Phase 3 LLM reasoning)

1. Clone the repository

git clone [https://github.com/yourusername/india-runs-candidate-discovery.git](https://github.com/yourusername/india-runs-candidate-discovery.git)
cd india-runs-candidate-discovery


2. Create a virtual environment and install dependencies

python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate
pip install pandas numpy sentence-transformers tqdm google-genai


3. Add your API Key

Export your Gemini API key as an environment variable before running Phase 3:

# On Linux/macOS
export GEMINI_API_KEY="your_api_key_here"

# On Windows (Command Prompt)
set GEMINI_API_KEY=your_api_key_here

# On Windows (PowerShell)
$env:GEMINI_API_KEY="your_api_key_here"


🚀 Usage

Place the original candidates.jsonl provided by the hackathon in the root data directory, then run the pipeline sequentially:

Run Phase 1 (Filtering):

python phase1_purge.py


Output: cleaned_candidates.jsonl

Run Phase 2 (Ranking):

python phase2_hybrid_ranker.py


Output: phase2_ranked_candidates.jsonl

Run Phase 3 (Behavioral Scoring & Submission Generation):

python phase3_behavioral_multiplier.py




📁 Repository Structure

├── [PUB] India_runs_data_and_ai_challenge/  # Data directory
│   ├── candidates.jsonl                     # Raw Hackathon Data (Not included in repo)
│   ├── cleaned_candidates.jsonl             # Output of Phase 1
│   └── phase2_ranked_candidates.jsonl       # Output of Phase 2
├── phase1_purge.py                          # Rule-based hard filtering script
├── phase2_hybrid_ranker.py                  # Embedding & mathematical scoring script
├── phase3_behavioral_multiplier.py          # Engagement multiplier & Gemini API script
├── submission_metadata.yaml                 # Required Hackathon Metadata
├── final_submission.csv                     # The final 100-row output
└── README.md                                # You are here


🏆 Acknowledgments

Built for the India Runs Hackathon organized by Redrob AI & Hack2skill.
