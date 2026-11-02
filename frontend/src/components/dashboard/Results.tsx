import { BadgeCheck, BadgeAlert, FileText, GitCommitHorizontal, Mail } from 'lucide-react';
import type { Answer } from '../../api/types';
import { colorFor, initials, textOnColor } from '../../utils/colors';
import { shortEvidence } from '../../utils/evidence';
import { timeAgo } from '../../utils/time';
import Button from '../ui/Button';
import Card from '../ui/Card';
import Pill from '../ui/Pill';

export default function Results({
  answer,
  onEvidence,
  onAsk,
}: {
  answer: Answer;
  onEvidence: (id: string) => void;
  onAsk: (name: string) => void;
}) {
  const verified = answer.verification?.verified ?? false;
  const contributors = answer.contributors ?? [];
  const maxLines = Math.max(1, ...contributors.map((c) => c.surviving_lines));
  return (
    <div className="space-y-4">
      <Card>
        <div className="flex items-start justify-between gap-3">
          <h2 className="text-xl font-semibold leading-snug tracking-tight text-slate-50">{answer.headline}</h2>
          <Pill
            tone={verified ? 'teal' : 'amber'}
            size="md"
            title="Verification confirms cited references resolve against the analyzed snapshot. It does not prove every AI interpretation."
            className="flex shrink-0 items-center gap-1"
          >
            {verified ? <BadgeCheck size={14} /> : <BadgeAlert size={14} />}
            {verified ? 'Verified refs' : 'Unverified'}
          </Pill>
        </div>
        {answer.findings.length > 0 && (
          <ul className="mt-3 list-disc space-y-1 pl-5 text-[15px] leading-relaxed text-slate-200">
            {answer.findings.map((f, i) => (
              <li key={i}>{f}</li>
            ))}
          </ul>
        )}
        <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-slate-400">
          <span>{answer.model_used ? 'Investigated by Muse' : 'Deterministic local analysis (no model key)'}</span>
          {answer.repaired && <span>· repaired once after verification</span>}
          {answer.scope !== undefined && answer.scope !== '' && (
            <span className="font-mono">· scope: {answer.scope}</span>
          )}
        </div>
        {answer.evidence_ids.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-2">
            {answer.evidence_ids.map((id) => (
              <button
                key={id}
                onClick={() => onEvidence(id)}
                className="flex items-center gap-1.5 rounded-full border border-ink-700 bg-ink-850 px-2.5 py-1 font-mono text-xs text-teal-200 hover:border-teal-700 hover:bg-ink-800"
              >
                {id.startsWith('c:') ? <GitCommitHorizontal size={13} /> : <FileText size={13} />}
                {shortEvidence(id)}
              </button>
            ))}
          </div>
        )}
        {answer.original_author && (
          <div className="mt-4 grid grid-cols-1 gap-2 text-sm sm:grid-cols-3">
            <RoleSmall label="Wrote it first" name={answer.original_author} />
            <RoleSmall label="Main contributor" name={answer.contributors?.find((c) => c.is_main)?.name ?? answer.contributor_names[0]} />
            <RoleSmall label="Last touched" name={answer.most_recent_contributor} />
          </div>
        )}
      </Card>

      {(answer.contributors ?? []).length === 0 && answer.contributor_names.length > 0 && (
        <div className="rounded-lg border border-ink-700 bg-ink-900 p-4">
          <div className="text-sm font-medium text-slate-200">Contributors named in this answer</div>
          <div className="mt-2 flex flex-wrap gap-2">
            {answer.contributor_names.map((n) => (
              <Button key={n} variant="accent" size="sm" onClick={() => onAsk(n)} className="flex items-center gap-1.5">
                <Mail size={13} /> Ask {n}
              </Button>
            ))}
          </div>
        </div>
      )}

      {contributors.length > 0 && (
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
          {contributors.map((c) => (
            <div key={c.name} className="rounded-lg border border-ink-700 bg-ink-900 p-4">
              <div className="flex items-center gap-3">
                <span
                  className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full text-sm font-bold"
                  style={{ backgroundColor: colorFor(c.name), color: textOnColor(colorFor(c.name)) }}
                >
                  {initials(c.name)}
                </span>
                <div className="min-w-0">
                  <div className="truncate font-semibold text-slate-50">{c.name}</div>
                  <div className="text-xs text-slate-400">
                    {c.is_main ? 'Main contributor' : 'Also contributed'}
                    {answer.original_author === c.name && ' · wrote it first'}
                    {answer.most_recent_contributor === c.name && ' · last touched'}
                  </div>
                </div>
                <Button variant="accent" size="sm" onClick={() => onAsk(c.name)} className="ml-auto flex shrink-0 items-center gap-1.5">
                  <Mail size={13} /> Ask
                </Button>
              </div>
              <div
                className="mt-3 h-1.5 overflow-hidden rounded-full bg-ink-800"
                title={`${c.surviving_lines.toLocaleString()} surviving lines`}
                role="img"
                aria-label={`${c.name}: ${c.surviving_lines.toLocaleString()} surviving lines`}
              >
                <div
                  className="h-full rounded-full"
                  style={{ width: `${Math.max(4, (c.surviving_lines / maxLines) * 100)}%`, backgroundColor: colorFor(c.name) }}
                />
              </div>
              <dl className="mt-3 grid grid-cols-3 gap-2 text-center">
                <Stat label="surviving lines" value={String(c.surviving_lines)} />
                <Stat label="commits" value={String(c.commits)} />
                <Stat label="last active" value={c.last_date ? timeAgo(c.last_date) : '—'} title={c.last_date ?? undefined} />
              </dl>
              {c.files.length > 0 && (
                <div className="mt-2 truncate font-mono text-xs text-slate-400" title={c.files.join('\n')}>
                  {c.files.slice(0, 3).join(', ')}
                  {c.files.length > 3 && ` +${c.files.length - 3} more`}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function RoleSmall({ label, name }: { label: string; name?: string | null }) {
  return (
    <div className="rounded-lg bg-ink-850 px-3 py-2">
      <div className="text-[11px] font-medium uppercase tracking-wide text-slate-500">{label}</div>
      <div className="truncate text-sm font-medium text-slate-100">{name ?? '—'}</div>
    </div>
  );
}

function Stat({ label, value, title }: { label: string; value: string; title?: string }) {
  return (
    <div className="rounded-lg bg-ink-850 px-2 py-1.5" title={title}>
      <div className="font-mono text-sm font-medium tabular-nums text-slate-100">{value}</div>
      <div className="text-[11px] text-slate-500">{label}</div>
    </div>
  );
}
