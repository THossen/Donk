import { useEffect, useState } from 'react';
import { AlertTriangle, CheckCircle2, ChevronDown, ChevronRight, Loader2, RotateCcw, Wrench, XCircle } from 'lucide-react';
import type { AskEvent } from '../../api/types';
import { filesFromEvents } from '../../utils/evidence';
import Button from '../ui/Button';
import Card from '../ui/Card';

export type RunStatus = 'live' | 'complete' | 'partial' | 'failed';

const PHASE_LABEL: Record<string, string> = {
  starting: 'Starting investigation',
  finding_files: 'Finding relevant files',
  checking_history: 'Checking commit history',
  asking_model: 'Asking Muse',
  no_model_key: 'No model key — local analysis',
  verifying: 'Verifying evidence',
};

function humanizeTool(name: string, summary: string): string {
  if (name === 'search_files') {
    const q = summary.replace(/^search\s+/, '').replace(/^['"]|['"]$/g, '');
    return q ? `Searching for \u201c${q}\u201d…` : 'Searching the codebase…';
  }
  if (name === 'read_snippet') return summary ? `Reading ${summary}…` : 'Reading code…';
  if (name === 'git_log') {
    const p = summary.replace(/^history\s+/, '');
    return p && p !== '(repo)' ? `Checking history of ${p}…` : 'Checking commit history…';
  }
  if (name === 'explain_authorship') {
    const p = summary.replace(/^authorship\s+/, '');
    return p ? `Comparing contributions in ${p}…` : 'Comparing contributions…';
  }
  return summary || name;
}

/** Plain-language read of what the investigation is doing right now. */
function liveSentence(events: AskEvent[]): string {
  const items = events.filter((e) => e.type === 'stage' || e.type === 'tool');
  const last = items[items.length - 1];
  if (last?.type === 'tool') return humanizeTool(last.name, last.summary);
  if (last?.type === 'stage') return `${PHASE_LABEL[last.phase] ?? last.phase}…`;
  return 'Starting investigation…';
}

export default function Timeline({
  events,
  status,
  stopped,
  onRetry,
}: {
  events: AskEvent[];
  status: RunStatus;
  stopped: boolean;
  onRetry: () => void;
}) {
  const [expanded, setExpanded] = useState(false);
  useEffect(() => {
    if (status === 'live') setExpanded(false);
    if (status === 'failed') setExpanded(true);
  }, [status]);

  const items = events.filter((e) => e.type === 'stage' || e.type === 'tool' || e.type === 'result');
  if (items.length === 0 && status !== 'live') return null;
  const toolCount = items.filter((e) => e.type === 'tool').length;
  const fileCount = filesFromEvents(events).length;
  const counts =
    toolCount > 0 || fileCount > 0
      ? ` · ${toolCount} call${toolCount === 1 ? '' : 's'} · ${fileCount} file${fileCount === 1 ? '' : 's'}`
      : '';

  return (
    <Card pad="sm" flat>
      <div className="flex w-full items-center gap-2 px-1 py-0.5">
        {status === 'live' && <Loader2 size={15} className="shrink-0 animate-spin text-teal-300" />}
        {status === 'complete' && <CheckCircle2 size={15} className="shrink-0 text-teal-300" />}
        {status === 'partial' && <AlertTriangle size={15} className="shrink-0 text-amber-300" />}
        {status === 'failed' && <XCircle size={15} className="shrink-0 text-red-300" />}
        <div className="min-w-0 text-sm font-medium text-slate-200">
          {status === 'live' && <span>{liveSentence(events)}</span>}
          {status === 'complete' && <span>Investigation complete</span>}
          {status === 'partial' && <span>{stopped ? 'Stopped early' : 'Ended without an answer'}</span>}
          {status === 'failed' && <span>Investigation failed</span>}
          <span className="font-normal text-slate-500">{counts}</span>
        </div>
        {(status === 'partial' || status === 'failed') && (
          <Button variant="secondary" size="sm" onClick={onRetry} className="ml-2 flex shrink-0 items-center gap-1.5 text-slate-200">
            <RotateCcw size={13} /> Retry
          </Button>
        )}
        <button
          onClick={() => setExpanded((v) => !v)}
          aria-expanded={expanded}
          aria-label={expanded ? 'Hide technical details' : 'Show technical details'}
          className="ml-auto shrink-0 rounded p-1 text-slate-400 hover:bg-ink-850 hover:text-slate-200"
        >
          {expanded ? <ChevronDown size={15} /> : <ChevronRight size={15} />}
        </button>
      </div>
      {(status === 'partial' || status === 'failed') && (
        <div className="px-1 text-[13px] text-slate-500">
          {status === 'partial' ? 'Showing partial progress.' : 'The error is shown above; technical details may help diagnose it.'}
        </div>
      )}
      {expanded && (
        <ol className="mt-2 space-y-1.5 border-t border-ink-700 pt-2">
          {items.map((e, i) => {
            if (e.type === 'stage') {
              return (
                <li key={i} className="flex items-baseline gap-2 text-sm">
                  <span className="font-medium text-slate-100">{PHASE_LABEL[e.phase] ?? e.phase}</span>
                  {e.detail && <span className="truncate text-[13px] text-slate-400">{e.detail}</span>}
                </li>
              );
            }
            if (e.type === 'tool') {
              return (
                <li key={i} className="flex items-center gap-2 font-mono text-[13px] text-slate-300">
                  <Wrench size={13} className="shrink-0 text-teal-300" />
                  <span>{e.name}</span>
                  <span className="truncate text-slate-400">{e.summary}</span>
                </li>
              );
            }
            return (
              <li key={i} className="pl-5 font-mono text-xs text-slate-500">
                {e.error ? (
                  <span className="text-amber-300">tool error: {e.error}</span>
                ) : (
                  <span>
                    {e.name} → {e.evidence_ids.length} evidence ref{e.evidence_ids.length === 1 ? '' : 's'}
                  </span>
                )}
              </li>
            );
          })}
        </ol>
      )}
    </Card>
  );
}
