# DONK v6 — Master Build Prompt

## Role and objective

You are an expert full-stack engineer, AI agent engineer, product designer, and technical lead.

Build **Donk**, a polished, functional AI-powered project resilience platform designed for student software development teams.

This is a submission for the Meta Global AI Developer Hackathon. It must demonstrate meaningful Meta Model API integration, genuine technical functionality, an intuitive user experience, and a memorable end-to-end demonstration.

**Do not build a generic AI chatbot, a static Git analytics dashboard, or a collection of disconnected prototypes. Build a cohesive application that feels like a real developer product.**

Use AI-assisted development aggressively, but prioritize correctness, reliability, and product quality.

If an existing Donk repository or earlier specification exists, inspect it first. Reuse working code and reconcile differences with this specification. This prompt is the authoritative product direction.

Before implementing, provide a concise architecture, assumptions, milestones, and any conflicts with existing code. Then proceed without waiting for approval unless a genuinely blocking dependency requires user input.

---

# 1. Product vision

## What is Donk?

Donk is an AI project teammate that helps student developers understand their shared codebase, identify knowledge bottlenecks, and coordinate with one another before problems become critical.

Students working on group programming assignments frequently encounter situations where:

- One teammate implemented an important feature that nobody else understands.
- The rest of the team doesn't know who to contact about a specific piece of code.
- A teammate becomes unavailable shortly before a deadline.
- The team needs to understand unfamiliar code without manually searching through dozens of commits.
- Students waste time coordinating explanations and clarifying responsibilities.

Donk addresses these problems by connecting Git repository evidence, contributor information, visual project mapping, and an actionable AI agent.

## Core capabilities

Users can:

1. Open an interactive dashboard showing their project, contributors, components, and inferred knowledge risks.
2. Explore a visual graph of how contributors relate to project components.
3. Ask natural-language questions about code authorship, project familiarity, and knowledge concentration.
4. Investigate repository evidence, including Git commits, relevant files, and surviving authored lines.
5. Simulate what happens when a teammate becomes temporarily unavailable.
6. Ask Donk to investigate technical questions and determine whom to contact.
7. Have Donk prepare contextual emails to teammates.
8. Review, edit, approve, and send emails through a secure confirmation workflow.
9. Review pending approvals and recorded actions.

Donk is focused on **student-team resilience**, not monitoring or ranking teammates.

Git history is evidence of activity, not proof of understanding, effort, skill, or assignment completion.

## Primary product promise

**Donk understands the history of your team's codebase and helps you figure out what to do next.**

---

# 2. Technical stack

Use the following unless the existing repository has a working, compatible alternative.

### Frontend

- React
- TypeScript
- Vite
- Tailwind CSS
- React Flow (`@xyflow/react`) for the interactive project map, if it is the best fit
- Lucide icons
- Reusable modular components

### Backend

- Python
- FastAPI
- Git CLI for repository analysis
- SQLite for action history and persistent application state if necessary
- Pydantic for validated data structures
- Server-sent events for agent progress streaming where practical

### Artificial intelligence

- Meta Model API
- Muse Spark, using the actual available model identifier verified from current documentation
- A single backend `llm_service` abstraction
- Structured outputs where supported
- Tool calling or an equivalent validated tool-execution loop
- Disk caching of repeatable demo responses

### Environment configuration

Credentials and runtime configuration must come from environment variables.

Include configurable settings for:

- Model identifier
- Meta Model API base URL
- API credentials
- Repository path
- Demo mode
- Email mode
- SMTP credentials
- Demo email redirect
- Familiarity thresholds

Do not assume an API endpoint or model capability exists without checking documentation or an available working example.

Never expose credentials in frontend code, Git commits, logs, or generated artifacts.

---

# 3. Implementation priorities

Use explicit priority tiers.

## MUST — required for a complete submission

- Functional Git analyzer.
- Deterministic contributor familiarity signals.
- Synthetic student repository with planted ownership patterns.
- Early analyzer evaluation against baseline approaches.
- Attractive, responsive dashboard.
- Interactive developer-to-component knowledge map.
- Evidence inspector.
- Functional teammate-absence simulation.
- Muse-powered repository investigation.
- Structured evidence verification.
- Persistent Ask Donk interface.
- Draft and approve email workflow.
- Functional local outbox.
- Recipient and email safety checks.
- Recorded pending and completed actions.
- Reproducible end-to-end demo.

