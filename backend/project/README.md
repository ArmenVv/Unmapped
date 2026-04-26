# Job Suitability Agent

Analyzes your ChatGPT conversation history to assess your suitability for a given job.

## How it works

1. **Ingest** — Parses your ChatGPT export and stores all user messages in a local ChromaDB vector database.
2. **Keywords** — Uses Gemini to generate targeted keywords from your job description.
3. **Retrieve** — Finds the most relevant messages from your history using semantic search.
4. **Analyse** — Gemini evaluates your suitability and returns a structured JSON report with a score, strengths, and gaps.

## Setup

```bash
# 1. Clone and enter the project
git clone <your-repo-url>
cd <project-folder>

# 2. Create a virtual environment
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set your API key
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY
```

## Usage

Export your ChatGPT history from [chat.openai.com](https://chat.openai.com) → Settings → Data Controls → Export.
Place the `conversations.json` file in the `data/` folder.

```bash
# Interactive
python main.py

# Or pass the job directly
python main.py --job "Senior Python Backend Engineer"

# Custom data path
python main.py --job "Data Scientist" --data path/to/conversations.json
```

## Output

```json
{
  "candidate": {
    "name": "Alex",
    "surname": "Smith",
    "age": 27,
    "city": "Berlin"
  },
  "analysis": {
    "profession": "Backend Engineer",
    "suitability_score": 82,
    "description": "Strong Python background evident from multiple conversations...",
    "strengths": ["Python", "REST APIs", "PostgreSQL"],
    "gaps": ["Kubernetes", "Go"]
  }
}
```

## Project Structure

```
├── src/
│   └── agent.py          # Core agent logic
├── data/
│   └── conversations.json  # Your ChatGPT export goes here
├── main.py               # CLI entry point
├── requirements.txt
├── .env.example
└── README.md
```
