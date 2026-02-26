# AI Job Application Agent

A privacy-first, AI-powered job application assistant built on **Claude** (Anthropic).
The agent helps job seekers navigate global job markets, generate tailored application
materials, and track their progress — all from a single interactive CLI.

---

## Features

### 1. Location-Aware Job Search
- Searches and ranks job listings based on the user's skills, experience level, and location preference.
- Filters by city/region and remote-work availability simultaneously.
- Scores every listing 0–100 using Claude, with an explanatory rationale — **no protected attributes** (age, gender, ethnicity, etc.) are ever used as ranking signals.

### 2. Regional Market Intelligence
- Generates a report for any region + industry combination covering:
  - Top in-demand skills
  - Average salary (USD equivalent)
  - Year-over-year job growth
  - Competition level (low / medium / high)
  - Trending roles
  - Cultural hiring norms and interview etiquette
- Separate endpoint for culturally-aware application tips per region.

### 3. AI-Tailored Document Generator
- **Resume generator** — Produces a Markdown resume tailored to a specific job listing, mirroring keywords, quantifying achievements, and matching the required skill set.  Supports three tones: `professional`, `creative`, `technical`.
- **Cover letter generator** — Writes a compelling 3–4 paragraph letter with a company-specific hook and a skills-to-requirements bridge.
- Every document includes `tailoring_notes` explaining the specific editorial choices made.

### 4. Application Lifecycle Tracker
- Logs new applications with status, notes, and timestamps.
- Updates status through the full pipeline: `draft → submitted → under_review → interview_scheduled → offer_received / rejected / withdrawn`.
- Records employer feedback for later analysis.

### 5. Analytics Dashboard
- Computes:
  - Response rate, interview rate, offer rate
  - Average days to first employer reply
  - Status distribution
  - Top industries and source platforms
- Claude generates actionable narrative insights from the raw metrics.
- Separate employer feedback analysis: extracts recurring themes, common rejection reasons, and personal action items.

### 6. Free-form Chat Interface
- Full conversational access to all agent capabilities.
- Powered by Claude's tool-use API — the model decides which tools to call and synthesises results into coherent advice.
- Conversation history maintained across turns within a session.

---

## Architecture

```
AI-Job-Agent/
├── main.py                  # Entry point
├── requirements.txt
├── config/
│   └── settings.py          # Environment-driven configuration
├── src/
│   ├── models.py            # Pydantic domain models + SQLAlchemy ORM
│   ├── privacy.py           # AES-256-GCM encryption, PII scrubbing, bias guard
│   ├── job_search.py        # JobSearchEngine + MarketIntelligenceService
│   ├── document_generator.py# Resume & cover letter generation
│   ├── analytics.py         # ApplicationTracker with metrics + AI insights
│   ├── agent.py             # Claude tool-use orchestrator (JobAgent)
│   └── ui.py                # Rich-based interactive CLI
├── tests/
│   ├── test_privacy.py
│   ├── test_models.py
│   └── test_analytics.py
└── data/
    └── job_agent.db         # Local SQLite database (auto-created)
```

### Agentic Loop (tool-use pattern)

```
User message
     │
     ▼
  Claude API  ──────────────────────────────────────────────────┐
     │  stop_reason == "tool_use"                               │
     ▼                                                          │
Tool Dispatcher                                                 │
  ├── search_jobs            → JobSearchEngine                  │
  ├── get_market_insights    → MarketIntelligenceService        │
  ├── get_application_tips   → MarketIntelligenceService        │
  ├── generate_resume        → DocumentGenerator                │
  ├── generate_cover_letter  → DocumentGenerator                │
  ├── track_application      → ApplicationTracker               │
  ├── update_application     → ApplicationTracker               │
  ├── get_analytics          → ApplicationTracker               │
  └── get_feedback_analysis  → ApplicationTracker               │
     │                                                          │
     └── tool_results ──────────────────────────────────────────┘
                                    │
                         stop_reason == "end_turn"
                                    │
                              Final response
```

---

## Privacy & Ethics

| Concern | Mitigation |
|---|---|
| PII at rest | Name, email, phone stored AES-256-GCM encrypted (PBKDF2-derived key, 390k iterations) |
| PII sent to LLM | Only anonymised skill/role/location data is sent; scrub_pii() strips emails, phones, names before any external call |
| Bias in recommendations | Protected attributes (gender, age, race, religion, nationality, etc.) are stripped before scoring; the model prompt explicitly forbids their use |
| Data sovereignty | All data lives in a local SQLite file — nothing is uploaded to third-party job boards or analytics platforms |
| Transparency | Every resume/cover letter includes tailoring_notes; every match score includes a rationale |

---

## Setup

### Prerequisites
- Python 3.11+
- An [Anthropic API key](https://console.anthropic.com/)

### Installation

```bash
git clone <repo-url>
cd AI-Job-Agent
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### Configuration

Create a `.env` file in the project root:

```dotenv
ANTHROPIC_API_KEY=sk-ant-...

# Optional overrides
AGENT_MODEL=claude-sonnet-4-6
MAX_TOKENS=4096
ENCRYPT_USER_DATA=true
MAX_JOBS_PER_SEARCH=25
APPLICATION_COOLDOWN_DAYS=30
```

### Run

```bash
python main.py
```

---

## Running Tests

```bash
pytest tests/ -v
```

Tests are fully offline (mock Anthropic client injected via dependency injection).

---

## Extending the Agent

### Adding a Real Job Board Adapter

In `src/job_search.py`, implement a method on `JobSearchEngine`:

```python
def _fetch_from_indeed(self, profile: UserProfile) -> list[JobListing]:
    # Call the Indeed API, normalise results into JobListing objects
    ...
```

Then call it inside `search()` and merge with other sources.

### Adding a New Tool

1. Define the JSON Schema entry in `TOOLS` in `src/agent.py`.
2. Add the handler method (`_tool_<name>`).
3. Register it in `_dispatch_tool`.

### Custom Document Templates

Subclass `DocumentGenerator` and override `_resume_system_prompt()` or
`_cover_letter_system_prompt()` to inject industry-specific instructions or
brand voice guidelines.

---

## Key Design Decisions

- **Claude as the reasoning layer** — All non-deterministic decisions (scoring, insights, writing) are delegated to Claude via structured prompts and tool use.
- **SQLite for storage** — Zero-infrastructure local database keeps the agent self-contained and privacy-preserving.
- **Pydantic for validation** — Every domain object is validated at creation time, preventing malformed data from reaching the LLM.
- **Dependency injection** — The Anthropic client and DB session are injected into every service, making the test suite fully offline.
- **Bias-by-design** — Protected attributes are stripped at the data layer before any scoring prompt is constructed, not left to prompt engineering alone.

---

## Roadmap

- [ ] Real job board API adapters (LinkedIn, Indeed, Glassdoor)
- [ ] PDF / DOCX export for generated documents
- [ ] Email integration for application submission
- [ ] Calendar integration for interview scheduling
- [ ] Multi-user support with separate encrypted profiles
- [ ] Web UI (FastAPI + React) alongside the CLI