## SHOULD — implement after MUST features work

- Real local repository support.
- SMTP email sending.
- Author-colored Git blame view.
- Authorship timeline visualization.
- Additional responsive layout refinement.
- CODEOWNERS comparison if applicable.

## STRETCH — implement only with remaining time

- GitHub URL ingestion.
- Advanced graph clustering.
- Extended historical analysis.
- Additional animations.
- More sophisticated repository visualization.

If resources become constrained, remove STRETCH features first, followed by SHOULD features.

Never substitute mocked functionality for unfinished MUST features.

---

# 4. Demo repository and data pipeline

Build the real data foundation before implementing dashboard metrics.

## Synthetic student project

Create a deterministic synthetic Git repository called:

**Team 3 — StudyGroup**

It represents four students building a study-group web application for a course project.

Contributors:

- Priya — primarily frontend and some API integration.
- Marcus — primarily API server and authentication.
- Jin — primarily database infrastructure.
- Sofia — primarily recommendation functionality.

Components:

1. Frontend UI
2. API Server
3. Authentication
4. Database
5. Recommender
6. Deployment Configuration

### Planted knowledge patterns

- Marcus is the only contributor with a strong familiarity signal for Authentication.
- Marcus also has the strongest signal for API Server.
- Priya has strong frontend familiarity and some API integration activity.
- Jin primarily works on Database.
- Sofia primarily works on Recommender.
- Deployment Configuration has limited or stale activity.

These patterns must emerge from actual generated Git history, not frontend hardcoding.

### Generator constraints

Create `scripts/make_synthetic_repo.py`.

Generate approximately:

- 20–30 short source files.
- 80–120 Git commits.
- Four fictional authors.
- Realistic timestamps.
- Plausible commit messages.
- Meaningful source modifications.
- A small number of noise commits.

Include adversarial history patterns:

- Formatting-only changes.
- Lockfile modifications.
- Duplicate author emails.
- An unusually large late commit.
- A contributor with many small commits.
- An inactive original contributor.
- Merge commits where feasible.

Use templates, configuration, and fixed random seeds.

Do not waste significant resources generating a large application with hundreds of complex files.

Store the planted ownership map separately from the analyzer's input.

## Data integrity

The same analyzer must process:

1. The generated demo repository.
2. A real local repository.

Do not maintain separate mock and production analysis logic.

Generate and cache a JSON snapshot of the demo analyzer output so the dashboard opens immediately.

All visible metrics, graph edges, contributor relationships, and repository evidence must derive from analyzer results.

Cache keys must account for the repository snapshot and relevant configuration.

---

# 5. Git analyzer

Build the analyzer as deterministic Python code before adding AI functionality.

## Commit extraction

Use Git CLI with bounded history extraction.

Capture:

- Commit hash.
- Author name and email.
- Timestamp.
- Commit message.
- Changed files.
- Additions and deletions.
- Relevant co-author metadata.

Support configurable history windows and maximum commit counts.

## Author normalization

- Merge identities using reliable email/name heuristics.
- Respect `.mailmap`.
- Exclude recognized bots.
- Avoid incorrectly merging distinct people with ambiguous names.
- Preserve internal identity mappings without displaying Git email addresses.

## Noise filtering

Exclude or discount:

- Merge commits.
- Generated files.
- Vendored files.
- Minified files.
- Lockfiles.
- Formatting-only commits.
- Large mass-renaming changes.
- Snapshot files.

Expose which changes were excluded and why.

## Component classification

Group files into logical components.

Use:

1. Configured path glob mappings.
2. Top-level directory fallback.

Create a reusable `ComponentClassifier` interface so more sophisticated classification can be added later.

---

# 6. Familiarity scoring and project resilience

Donk should infer contributor familiarity from several Git signals.

Do not equate commit count with knowledge.

## Per-contributor signals

Calculate:

- Surviving authored lines at HEAD from Git blame.
- Recency-weighted meaningful changes.
- Distinct meaningful commits over time.
- Significant file introductions or rewrites.
- Contributions across relevant component files.

Use capped contributions so one enormous commit does not dominate.

Use a configurable recency-decay formula.

Keep each sub-signal available for inspection.

## Component coverage

For each component, calculate:

- Contributors with meaningful familiarity signals.
- Top-contributor concentration.
- Number of contributors above configured thresholds.
- Time since meaningful activity.
- A coverage classification.

