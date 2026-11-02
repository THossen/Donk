import { useEffect, useState } from 'react';
import { CheckCircle2, ChevronDown, ChevronRight, Loader2, Wrench } from 'lucide-react';
import type { AskEvent } from '../../api/types';
import Card from '../ui/Card';

const PHASE_LABEL: Record<string, string> = {
  starting: 'Starting investigation',
  finding_files: 'Finding relevant files',
  checking_history: 'Checking commit history',
  asking_model: 'Asking Muse',
  no_model_key: 'No model key — local analysis',
  verifying: 'Verifying evidence',
};

export default function Timeline({ events, live }: { events: AskEvent[]; live: boolean }) {
  const [expanded, setExpanded] = useState(false);
  useEffect(() => {
    if (live) setExpanded(false);
  }, [live]);

  const items = events.filter((e) => e.type === 'stage' || e.type === 'tool' || e.type === 'result');
  if (items.length === 0) return null;
  const toolCount = items.filter((e) => e.type === 'tool').length;
  const showFull = live || expanded;

  return (
    <Card pad="sm" flat>
      {live ? (
        <div className="mb-2 flex items-center gap-2 text-sm font-medium text-slate-200">
          <Loader2 size={15} className="animate-spin text-teal-300" />
          Investigation in progress
        </div>
      ) : (
        <button
          onClick={() => setExpanded((v) => !v)}
          aria-expanded={expanded}
          className="flex w-full items-center gap-2 rounded-lg px-1 py-0.5 text-left text-sm font-medium text-slate-200 hover:bg-ink-850"
        >
          <CheckCircle2 size={15} className="shrink-0 text-teal-300" />
          Investigation complete
          <span className="font-normal text-slate-500">
            · {toolCount} tool call{toolCount === 1 ? '' : 's'}
          </span>
          <span className="ml-auto text-slate-400">
            {expanded ? <ChevronDown size={15} /> : <ChevronRight size={15} />}
          </span>
        </button>
      )}
      {showFull && (
        <ol className="mt-1 space-y-1.5">
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
