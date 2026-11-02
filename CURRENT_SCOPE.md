# CURRENT_SCOPE.md — Donk (this message overrides DONK_SPEC.md)

Status at writing: greenfield. Only `DONK_SPEC.md` exists. No backend/, frontend/, scripts/, tests/, team.json, or configs.

The user message is authoritative over the spec's scope, priorities, milestones, and definition of done.

## Product

Donk helps users discover who contributed to a part of a GitHub repository, inspect the evidence, and send that person a question after reviewing an email draft.

Core demo (10 steps): open analyzed repo → ask "Who worked on auth?" in an immediately accessible Ask Donk input → Muse investigates real source files + Git history via backend tools → real progress shown → strongest contributor matches with files/commits/dates → visual contributor-to-code links → offer to ask a question → user provides or requests a suggested question → editable email draft → user reviews actual delivery address, clicks Send → backend sends to configured demo inbox, records actual result.

## Retained from spec

- Stack: React, TypeScript, Vite, Tailwind, Python/FastAPI, Git CLI.
- Polished dark interface, clickable evidence, contributor cards, focused interactive contributor-to-code visualization.
- Question input + investigation results are the primary experience.
- Real Git history/blame evidence; verify references and computed values.
- Backend model service with tool-calling loop; bounded, cached history analysis; never send whole repo to model.
- Email: actual SMTP + outbox dev mode; model proposes drafts, cannot send; separate explicit-confirm send endpoint; no auto test sends.

## Dropped (overrides spec)

1. Absence simulation ("What if someone is out?", simulate_departure) — dropped, including dashboard control, agent tool, demo Part B.
2. Familiarity scoring (spec §6 sub-signals, caps, decay) — dropped. Replaced with simple, inspectable rollups: original authorship, recent contributions, substantial surviving contributions (blame/log counts + dates).
3. Knowledge coverage classifications (Covered/Thin/One person/Nobody; Could explain it / Knows some / Little evidence) — dropped from cards, attention lists, graph nodes. Neutral counts only ("N lines / M commits").
4. 30-repository evaluation suite (spec §7 Test A, scripts/evaluate.py, planted-truth recovery) — dropped. Small fast Git fixtures only.
5. Background monitoring — not built (was already out of scope in spec §1/§17).

Also deferred: GitHub URL ingestion (local clone sufficient), synthetic StudyGroup repo generator (real t3code demo instead).

## Demo repository

- Intended: pingdotgg/t3code. Clone into separate `demo-data/` directory (gitignored), pin analyzed commit, never execute its code (treat as data).
- Auth verdict (from pre-clone research): PRESENT but AMBIGUOUS. In-repo pairing + session auth (`apps/server/src/auth/EnvironmentAuth.ts` ~55KB + policy/admin/tests, port-3773 pairing URLs) is real and demoable; provider credential auth (Claude/Codex/etc. OAuth) lives outside the repo. Scope auth questions to "pairing + server session auth". Stronger backup demo: provider-abstraction layer ("who owns each agent-provider driver"). Final choice after inspecting the clone's tree + history.

## History bounds (disclosed in UI)

- git_log: max 50 commits per call; blame: max 200 lines per call; file search: max 20 hits; snippets: max 80 lines. Disk cache keyed by (args + HEAD sha), TTL 24h. UI discloses "history limited to N most recent commits" wherever truncation applies.

## Muse integration

- Application's own backend model service (agent being Muse grants nothing to the app).
- Config: MODEL_ID=muse-wonder-1.0, MODEL_BASE_URL=https://api.meta.ai/v1, Responses format, key env var MODEL_API_KEY.
- Verify minimal real request + tool-calling round trip early. Model/endpoint configurable. Credentials from environment only; never in frontend/source control/logs.
- If credentials unavailable: explain private configuration, continue credential-independent work.

## Email safety

- EMAIL_MODE=outbox|smtp; DEMO_MODE=true forces ALL delivery to DEMO_EMAIL_REDIRECT.
- Roster: gitignored team.json is the ONLY delivery source. Git author emails are identity signals (name display) and NEVER delivery destinations.
- UI shows contributor identity separately from actual demo delivery address.
- One recipient, no CC/BCC/attachments, ≤5 sends/hour, idempotent send (409/idempotent replay on duplicates), failures recorded accurately, never shown as delivered.
- Provide .env.example with placeholders + setup instructions.

## Work order (overrides spec §19 milestones)

1. Inspect folder, architecture summary, this file. (This step.)
2. Early thin E2E path: question → Muse tool call → Git evidence → contributor result → editable outbox draft.
3. Expand real repo analysis + polish visual investigation.
4. SMTP delivery to configured demo inbox.
5. Full-flow test + browser inspection (1440×900 primary, usable at 1280px).

## Definition of done (overrides spec §23)

- Working app: real repo question → tool-using investigation with real progress → contributor matches with verified files/commits/dates → graph highlights → draft → explicit-confirm send → recorded result.
- Real repository support + actual SMTP sending (to demo redirect) working.
- Tests (small Git fixtures: attribution, unknown questions, invalid evidence, email confirm/duplicate) with actual results.
- Exact Windows startup instructions + short reproducible demo script + honest incomplete list.