Statuses:

- **Covered** — multiple contributors have meaningful familiarity evidence.
- **Thin** — some evidence, but limited redundancy.
- **One person** — only one contributor has sufficient evidence.
- **Nobody** — no contributor meets the configured threshold.

These are inferred statuses, not factual assessments of students.

Use user-facing language:

- Could explain it
- Knows some of it
- Little evidence

Show exact scoring formulas only within technical details.

---

# 7. Early evaluation framework

Implement evaluation immediately after the analyzer and repository generator.

Do not defer all evaluation until final polish.

Create `scripts/evaluate.py`.

## Test A — planted-truth recovery

Generate at least 30 synthetic repository variations using different seeds and noise patterns.

Compare familiarity scoring against:

- Raw meaningful commit count.
- Lines added.

Report:

- Top-1 ownership recovery accuracy.
- Top-3 ownership recovery accuracy.
- Results on adversarial histories.

Do not claim improvement unless the measured results support it.

## Test B — departure simulation

Verify that removing a planted sole contributor identifies the expected uncovered components.

Test cases with multiple knowledgeable contributors should remain appropriately covered.

## Test C — authorship verification

Verify that Donk identifies:

- Original meaningful author.
- Primary current maintainer inferred from Git evidence.
- Most recent meaningful editor.

## Test D — citation faithfulness

Evaluate at least 20 fixed questions.

Measure:

- Whether cited evidence exists.
- Whether referenced metric values match deterministic calculations.
- How frequently answer repair was required.
- Whether unsupported questions are handled honestly.

## Test E — email safety

Test that:

- The AI cannot directly send emails.
- Proposed drafts cannot send without explicit confirmation.
- Unknown recipients are rejected.
- Demo-mode redirection works.
- Rate limits are enforced.
- Failed sends do not appear as delivered.
- Repeated confirmations cannot accidentally send the same action multiple times.

## Reporting

Write a readable Markdown evaluation report.

Clearly distinguish:

- Tested correctness.
- Synthetic evaluation limitations.
- Unverified assumptions.
- Real-world limitations.

Synthetic evaluation demonstrates recovery of planted patterns, not actual human understanding.

---

# 8. Visual product direction

Create a premium dark-mode developer workspace.

The application should feel like a refined startup product, not a standard hackathon template.

### Design references

Borrow principles from:

- Linear — organization, typography, information hierarchy.
- React Flow-style editors — interactive project graphs.
- Modern AI agent workspaces — visible execution progress and action approval.

Do not reproduce another product's exact design.

## Colors and typography

Use:

- Deep charcoal/navy background.
- Slightly lighter slate cards.
- Muted teal/cyan primary accent.
- Reserved amber and red for risk.
- A consistent colorblind-safe palette for people.

Typography:

- Inter for interface text.
- JetBrains Mono for filenames, code, and commit hashes.

Visual guidelines:

- 8px spacing grid.
- 12px border radius.
- Subtle borders.
- Restrained shadows.
- Clean empty states.
- Soft transitions around 200–300 ms.
- Clear hover and selection states.
- Accessible contrast.
- Keyboard accessibility.
- Reduced-motion support.

Avoid:

- Excessive gradients.
- Floating decorative blobs.
- Neon glow around every card.
- Huge dashboard headers.
- Unnecessary charts.
- Tiny unreadable labels.
- Random animations.
- Generic AI-generated dashboard aesthetics.

**The interface should feel calm, technical, and deliberate.**

---

# 9. Application layout

Target 1440×900 and 1920×1080 desktop layouts.

Remain usable at 1280px without horizontal page scrolling.

## Left sidebar

Approximately 200–220px.

Contains:

- Donk logo.
- Current project name.
- Overview.
- Project Map.
- Data source indicator.
- Reset Demo.

Do not create a Settings button unless it opens an actual implemented settings view.

Only show configured data sources. Never display a nonfunctional selector option.

## Main workspace

Changes between:

- Overview
- Project Map

Use clear headings and contextual controls.

## Right agent panel

Approximately 380–420px.

Persistent throughout the application.

Contains two tabs:

- **Ask Donk**
- **Activity**

The panel should remain useful regardless of which main view is selected.

Provide collapse/resizing behavior where practical.

The agent conversation should maintain state while navigating between views.

Avoid making the user repeatedly reopen or restart the agent.

