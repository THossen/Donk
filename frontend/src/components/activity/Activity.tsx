import { useEffect, useState } from 'react';
import { Inbox, MailOpen, RefreshCw } from 'lucide-react';
import { fetchActivity } from '../../api/client';
import { timeAgo } from '../../utils/time';
import Card from '../ui/Card';
import IconButton from '../ui/IconButton';
import Pill from '../ui/Pill';

export default function Activity({ refreshKey }: { refreshKey: number }) {
  const [actions, setActions] = useState<Record<string, unknown>[]>([]);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    try {
      const r = await fetchActivity();
      setActions(r.actions);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'failed');
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [refreshKey]);

  return (
    <Card pad="sm">
      <div className="mb-2 flex items-center justify-between">
        <div className="flex items-center gap-2 text-sm font-medium text-slate-200">
          <Inbox size={15} /> Activity
        </div>
        <IconButton label="Refresh activity" onClick={load} className="text-slate-400 hover:text-slate-100">
          <RefreshCw size={14} />
        </IconButton>
      </div>
      {error && <div className="text-sm text-red-300">{error}</div>}
      {actions.length === 0 && !error && (
        <div className="flex flex-col items-center py-6 text-center">
          <span className="flex h-10 w-10 items-center justify-center rounded-full bg-ink-800 text-slate-400">
            <MailOpen size={18} />
          </span>
          <div className="mt-2 text-sm font-medium">No email actions yet</div>
          <div className="mt-0.5 text-[13px] text-slate-500">
            Ask Donk about the code, then ask a contributor.
          </div>
        </div>
      )}
      <ul className="space-y-2">
        {actions.map((a) => (
          <li key={String(a.id)} className="rounded-lg bg-ink-850 px-3 py-2 text-[13px]">
            <div className="flex items-center justify-between gap-2">
              <span className="font-medium text-slate-100">Email to {String(a.contributor)}</span>
              <StatusPill status={String(a.status)} />
            </div>
            <div className="mt-0.5 truncate text-slate-400">{String(a.subject)}</div>
            <div className="mt-0.5 font-mono text-xs text-slate-500">
              delivers to {String(a.delivers_to)} · {String(a.human_status ?? a.status)}
              {typeof a.created_at === 'number' && timeAgo(a.created_at) ? ` · ${timeAgo(a.created_at)}` : ''}
            </div>
          </li>
        ))}
      </ul>
    </Card>
  );
}

function StatusPill({ status }: { status: string }) {
  const tone =
    status === 'sent'
      ? 'teal'
      : status === 'outbox_saved'
        ? 'sky'
        : status === 'failed'
          ? 'red'
          : ('gray' as const);
  return <Pill tone={tone}>{status}</Pill>;
}
