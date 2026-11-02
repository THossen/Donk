# Donk — who wrote this code?

Donk helps you discover who contributed to a part of a repository, inspect the
Git evidence, and send that person a question after reviewing an email draft.

Scope and overrides vs the original spec live in [CURRENT_SCOPE.md](CURRENT_SCOPE.md).

## Quick start (Windows)

Prerequisites: Python 3.11+, Node 18+, Git CLI.

```powershell
# 1. Backend environment (project-local .venv)
python -m venv .venv
.\.venv\Scripts\python -m pip install -r backend/requirements.txt

# 2. Private configuration (never commit .env)
Copy-Item .env.example .env
# Edit .env: set MODEL_API_KEY for Muse investigation (optional for local demo),
# and DEMO_EMAIL_REDIRECT to YOUR email for the final send.
# For real SMTP sending also set EMAIL_MODE=smtp plus SMTP_* (see below).

# 3. Demo repository (already cloned? skip)
git clone --depth 200 https://github.com/THossen/BiddersBlock-v2.git demo-data/BiddersBlock-v2

# 4. Start the backend (from the project root)
.\.venv\Scripts\python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000

# 5. Start the frontend (second terminal, from the project root)
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 in a browser.

Without `MODEL_API_KEY`, Donk runs deterministic local analysis (real Git
evidence, template answers). With the key, the backend performs tool-using
Muse investigations over the same evidence. Verify the key with
`GET http://127.0.0.1:8000/api/health/model` (expect `{"ok": true, ...}`);
without a key it returns 503 and the UI says so.

## How it works

- **Backend** (`backend/app/`): FastAPI + Git CLI. `gittools.py` exposes
  bounded search/snippet/log/blame at the pinned HEAD. `llm_service.py` is the
  application's own model service: Responses API tool loop
  (`search_files`, `read_snippet`, `git_log`, `explain_authorship`) plus a
  deterministic fallback. `verify.py` checks that cited evidence IDs resolve
  against the snapshot (reference validation — it does not prove every AI
  interpretation). `actions.py` + `store.py` implement propose/confirm-send
  with SQLite, idempotency, rate limits, and outbox/SMTP delivery.
- **Frontend** (`frontend/src/`): React + Vite + Tailwind. Ask input first,
  live tool-progress timeline, contributor cards (main contributor / wrote it
  first / last touched), clickable evidence chips + inspector, a focused
  contributor→code graph, an editable email confirmation card, and activity.
- **History bounds** (disclosed in the UI): ≤50 commits, ≤200 blame lines,
  ≤20 search hits, ≤80 snippet lines per call. Disk cache keyed by
  (args + HEAD), 24h TTL. The whole repo is never sent to the model.
- **Analyzed repos are data**: read-only Git access; nothing in them is
  executed and no instructions in them are followed.

## Email safety

- The model proposes drafts; it cannot send. Sending needs your explicit Send
  click through `POST /api/actions/{id}/send`.
- `DEMO_MODE=true` (default) forces **all** delivery to `DEMO_EMAIL_REDIRECT`
  (your inbox). The UI shows the contributor identity separately from the
  actual delivery address.
- `EMAIL_MODE=outbox` (default) saves `.eml` files under `outbox/` — nothing
  leaves the machine. `EMAIL_MODE=smtp` sends via your SMTP server.
- Outside demo mode, recipients must be in the roster (`team.json`,
  gitignored; see `team.json.example`). Git author emails are identity signals
  only and are never delivery destinations.
- One recipient, no CC/BCC/attachments, ≤5 sends/hour, idempotent sends,
  failures recorded (never shown as delivered).

### SMTP setup (example: Gmail app password)

```powershell
# in .env:
EMAIL_MODE=smtp
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=you@gmail.com
SMTP_PASS=<app password, not your login>
SMTP_FROM=you@gmail.com
DEMO_MODE=true
DEMO_EMAIL_REDIRECT=you@gmail.com
```

Keep `DEMO_MODE=true` for the demo so every send lands in your inbox. No test
emails are sent automatically — you trigger the final send in the UI.

## Tests

```powershell
.\.venv\Scripts\python -m pytest backend/tests -q
```

Small fast Git fixtures cover: original vs main vs recent attribution,
ambiguity (multiple mains), unknown questions, invalid evidence IDs,
propose-never-sends, confirm/duplicate-send, demo redirect, rate limit, and
SMTP-failure recording. No network, no auto-sends.

## Publishing to GitHub

Secrets live only in `.env`, which is gitignored — never force-add it
(`git add -f .env`). What is safe to push:

- `.env.example` / `team.json.example`: placeholder templates (a test fails if
  real-looking values creep into `.env.example`).
- `demo-data/`, `outbox/`, `*.db`, `.cache/`: ignored — analyzed repo
  history, drafts, and caches stay on your machine.
- Backend config defaults carry no secrets; the model key comes from the
  environment (`MODEL_API_KEY`) and is never returned by any API.

If a real key was ever committed, rotate it at the provider and rewrite the
pushed history — deleting the file later does not remove it from history.

## Known limitations

- Git history shows activity, not understanding. "Main contributor" is inferred
  from surviving lines + commits — never official ownership.
- Shallow/bounded history weakens original-authorship claims for old code;
  bounds are disclosed wherever truncation applies.
- Draft question suggestions are grounded in cited files but are still
  generated text — review before sending.
- `.repos/` and `node_modules/` mirrors are excluded from content search as
  vendored noise.
- Donk is not for grading, employment decisions, or measuring individual effort.
