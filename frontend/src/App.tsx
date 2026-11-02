import { useEffect, useRef, useState } from 'react';
import type { Answer, AskEvent, DraftAction, Overview, RepoMapData, Status } from './api/types';
import { askDonk, fetchAction, fetchEvidence, fetchOverview, fetchRepoMap, fetchStatus, proposeEmail } from './api/client';
import { filesFromEvents } from './utils/evidence';
import { repoName } from './utils/repo';
import Timeline from './components/dashboard/Timeline';
import Results from './components/dashboard/Results';
import Graph from './components/dashboard/Graph';
import EmailCard from './components/dashboard/EmailCard';
import AskBox from './components/dashboard/AskBox';
import EmailPrompt from './components/dashboard/EmailPrompt';
import History from './components/dashboard/History';
import AnswerSkeleton from './components/dashboard/AnswerSkeleton';
import OverviewCard from './components/dashboard/OverviewCard';
import Inspector from './components/evidence/Inspector';
import Activity from './components/activity/Activity';
import Sidebar from './components/layout/Sidebar';
import MobileNav from './components/layout/MobileNav';
import CommandPalette from './components/command/CommandPalette';
import Repositories from './components/repos/Repositories';
import PageHeader from './components/ui/PageHeader';
import type { Page } from './components/layout/navigation';