---

# 10. Overview dashboard

A first-time user should understand the project within ten seconds.

## Header

Display:

- Team 3 — StudyGroup.
- Four-student project context.
- Data source.
- Last analysis time.
- Brief coverage explanation.

## Summary cards

Show:

- Contributors.
- Components.
- Components dependent on one person.
- Components with insufficient familiarity evidence.

Every value must come from real analyzer output.

## Coverage visualization

Use a compact, readable visualization showing component status.

Sort concerning components first.

Each component displays:

- Name.
- Coverage status.
- Relevant contributors.
- Evidence access.

Use icons and labels alongside colors.

## Attention needed

Show the most important inferred risks.

Example findings:

- Authentication appears dependent on Marcus.
- API Server has concentrated familiarity.
- Deployment Configuration has little recent activity.

Each finding includes:

- Explanation.
- Evidence button.
- "Investigate with Donk" action.

These findings must be derived from real analyzed data.

## Recent activity

Display recent meaningful commits and recorded Donk actions.

Do not invent project progress percentages or completion states.

Do not claim to know whether an assignment requirement is finished unless a separate verified requirements system is implemented.

---

# 11. Project Map — visual centerpiece

Create a distinctive, clean, interactive graph.

## Structure

Use a structured bipartite layout:

**Contributors on the left → project components on the right.**

Use fixed or deterministic layout coordinates by default.

Avoid chaotic force movement and overlapping labels.

## Contributor nodes

Display:

- Colored avatar.
- Initials.
- Name.
- Consistent contributor color.

## Component nodes

Display:

- Component icon.
- Component name.
- Coverage status.
- Subtle status indication.

## Connections

Edge thickness and opacity represent inferred familiarity strength.

Use curved edges with restrained styling.

Provide an understandable legend.

## Interaction

Hovering a node:

- Highlights related nodes.
- Highlights relevant edges.
- Dims unrelated graph content.

Clicking a node:

- Selects it.
- Opens an inspector.
- Shows component or contributor details.
- Provides relevant evidence and suggested actions.

Provide:

- Zoom controls.
- Fit-to-view.
- Reset selection.
- Component filtering where necessary.
- A usable solution for large graphs.

Do not hide critical information behind hover alone.

## Evidence inspector

Clicking an evidence reference opens a contextual inspector showing:

- Related files.
- Commit hashes.
- Commit messages.
- Authors.
- Dates.
- Relevant line or file evidence.

Where possible, include a source view with author-colored Git blame gutters.

Make evidence links work consistently across the dashboard, graph, and agent.

---

# 12. Signature feature — teammate absence simulation

Implement a prominent control:

**"What if someone is out?"**

Let the user choose a teammate.

Example: Marcus.

The backend runs `simulate_departure("Marcus")`.

The same deterministic function must be used by:

1. The dashboard control.
2. The Ask Donk agent tool.

Never create separate frontend simulation calculations.

## Visual transition

Animate the change over approximately 300–600 ms.

- Marcus's node fades or greys out.
- His connections disappear or fade.
- Affected components update their coverage status.
- Newly uncovered components briefly pulse.
- A concise result banner explains the change.

Example:

"If Marcus is unavailable, Authentication and API Server no longer have a contributor above the familiarity threshold."

This is an inferred knowledge-coverage scenario, not a claim that the software stops working.

Provide Reset to restore the original state.

Support reduced-motion settings.

This should be the project's most memorable visual interaction.

---

# 13. Ask Donk — AI agent

Ask Donk must be a genuine tool-using AI agent powered by Meta Model API.

It must investigate real repository data.

Do not implement a chatbot that receives a large static JSON blob and improvises answers.

## Backend tools

Implement deterministic, typed, tested tools:

### `find_code(query)`

Search real repository paths, symbols, and source content.

Return bounded candidate results with evidence identifiers.

Do not invent files or functions.

### `explain_authorship(path_or_symbol)`

Identify:

- Original meaningful author.
- Primary current maintainer.
- Most recent meaningful editor.

Include supporting commits, timestamps, and relevant Git blame results.

### `get_component_summary(component)`

Return:

- Relevant files.
- Contributors.
- Familiarity sub-signals.
- Coverage status.
- Staleness.
- Relevant evidence IDs.

### `simulate_departure(developer)`

Recompute inferred coverage after excluding a contributor.

Return affected components and deterministic metrics.

