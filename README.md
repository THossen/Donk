<img src="frontend/public/donk.svg" width="64" alt="Donk logo">

# Donk — who wrote this code?

Point Donk at any Git repository, ask who built a part of it, and get the
contributors with clickable Git evidence — then send one of them a question
after reviewing an email draft. No key required to start: without a model API
key Donk runs fully local deterministic analysis over real Git history.

## Features

- **Ask in plain English** — "who built the auth flow?" streams a live
  investigation timeline and lands on contributor cards: main contributor,
  who wrote it first, who touched it last. Follow-ups ("why them?", "only
  the backend") continue the same investigation with its scope and evidence.
- **Evidence, not vibes** — every claim links to the commit, blame lines, or
  snippet behind it, with an inspector to read the code in context.
- **Repo map** — an expandable tree of the repository that zooms to the files
  your question touches.
- **Ask a contributor** — prepare an email draft (model-written or template),
  edit it, and confirm the send. Pending drafts can be resumed or discarded
  later from Activity.
- **Past investigations** — every investigation is saved with its answers.
  Reopen one to restore the full results and keep asking where you left off.
- **Multiple repos** — detect and switch repositories without restarting.
- **Command palette** (`Cmd/Ctrl-K`) — ask, navigate, and switch repos from
  the keyboard.
- **Safe by default** — demo mode redirects all delivery to your inbox, and
  the default outbox mode never sends anything anywhere.

## Quick start

Prerequisites: Python 3.11+, Node 18+, Git CLI.

### Windows (PowerShell)

```powershell
# 0. Clone Donk
git clone https://github.com/THossen/Donk.git
cd Donk

# 1. Backend environment (project-local .venv)
python -m venv .venv
.\.venv\Scripts\python -m pip install -r backend/requirements.txt

# 2. Private configuration (never commit .env)
Copy-Item .env.example .env
# Edit .env: MODEL_API_KEY enables Muse investigation (optional);
# DEMO_EMAIL_REDIRECT is your inbox for the final send.
# For real SMTP sending also set EMAIL_MODE=smtp plus SMTP_* (see below).

# 3. Demo repository (already have one? point REPO_PATH at it and skip)
git clone --depth 200 https://github.com/THossen/BiddersBlock-v2.git demo-data/BiddersBlock-v2

# 4. Start the backend (from the project root)
.\.venv\Scripts\python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000

# 5. Start the frontend (second terminal, from the project root)
cd frontend
npm install
npm run dev
```

### macOS / Linux (bash or zsh)

```bash
# 0. Clone Donk
git clone https://github.com/THossen/Donk.git
cd Donk

# 1. Backend environment (project-local .venv)
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r backend/requirements.txt

# 2. Private configuration (never commit .env)
cp .env.example .env
# Edit .env: MODEL_API_KEY enables Muse investigation (optional);
# DEMO_EMAIL_REDIRECT is your inbox for the final send.
# For real SMTP sending also set EMAIL_MODE=smtp plus SMTP_* (see below).

# 3. Demo repository (already have one? point REPO_PATH at it and skip)
git clone --depth 200 https://github.com/THossen/BiddersBlock-v2.git demo-data/BiddersBlock-v2

# 4. Start the backend (from the project root, .venv activated)
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000

# 5. Start the frontend (second terminal)
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

## Configuration

All settings live in `.env` (see `.env.example` for the full template):

| Key | Default | What it does |
| --- | ------- | ------------ |
| `MODEL_API_KEY` | _(empty)_ | Enables Muse investigation; empty = local demo mode |
| `MODEL_ID` / `MODEL_BASE_URL` | `muse-wonder-1.0` | Model and API endpoint |
| `REPO_PATH` | `./demo-data/BiddersBlock-v2` | Repository under investigation (read-only) |
| `EMAIL_MODE` | `outbox` | `outbox` saves `.eml` locally; `smtp` really sends |
| `DEMO_MODE` | `true` | Forces all delivery to `DEMO_EMAIL_REDIRECT` |
| `DEMO_EMAIL_REDIRECT` | _(empty)_ | Your inbox for demo sends |
| `SMTP_HOST/PORT/USER/PASS/FROM` | | Real sending credentials (SMTP mode only) |

History bounds (`GIT_MAX_COMMITS`, `GIT_MAX_BLAME_LINES`,
`SEARCH_MAX_RESULTS`, `SNIPPET_MAX_LINES`) default to 50 / 200 / 20 / 80
and are disclosed in the UI wherever truncation applies.

## How it works

- **Backend** (`backend/app/`): FastAPI + Git CLI. `gittools.py` exposes
  bounded search/snippet/log/blame at the pinned HEAD. `llm_service.py` is
  the application's own model service: Responses API tool loop
  (`search_files`, `read_snippet`, `git_log`, `explain_authorship`) plus a
  deterministic fallback. `verify.py` checks that cited evidence IDs resolve
  against the snapshot (reference validation — it does not prove every AI
  interpretation). `actions.py` + `store.py` implement propose/confirm-send
  with SQLite, idempotency, rate limits, and outbox/SMTP delivery.
  Contributor cards and graphs always describe the files actually
  investigated — never a re-derived repository-wide rollup. Completed
  investigations persist as threads in SQLite, so follow-ups reuse prior
  scope, findings, and evidence (per repository; switching repos starts
  a fresh thread).
- **Frontend** (`frontend/src/`): React + Vite + Tailwind. Ask composer,
  conversational investigation view, contributor cards, clickable evidence
  chips + slide-over inspector, repository map and contributor graph behind
  tabs, editable email confirmation card, activity feed, past
  investigations, and a command palette.
- **Performance**: disk cache keyed by (args + HEAD) with 24h TTL. The whole
  repo is never sent to the model.
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

On macOS/Linux, with the venv from quick start activated:

```bash
python -m pytest backend/tests -q
```

Small fast Git fixtures cover: original vs main vs recent attribution,
ambiguity (multiple mains), unknown questions, invalid evidence IDs,
propose-never-sends, confirm/duplicate-send, discard, resume payload,
ask-history record/list/delete, investigation threads (create, continue,
repo-mismatch, investigated-file scope preservation), demo redirect, rate
limit, and SMTP-failure recording. No network, no auto-sends.

## Project structure

```
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI app + router wiring
│   │   ├── routes/          # ask, email/activity, investigations, repos endpoints
│   │   ├── services/        # investigation orchestration
│   │   ├── llm_service.py   # model tool loop + deterministic fallback
│   │   ├── gittools.py      # bounded Git access at pinned HEAD
│   │   ├── actions.py       # propose / confirmed-send / discard
│   │   ├── store.py         # SQLite: actions, investigations, question history
│   │   └── ...              # config, evidence, verify
│   └── tests/               # pytest suite (fast Git fixtures, no network)
├── frontend/
│   └── src/
│       ├── api/             # typed client + types
│       ├── components/      # dashboard, activity, repos, evidence, command, ui kit
│       └── utils/           # time, colors, evidence, repo helpers
├── .env.example             # placeholder config template (safe to commit)
├── team.json.example        # approved-recipient roster template
└── demo-data/               # your local analyzed repos (gitignored)
```

## Security notes for contributors

- Secrets live only in `.env`, which is gitignored — never force-add it
  (`git add -f .env`).
- `.env.example` / `team.json.example` are placeholder templates; a test
  fails if real-looking values creep into `.env.example`.
- `demo-data/`, `outbox/`, `*.db`, `.cache/` are ignored — analyzed repo
  history, drafts, and caches stay on your machine.
- Backend config defaults carry no secrets; the model key comes from the
  environment (`MODEL_API_KEY`) and is never returned by any API.
- If a real key was ever committed, rotate it at the provider and rewrite the
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
- Follow-ups carry the last few turns of context, per repository — switching
  repos starts a fresh investigation. In local (no-key) mode, a follow-up
  reuses the previous scope rather than interpreting new intent.
- Donk is not for grading, employment decisions, or measuring individual effort.

## Docs

- [CURRENT_SCOPE.md](CURRENT_SCOPE.md) — scope and overrides vs the original spec.
- [DEMO.md](DEMO.md) — demo script.
- [DONK_SPEC.md](DONK_SPEC.md) — original specification.
