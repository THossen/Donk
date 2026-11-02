# Donk demo script (reproducible, ~5 minutes)

Prereqs: backend on :8000, frontend on :5173 (see README). `.env` has
`DEMO_EMAIL_REDIRECT=<your email>`. Start in outbox mode; switch to SMTP only
for the final send.

## 1. Open the analyzed repo (30s)

Open http://localhost:5173. The sidebar shows `BiddersBlock-v2`, pinned HEAD
`e6e2ab0`, and the history bounds. Note the demo/outbox mode line.

## 2. Ask about auth (60s)

Type **"Who worked on auth?"** (or click the suggestion chip). Watch the
investigation timeline: real tool calls (`search_files`, `explain_authorship`)
stream in — no fake progress.

Expect: headline naming a main contributor for `apps/server/src/auth`, with
supporting files, commits, and dates. Auth here means the in-repo pairing +
session code (`EnvironmentAuth.ts`, `PairingGrantStore.ts`, policy files).
Provider credential auth (Claude/Codex OAuth) lives outside this repo — if you
ask about that, Donk should say the evidence isn't here.

## 3. Inspect the evidence (60s)

- Click evidence chips (files/commits) to open the inspector: snippets with
  line numbers, commit author/date/subject, blame gutters.
- Check the contributor→code graph: contributors left, files right; edges from
  this investigation light up as tool results arrive. Click a file node.
- Note "Wrote it first / Main contributor / Last touched" — three different
  questions with three possibly different answers.
- The repo tree at the top expands and zooms to the answer's scope; matching
  nodes light up as tool results stream in. Click a branch to expand, a node
  to zoom, "Whole repo" to reset.

## 4. Ask the contributor (90s)

The email prompt opens automatically for the main contributor (click **Ask**
on another card to switch person). Either type your question or click
**Suggest a question from the code**. Click **Prepare draft**.

## 5. Review and send (60s)

The confirmation card shows the contributor identity separately from the
actual delivery address (`Delivers to: <your demo inbox>` + demo-mode notice).
Edit the subject/body, then click **Send**.

- Outbox mode: result reads "Saved to outbox" with the `.eml` under `outbox/`.
- SMTP mode (`EMAIL_MODE=smtp` + SMTP_* set): result reads "Sent (accepted by
  mail server…)" and the mail lands in YOUR inbox via the demo redirect — never
  at an address scraped from Git history.

## 6. Verify the record (30s)

The Activity tab lists the action with its honest status. Duplicate Send
clicks replay the original result without resending.

## Backup questions (if auth disappoints)

- "Who changed the server pairing code?"
- "Who wrote the provider integrations?"