### `propose_email(recipient, subject_hint, evidence_ids)`

Create an email draft as a pending action.

**This tool must never send email.**

## Agent behavior

The model chooses which tools to call according to the user's question.

Tool results provide the facts.

The model interprets those results, explains the situation, and recommends appropriate next steps.

The model must not invent:

- File paths.
- Commit hashes.
- Contributor identities.
- Numerical metrics.
- Unverified project status.
- Email delivery results.

If evidence is insufficient, state the limitation.

---

# 14. Evidence-backed AI responses

Use structured output for factual answers.

Each claim should include:

- Claim text.
- Evidence identifiers.
- Referenced metric identifiers and exact values where relevant.

The backend verifies:

- Referenced evidence exists.
- Numerical values match computed results.
- Claims include supporting references.
- Referenced evidence belongs to the analyzed repository snapshot.

If verification fails:

1. Attempt one targeted repair.
2. Re-verify.
3. If still unsuccessful, clearly flag the claim or answer as unverified.

Do not use fragile regular expressions to extract and verify arbitrary numerical claims.

Keep the following layers distinguishable:

- Repository evidence.
- Deterministic metrics.
- AI interpretation.

Use cautious language such as:

"Repository history suggests Marcus is the primary current maintainer."

Never say:

"Marcus is definitely the only person capable of maintaining this code."

---

# 15. Ask Donk interface

The right-side panel should feel like an active assistant, not a plain text box.

## Empty state

Show contextual suggested questions.

Examples:

- "Who maintains authentication?"
- "What happens if Marcus is unavailable?"
- "Who last changed the API server?"
- "Can you ask Marcus about the session logic?"

Clicking a suggestion immediately submits it.

## Agent progress

Show real execution stages as they occur:

- Finding relevant files.
- Checking commit history.
- Analyzing contributor signals.
- Verifying evidence.
- Preparing an action.

Use server-sent events if practical.

Do not invent progress events or simulate tool calls that did not happen.

Use compact indicators rather than overwhelming technical logs.

## Answer design

Default answers should be concise.

Include:

- One-sentence headline.
- Up to three key findings.
- Clickable evidence chips.
- Evidence-strength indicator.
- Verified or Unverified status.
- Expandable technical details.
- Contextual next-action buttons.

Keep normal answers around 90 words when practical.

## Authorship answers

Use a specialized card displaying:

- Wrote it first.
- Maintains it now.
- Last touched.

For each role show:

- Contributor name.
- Avatar.
- Relevant date.
- Evidence.
- Small authorship or activity visualization where supported.

Include a compact commit timeline.

Avoid visually ranking teammates against one another.

---

# 16. Email actions — investigate, propose, approve, send

This is a defining feature of Donk.

The agent should be able to move from explaining a problem to preparing a meaningful action.

## Example interaction

User:

"Marcus is unavailable next week. Can you ask him to explain the authentication system before our demo?"

Donk:

1. Investigates authentication history.
2. Identifies the relevant contributor.
3. Retrieves supporting code evidence.
4. Drafts a concise, specific request.
5. Creates a pending action.
6. Displays an editable confirmation card.

## Confirmation card

Display:

- Recipient name.
- Actual delivery destination or clearly identified demo redirect.
- Subject.
- Editable message body.
- Relevant files and evidence.
- Send button.
- Cancel button.

Example subject:

`[Donk] Question about session authentication`

Example body:

"Hey Marcus,

I was looking through the authentication implementation in auth/session.py. Could you explain how session tokens are generated and validated, and whether there are any edge cases we should understand before the demo?

Thanks!"

Drafts should be natural, specific, and based on verified evidence.

Do not include invented claims.

## Security architecture

The model cannot send.

`propose_email` only creates a pending record.

Sending occurs through a separate backend endpoint, invoked after the user explicitly clicks Send.

For example:

`POST /api/actions/{id}/send`

The backend must verify:

- The pending action exists.
- The request is explicitly confirmed through the UI.
- The recipient belongs to an approved local roster.
- The action has not already been sent.
- The sender is permitted by the local application's confirmation mechanism.
- Rate limits and configured delivery policies are satisfied.

Do not rely exclusively on a frontend flag for authorization.

## Recipient roster

Use a local, gitignored `team.json`.

Include:

- Teammate name.
- Permitted aliases.
- Approved email address.