export default function App() {
  const [status, setStatus] = useState<Status | null>(null);
  const [statusError, setStatusError] = useState<string | null>(null);
  const [overview, setOverview] = useState<Overview | null>(null);
  const [repoMap, setRepoMap] = useState<RepoMapData | null>(null);
  const [mapError, setMapError] = useState(false);
  const [question, setQuestion] = useState('');
  const [asking, setAsking] = useState(false);
  const [events, setEvents] = useState<AskEvent[]>([]);
  const [answer, setAnswer] = useState<Answer | null>(null);
  const [askError, setAskError] = useState<string | null>(null);
  const [liveFiles, setLiveFiles] = useState<string[]>([]);
  const [inspectId, setInspectId] = useState<string | null>(null);
  const [inspectData, setInspectData] = useState<Record<string, unknown> | null>(null);
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [draft, setDraft] = useState<DraftAction | null>(null);
  const [draftFor, setDraftFor] = useState<string | null>(null);
  const [draftQuestion, setDraftQuestion] = useState('');
  const [draftBusy, setDraftBusy] = useState(false);
  const [draftError, setDraftError] = useState<string | null>(null);
  const [activityKey, setActivityKey] = useState(0);
  const [historyKey, setHistoryKey] = useState(0);
  const [page, setPage] = useState<Page>('dashboard');
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const draftBoxRef = useRef<HTMLDivElement>(null);

  function refreshRepoContext() {
    fetchStatus().then(setStatus).catch((e) => setStatusError(e instanceof Error ? e.message : 'unreachable'));
    fetchOverview().then(setOverview).catch(() => {});
    setMapError(false);
    fetchRepoMap().then(setRepoMap).catch(() => setMapError(true));
    setAnswer(null);
    setEvents([]);
    setLiveFiles([]);
    setDraft(null);
    setDraftFor(null);
    setAskError(null);
  }

  useEffect(() => {
    refreshRepoContext();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        setPaletteOpen((v) => !v);
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  // Open the email prompt for the main contributor as soon as an answer names someone,
  // so the box is visible without discovering the per-card Ask button first.
  useEffect(() => {
    if (!answer) return;
    const cards = answer.contributors ?? [];
    const main = cards.find((c) => c.is_main)?.name ?? cards[0]?.name ?? answer.contributor_names[0];
    if (main) {
      setDraftFor(main);
      setDraftQuestion(answer.suggested_question ?? '');
    }
  }, [answer]);

  // Bring the prompt box into view whenever it opens for someone new.
  useEffect(() => {
    if (!draftFor) return;
    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    draftBoxRef.current?.scrollIntoView({ behavior: reduced ? 'auto' : 'smooth', block: 'nearest' });
  }, [draftFor]);

  async function runAsk(q: string) {
    const query = q.trim();
    if (!query || asking) return;
    setAsking(true);
    setAskError(null);
    setAnswer(null);
    setEvents([]);
    setLiveFiles([]);
    setDraft(null);
    setDraftFor(null);
    const collected: AskEvent[] = [];
    try {
      for await (const e of askDonk(query)) {
        if (e.type === 'answer') setAnswer(e.answer);
        else if (e.type === 'error') setAskError(e.detail);
        else if (e.type !== 'done') {
          collected.push(e);
          setEvents([...collected]);
          setLiveFiles(filesFromEvents(collected));
        }
      }
    } catch (e) {
      setAskError(e instanceof Error ? e.message : 'request failed');
    } finally {
      setAsking(false);
      setHistoryKey((k) => k + 1);
    }
  }

  async function openEvidence(id: string) {
    try {
      const data = await fetchEvidence(id);
      setInspectId(id);
      setInspectData(data);
    } catch (e) {
      setAskError(e instanceof Error ? e.message : 'evidence failed');
    }
  }

  async function resumeDraft(id: string) {
    const d = await fetchAction(id);
    if (d.status !== 'pending') throw new Error(`Draft is ${d.status}, cannot resume`);
    setDraft(d);
    setDraftFor(null);
    setPage('dashboard');
  }

  async function startDraft(contributor: string, suggested: boolean) {
    if (!answer) return;
    setDraftBusy(true);
    setDraftError(null);
    try {
      const d = await proposeEmail({
        contributor,
        question: suggested ? '' : draftQuestion,
        scope: answer.scope ?? '',
        evidence_ids: answer.evidence_ids ?? [],
        suggested,
      });
      setDraft(d);
      setDraftFor(null);
    } catch (e) {
      setDraftError(e instanceof Error ? e.message : 'draft failed');
    } finally {
      setDraftBusy(false);
    }
  }

  return (
    <div className="relative flex min-h-screen bg-ink-950 text-slate-900">
      <div className="app-grid pointer-events-none absolute inset-x-0 top-0 h-[34rem]" aria-hidden="true" />
      {/* Sidebar */}
      <Sidebar page={page} onNavigate={setPage} status={status} statusError={statusError} />

      {/* Main */}
      <main className="relative mx-auto w-full max-w-5xl flex-1 px-4 py-8 sm:px-8 lg:px-10">
        <MobileNav page={page} onNavigate={setPage} />
        {page === 'dashboard' ? (
          <>
            <PageHeader
              eyebrow="Workspace"
              title="Dashboard"
              description="Ask who wrote, changed, or knows any part of this codebase."
            />
            <div className="mt-4">
              <AskBox
                question={question}
                onQuestionChange={setQuestion}
                asking={asking}
                status={status}
                inputRef={inputRef}
                onAsk={runAsk}
                repoLabel={repoName(status?.repo.path)}
                onRepoClick={() => setPage('repos')}
                onOpenPalette={() => setPaletteOpen(true)}
              />
            </div>
            {draft && !answer && (
              <div className="mt-4">
                <div className="mb-1 text-xs text-slate-500">Resumed draft from Activity</div>
                <EmailCard key={draft.id} draft={draft} onDone={() => setActivityKey((k) => k + 1)} onCancel={() => setDraft(null)} />
              </div>
            )}
            <History refreshKey={historyKey} onRerun={(q) => { setQuestion(q); runAsk(q); }} />
            {overview && (
              <div className="mt-4">
                <OverviewCard
                  overview={overview}
                  status={status}
                  repoMap={repoMap}
                  mapError={mapError}
                  scope={answer?.scope ?? null}
                  liveFiles={liveFiles}
                  onEvidence={openEvidence}
                />
              </div>
            )}

        {askError && (
          <div className="mt-4 rounded-lg border border-red-900 bg-red-950 p-4 text-sm text-red-200">{askError}</div>
        )}

        {(events.length > 0 || asking) && (
          <div className="mt-4">
            <Timeline events={events} live={asking} />
          </div>
        )}

        {asking && !answer && <AnswerSkeleton />}

        {answer && (
          <div className="mt-4 space-y-4">
            <Results answer={answer} onEvidence={openEvidence} onAsk={(n) => { setDraftFor(n); setDraftQuestion(answer.suggested_question ?? ''); }} />

            {draftFor && (!draft || draft.contributor !== draftFor) && (
              <EmailPrompt
                draftFor={draftFor}
                draftQuestion={draftQuestion}
                onDraftQuestionChange={setDraftQuestion}
                draftBusy={draftBusy}
                draftError={draftError}
                onPrepare={(suggested) => startDraft(draftFor, suggested)}
                onCancel={() => setDraftFor(null)}
                boxRef={draftBoxRef}
              />
            )}

            {draft && (
              <EmailCard key={draft.id} draft={draft} onDone={() => setActivityKey((k) => k + 1)} onCancel={() => setDraft(null)} />
            )}

            <Graph answer={answer} liveFiles={liveFiles} onEvidence={openEvidence} />
          </div>
        )}

          </>
        ) : page === 'activity' ? (
          <div>
            <PageHeader
              eyebrow="Workspace"
              title="Activity"
              description="Drafts, sends, and delivery history — resume or discard pending drafts."
            />
            <div className="mt-4">
              <Activity refreshKey={activityKey} onResume={resumeDraft} />
            </div>
          </div>
        ) : (
          <div>
            <PageHeader
              eyebrow="Workspace"
              title="Repositories"
              description="Switch which repository Donk investigates — no restart needed."
            />
            <div className="mt-4">
              <Repositories onSwitched={refreshRepoContext} />
            </div>
          </div>
        )}

        <footer className="mt-6 text-xs leading-relaxed text-slate-600">
          Git history shows activity, not understanding. Donk names main contributors from surviving lines and recent
          commits — never official owners. Reference checks confirm citations resolve; they don't prove every
          interpretation.
        </footer>
      </main>

      {inspectId && <Inspector evidence={inspectData} onClose={() => { setInspectId(null); setInspectData(null); }} />}
      <CommandPalette
        open={paletteOpen}
        onClose={() => setPaletteOpen(false)}
        onAsk={(q) => {
          setPaletteOpen(false);
          setPage('dashboard');
          setQuestion(q);
          runAsk(q);
        }}
        onNavigate={setPage}
        onSwitched={refreshRepoContext}
      />
    </div>
  );
}

