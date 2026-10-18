# Car rental chatbot

A multi-agent conversational assistant for a (fictional) car rental company, built with **LangGraph** and
language models served by **Groq**. Visitors search for a car by city and dates, ask for recommendations and
go through a simulated booking.

| | |
|---|---|
| Live demo | *published on Render — URL added after the first deployment* |
| Portfolio page | https://portfolio.gabriel-olius.workers.dev/projects/car-rental-chatbot/ |
| Original version | tag [`v0-original`](https://github.com/6roli/Car_Rental_Chatbot/tree/v0-original) and branch `original` (kept unchanged) |
| Cost | €0 (Render Free + Groq free tier, no payment methods) |

> **Demo notice:** the fleet is randomly generated, no real booking is made, and visitors are asked not to enter
> real personal data. Messages are sent to Groq to generate answers; this app does not store them.

## How it works

```
Visitor message
   │
   ├─ stage "search" ── Search workflow (LangGraph)
   │      extract_criteria  (LLM, small model)  → city, dates, max price as structured data
   │      check_criteria    (Python)            → clear messages for missing or invalid data
   │      search_inventory  (Python + SQLite)   → parameterised query, cheapest first
   │
   └─ stage "chat" ──── Conversation workflow (LangGraph, memory per visitor)
          supervisor        (LLM, small model)  → routes to one of:
          recommendation    (LLM, large model)  → advice using only the cars found
             └─ tools       (optional Tavily web search, for weather questions)
          booking           (LLM, large model)  → simulated booking, reminds to use fake data
```

The language model only does what needs language understanding. Validation, the SQL query and the car list are
plain Python, so the bot cannot invent cars, write a wrong query or format prices inconsistently — and each
message uses less of the free quota.

### What changed from the original

| Original (`v0-original`) | Now |
|---|---|
| Model `mixtral-8x7b-32768` (retired by Groq) | `llama-3.3-70b-versatile` and `llama-3.1-8b-instant`, configurable |
| Database with dates only up to 31 Dec 2025 | Synthetic fleet generated daily, available from today for 180 days |
| City list in the validator did not match the database | Cities come from one list shared by data and validation |
| LLM wrote SQL and formatted results | Python builds a parameterised query and formats results |
| Conversation state in global variables (visitors would mix) | One session and LangGraph thread per visitor |
| No limits | Per-visitor (20/hour) and global (300/day) message limits; friendly errors when Groq's quota runs out |
| 143 pinned packages in a UTF-16 `requirements.txt` | 7 direct dependencies in `pyproject.toml` |
| API keys committed in early history | Keys only in `.env` (ignored) or Render secrets |
| No tests | 17 pytest tests (data, validation, sessions, limits, web API) |

## Project layout

```
car_rental/
  config.py       Settings from environment variables (.env locally, secrets on Render)
  inventory.py    Synthetic fleet (SQLite in memory) and the parameterised search
  agents.py       LangGraph workflows, prompts and structured outputs
  assistant.py    One message in → one reply out, per visitor stage
  sessions.py     Per-visitor sessions and usage limits
  web.py          Flask app: page, /chat API, /health, security headers
  templates/, static/   Chat page (plain HTML, CSS, JavaScript)
tests/            pytest tests (no API key needed)
render.yaml       Render deployment settings
pyproject.toml    Dependencies and project metadata
.env.example      Template for local secrets
```

## Technologies: what, where, why

| Technology | Runs where | Why |
|---|---|---|
| **Python 3.13** | Your computer and Render | Language of the whole app |
| **LangGraph** | Server | Defines the agents and how messages flow between them; keeps memory per conversation |
| **LangChain + langchain-groq** | Server | Common interface to the language model, structured outputs, tools |
| **Groq** | Groq's cloud | Runs the open models (Llama 3) very fast; free tier with daily limits |
| **Tavily** (optional) | Tavily's cloud | Web search for weather questions |
| **SQLite** | Server memory | Small database for the fictional fleet |
| **Flask + gunicorn** | Server | Web page and JSON API; gunicorn is the production web server |
| **pytest** | Your computer and Render's build | Automatic tests |
| **Render** | Render's cloud | Hosts the server for free and redeploys on every push to `main` |

## Run locally (VS Code)

Requirements: Python 3.12+ and Git.

```bash
git clone https://github.com/6roli/Car_Rental_Chatbot.git
cd Car_Rental_Chatbot
python -m venv .venv
.venv\Scripts\activate              # Windows  (macOS/Linux: source .venv/bin/activate)
pip install -e ".[dev]"
copy .env.example .env              # macOS/Linux: cp .env.example .env
#   then put your own GROQ_API_KEY in .env  (free at https://console.groq.com/keys)
flask --app car_rental.web run      # http://127.0.0.1:5000
```

| Command | Purpose |
|---|---|
| `flask --app car_rental.web run --debug` | Development server with auto-reload |
| `python -m pytest` | Tests (no API key needed) |

## Publish on Render (free)

1. Sign in at https://render.com with GitHub (no card needed for the free instance).
2. **New → Blueprint** → choose this repository. Render reads `render.yaml`.
3. When asked, paste your **new** `GROQ_API_KEY` (and optionally `TAVILY_API_KEY`). They are stored as secrets.
4. Deploy. The address looks like `https://car-rental-chatbot.onrender.com`.

After that, every push to `main` runs the tests and redeploys; if a test fails, the previous version stays online.

Free-plan behaviour: the service sleeps after 15 minutes without visitors and the next visit takes about a minute
to wake it. Render gives 750 free instance hours per month; without a payment method it suspends the service
instead of charging.

## Costs and limits

| Item | Plan | Cost | Protection |
|---|---|---|---|
| Hosting | Render Free | €0 | No payment method → suspended, never billed |
| Language model | Groq free tier | €0 | Daily token limits per model; the app answers politely when they are reached. Don't add a card to Groq unless you decide to pay |
| Weather search | Tavily free credits (optional) | €0 | Only used for weather questions |
| Abuse | — | — | 20 messages per visitor per hour, 300 per day in total, 500 characters per message |

Adjust the limits with environment variables (see `.env.example`).

## Security

- Never commit `.env` or keys. If a key is ever exposed, revoke it in the provider's dashboard and create a new one.
- The original repository history contains old keys; they must be revoked (rewriting history does not undo exposure).
- Model replies are displayed as plain text, never as HTML.
- The page sends a Content-Security-Policy and does not allow being embedded in other sites.