Never automatically use email addresses extracted from Git commits as delivery destinations.

## Email modes

### Outbox mode — default

Store approved messages locally.

No message leaves the computer.

Show status as:

"Saved to outbox"

Do not call this externally delivered.

### SMTP mode

Send email using properly configured SMTP credentials.

Only display "Sent" when the backend confirms submission to the configured mail server.

Do not imply the recipient has read or received it merely because the SMTP server accepted it.

### Demo redirect

During the demonstration, redirect outgoing messages to `DEMO_EMAIL_REDIRECT`.

Make this obvious in the confirmation UI.

Example:

"Demo mode: this email will be sent to your test inbox instead of Marcus."

## Additional protections

- One recipient per action.
- No CC/BCC.
- No attachments.
- Maximum five sends per hour.
- Idempotent confirmed send operations.
- Record proposals, approvals, cancellations, and send results.
- Never expose credentials.

---

# 17. Activity tab

Place Activity beside Ask Donk in the persistent right panel.

Do not create a separate Activity page for the MVP.

## Display

- Pending email approvals.
- Canceled drafts.
- Saved outbox messages.
- SMTP-submitted messages.
- Failed actions.
- Completed agent investigations where persisted.

Each entry includes:

- Action type.
- Description.
- Relevant teammate or component.
- Timestamp.
- Status.
- Link to details or evidence.

Do not imply that Donk tracks email replies. Reply monitoring is outside scope.

All Activity items must come from real application state.

---

# 18. End-to-end demonstration

Build the application around this complete interaction.

### Part A — understand the project

1. Open Donk.
2. See Team 3 — StudyGroup.
3. Observe the real coverage summary.
4. Open Project Map.
5. Explore Marcus and Authentication.
6. Open the relevant Git evidence.

### Part B — simulate a problem

7. Click "What if someone is out?"
8. Select Marcus.
9. Watch his graph connections fade.
10. Watch affected component statuses change.
11. Read the resulting coverage warning.

### Part C — investigate with AI

12. Ask: "If Marcus is unavailable, what should we understand before the demo?"
13. Donk calls backend tools.
14. Real tool progress appears.
15. Muse explains the evidence and relevant knowledge gaps.
16. The answer contains verified references.

### Part D — take action

17. Ask: "Can you email Marcus asking him to explain the most important authentication details?"
18. Donk prepares a relevant message.
19. The confirmation card appears.
20. The user edits the draft.
21. The user explicitly approves.
22. The backend stores the email in the outbox or sends through configured SMTP.
23. The interface shows the accurate result.
24. Activity records the action.

The complete flow must be reproducible without manual database edits or hardcoded backend answers.

---

# 19. Implementation milestones

Follow this order.

Stop after each milestone and summarize:

- What was built.
- Which files changed.
- What was tested.
- What works.
- What remains.
- Any limitations or failures.

Do not silently declare unfinished functionality complete.

## M1 — Git analyzer and data contracts

Build:

- Repository analyzer.
- Author normalization.
- Noise filtering.
- Component classification.
- Familiarity scoring.
- Coverage classification.
- Deterministic data schemas.
- Unit tests.

Deliver a working analyzer with sample machine-readable output.

Do not build the dashboard yet.

## M2 — Synthetic repository and evaluation

Build:

- Bounded synthetic repository generator.
- Team 3 demo repository.
- Ground-truth ownership configuration.
- Planted-truth evaluation.
- Baseline comparisons.
- Departure simulation.
- Authorship checks.
- Cached demo analysis snapshot.

Report the initial measured results.

This milestone establishes the factual foundation of the product.

## M3 — Dashboard and interactive project map

Build:

- Visual design system.
- Application shell.
- Overview dashboard.
- Persistent agent panel layout.
- React Flow project map.
- Node selection and highlighting.
- Evidence inspector.
- Coverage statuses.
- Departure animation.

Use actual analyzer data from M2.

Do not independently hardcode the displayed metrics.

After implementation, capture screenshots at 1440×900 and 1920×1080 using Playwright.

Inspect and correct:

- Overlapping elements.
- Graph label collisions.
- Truncated content.
- Scrolling problems.
- Panel sizing.
- Console errors.
- Major contrast problems.

## M4 — Muse-powered agent

Build:

- Model API service.
- Repository investigation tools.
- Tool-calling execution.
- Evidence verification.
- Structured answers.
- Agent progress indicators.
- Contextual answer cards.
- Evidence links.
- Citation-faithfulness tests.

