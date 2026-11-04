import { useEffect } from 'react';
import { X } from 'lucide-react';
import { colorFor } from '../../utils/colors';
import { shortEvidence } from '../../utils/evidence';
import { shortPath } from '../../utils/repo';
import { timeAgo } from '../../utils/time';
import IconButton from '../ui/IconButton';
import Pill from '../ui/Pill';

export default function Inspector({
  evidence,
  closing,
  onClose,
}: {
  evidence: Record<string, unknown> | null;
  closing: boolean;
  onClose: () => void;
}) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  if (!evidence) return null;
  const kind = evidence.kind as string;
  const header = headerFor(evidence);
  return (
    <div className={`fixed inset-y-0 right-0 z-50 flex w-full max-w-md flex-col border-l border-ink-700 bg-ink-900 shadow-xl ${closing ? 'donk-panel-out' : 'donk-panel-in'}`}>
      <div className="flex items-center gap-2 border-b border-ink-700 px-4 py-3">
        <Pill tone={header.tone}>{header.kindLabel}</Pill>
        <div className="min-w-0 flex-1 truncate font-mono text-[13px] text-slate-200" title={header.full}>
          {header.label}
        </div>
        <IconButton label="Close evidence" onClick={onClose} className="shrink-0 text-slate-400 hover:text-slate-100">
          <X size={16} />
        </IconButton>
      </div>
      <div className="donk-scroll flex-1 overflow-auto p-4">
        {kind === 'commit' && <CommitView e={evidence} />}
        {kind === 'snippet' && <SnippetView e={evidence} />}
        {kind === 'blame' && <BlameView e={evidence} />}
      </div>
    </div>
  );
}

/** Human-readable header: kind + file/line, with the raw ID as tooltip. */
function headerFor(e: Record<string, unknown>): {
  tone: 'teal' | 'sky' | 'amber' | 'gray';
  kindLabel: string;
  label: string;
  full: string;
} {
  const kind = String(e.kind ?? '');
  const id = String(e.id ?? '');
  if (kind === 'snippet' || kind === 'blame') {
    const path = String(e.path ?? '');
    if (kind === 'blame') {
      return { tone: 'amber', kindLabel: 'blame', label: shortPath(path, 44), full: `${path} (${id})` };
    }
    const start = Number(e.start_line ?? 1);
    const shown = String(e.text ?? '').split('\n').length;
    return {
      tone: 'sky',
      kindLabel: 'snippet',
      label: `${shortPath(path, 36)}:${start}–${start + shown - 1}`,
      full: `${path}:${start} (${id})`,
    };
  }
  return { tone: 'teal', kindLabel: kind || 'evidence', label: shortEvidence(id), full: id };
}

function CommitView({ e }: { e: Record<string, unknown> }) {
  return (
    <div className="space-y-2 text-sm">
      <div className="font-medium text-slate-100">{String(e.subject)}</div>
      <dl className="space-y-1 text-[13px]">
        <Row k="sha" v={String(e.sha)} mono />
        <Row k="author" v={String(e.author)} />
        <Row k="date" v={timeAgo(String(e.date)) ? `${String(e.date)} · ${timeAgo(String(e.date))}` : String(e.date)} />
      </dl>
    </div>
  );
}

function SnippetView({ e }: { e: Record<string, unknown> }) {
  const lines = String(e.text ?? '').split('\n');
  const start = Number(e.start_line ?? 1);
  return (
    <div>
      <div className="mb-2 truncate font-mono text-xs text-slate-400" title={String(e.path)}>
        {String(e.path)}:{String(e.start_line)} · {String(e.total_lines)} lines total
        {(e.truncated as boolean) && ' · truncated'}
      </div>
      <pre className="overflow-x-auto rounded-lg bg-ink-950 p-3 font-mono text-xs leading-relaxed">
        {lines.map((l, i) => (
          <div key={i} className="flex gap-3">
            <span className="w-8 shrink-0 select-none text-right text-slate-600">{start + i}</span>
            <span className="whitespace-pre text-slate-200">{l}</span>
          </div>
        ))}
      </pre>
    </div>
  );
}

function BlameView({ e }: { e: Record<string, unknown> }) {
  const lines = (e.lines as { sha: string; author: string; text: string }[]) ?? [];
  return (
    <div>
      <div className="mb-2 truncate font-mono text-xs text-slate-400" title={String(e.path)}>{String(e.path)} · blame</div>
      <pre className="overflow-x-auto rounded-lg bg-ink-950 p-3 font-mono text-xs leading-relaxed">
        {lines.map((l, i) => (
          <div key={i} className="flex gap-2">
            <span className="w-24 shrink-0 truncate" style={{ color: colorFor(l.author) }} title={`${l.author} · ${l.sha.slice(0, 12)}`}>
              {l.author}
            </span>
            <span className="whitespace-pre text-slate-200">{l.text}</span>
          </div>
        ))}
      </pre>
      {e.rollup ? (
        <div className="mt-3 text-xs text-slate-400">
          Surviving lines:{' '}
          {Object.entries(e.rollup as Record<string, number>)
            .sort((a, b) => b[1] - a[1])
            .map(([n, c]) => `${n} ${c}`)
            .join(' · ')}
        </div>
      ) : null}
    </div>
  );
}

function Row({ k, v, mono }: { k: string; v: string; mono?: boolean }) {
  return (
    <div className="flex gap-2">
      <dt className="w-14 shrink-0 text-slate-500">{k}</dt>
      <dd className={`break-all text-slate-200 ${mono ? 'font-mono text-xs' : ''}`}>{v}</dd>
    </div>
  );
}