Verify that the agent can answer the core demo questions from actual repository evidence.

## M5 — Email and action workflow

Build:

- Proposed actions.
- Pending approval cards.
- Editable email drafts.
- Local roster.
- Recipient allowlisting.
- Separate confirmed-send endpoint.
- Outbox mode.
- Activity history.
- Email safety tests.
- SMTP integration if resources permit.

Verify that no AI response can directly trigger a send.

## M6 — Final integration and polish

Complete:

- End-to-end demonstration.
- Required evaluation report.
- Integration tests.
- Final visual regression checks.
- README.
- Configuration instructions.
- Architecture documentation.
- Known limitations.
- Repeatable demo script.

Prioritize fixing failures in the core demonstration before adding any extra features.

---

# 20. UI and interaction quality standards

Every visible control must work.

Do not include:

- Fake buttons.
- Placeholder navigation.
- Hardcoded fabricated commits.
- Invented email confirmations.
- Mock AI tool progress.
- Static graphs falsely presented as analyzed results.
- Unsupported project completion percentages.
- Inaccessible contrast.
- Unnecessary decorative charts.

Include:

- Skeleton loading states.
- Helpful empty states.
- Clear error feedback.
- Keyboard focus.
- Responsive layout behavior.
- Consistent components.
- Reusable styles.
- Stable graph layout.
- Sensible animations.
- Actual backend-driven status updates.

If a feature is unavailable, clearly mark it unavailable rather than pretending it works.

---

# 21. Performance and resource discipline

Keep implementation efficient.

- Cache analyzed repository data.
- Cache Git blame results.
- Bound repository-history operations.
- Avoid unnecessary full-repository re-analysis.
- Keep React components modular.
- Avoid enormous generated source files.
- Use narrow tests during individual milestones.
- Run broader tests at milestone completion.
- Take screenshot batches at M3 and M6.
- Use additional screenshots only to resolve identified issues.
- Cache verified demonstration responses where appropriate.

Do not spend excessive time or model usage generating peripheral functionality.

The highest priority is a functioning vertical slice.

---

# 22. Final README requirements

Document:

1. Product problem and student audience.
2. Technical architecture.
3. Frontend and backend setup.
4. Environment variables.
5. Meta Model API integration.
6. Repository analyzer behavior.
7. Synthetic repo generation.
8. Familiarity scoring.
9. Departure simulation.
10. Citation verification.
11. Email confirmation and delivery safety.
12. Evaluation methodology and measured results.
13. How to reproduce the demonstration.
14. Known limitations.

Include the following conceptual limitations explicitly:

- Git history does not establish actual human understanding.
- Some teams commit through shared accounts.
- Co-authorship is imperfectly represented.
- File-level authorship may not reflect design contributions.
- Small repositories can produce noisy signals.
- Synthetic evaluation cannot validate real team dynamics.
- Donk is not intended for grading, employment decisions, or measuring individual effort.

---

# 23. Definition of done

Donk is finished when:

- The demo project is generated from real Git commits.
- The analyzer produces reproducible metrics.
- The dashboard displays those metrics accurately.
- The graph responds to user interactions.
- Departure simulation updates the graph using backend calculations.
- Muse answers repository questions using real tools.
- Answers can be traced to verified evidence.
- The user can approve and execute an email action.
- Delivery or outbox status is reported accurately.
- Activity records the result.
- Required evaluation tests execute.
- The complete demonstration works without manual intervention.

A visually impressive application with fabricated backend behavior is not complete.

A technically correct backend with a confusing or unfinished interface is also not complete.

Both must work together.

---

# 24. Begin implementation

First, inspect the existing repository and any earlier Donk specifications.

Then:

1. Summarize the current codebase.
2. Identify reusable components.
3. Present the proposed architecture.
4. Identify conflicts or missing dependencies.
5. Confirm the implementation milestones.
6. Begin M1 immediately.

Do not ask for confirmation between milestones unless a genuinely blocking choice or credential is required. Otherwise, use sensible documented defaults.

At each milestone boundary, provide the required summary before continuing. Pause only if explicitly required by the available execution environment or by a blocking issue.

**Final objective: build Donk as a genuinely useful, visually memorable AI agent for student software teams, with measurable functionality, transparent evidence, and real user-approved actions.**
