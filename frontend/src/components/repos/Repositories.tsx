import { useEffect, useState } from 'react';
import { CheckCircle2, FolderGit2, RefreshCw } from 'lucide-react';
import type { RepoEntry } from '../../api/types';
import { fetchRepos, selectRepo } from '../../api/client';
import Card from '../ui/Card';
import IconButton from '../ui/IconButton';
import Pill from '../ui/Pill';
import Button from '../ui/Button';
import { formatCompact } from '../../utils/format';
import { timeAgo } from '../../utils/time';

export default function Repositories({ onSwitched }: { onSwitched: () => void }) {
  const [repos, setRepos] = useState<RepoEntry[] | null>(null);
  const [truncated, setTruncated] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [switching, setSwitching] = useState<string | null>(null);

  async function load() {
    try {
      const r = await fetchRepos();
      setRepos(r.repos);
      setTruncated(r.truncated);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'failed');
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function switchTo(name: string) {
    setSwitching(name);
    setError(null);
    try {
      await selectRepo(name);
      await load();
      onSwitched();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'switch failed');
    } finally {
      setSwitching(null);
    }
  }

  return (
    <Card pad="sm">
      <div className="mb-2 flex items-center justify-between">
        <div className="flex items-center gap-2 text-sm font-medium">
          <FolderGit2 size={15} /> Available repositories
        </div>
        <IconButton label="Refresh repositories" onClick={load}>
          <RefreshCw size={14} />
        </IconButton>
      </div>
      {error && (
        <div className="mb-2 flex items-center justify-between gap-2 rounded-lg bg-red-950 px-3 py-2 text-sm text-red-300">
          <span className="truncate">{error}</span>
          <Button variant="secondary" size="sm" onClick={load} className="shrink-0 text-slate-200">
            Retry
          </Button>
        </div>
      )}
      {repos === null && !error && (
        <div className="animate-pulse space-y-3 py-2" aria-label="Loading repositories">
          {[0, 1].map((i) => (
            <div key={i} className="flex items-center gap-3">
              <div className="h-4 w-32 rounded bg-ink-800" />
              <div className="h-4 flex-1 rounded bg-ink-850" />
            </div>
          ))}
        </div>
      )}
      <ul className="divide-y divide-ink-700">
        {(repos ?? []).map((r) => (
          <li key={r.name} className="flex items-center gap-3 py-3">
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2">
                <span className="truncate text-sm font-semibold">{r.name}</span>
                {r.active && (
                  <Pill tone="teal" className="flex shrink-0 items-center gap-1">
                    <CheckCircle2 size={12} /> Current
                  </Pill>
                )}
              </div>
              <div className="mt-0.5 truncate font-mono text-xs">{r.path}</div>
              {r.error ? (
                <div className="mt-0.5 text-[13px] text-red-300">{r.error}</div>
              ) : (
                <div className="mt-0.5 truncate text-[13px]">
                  <span className="font-mono text-xs">{r.head_short}</span> {r.head_subject}
                  <span title={r.tracked_total != null ? `${r.tracked_total.toLocaleString()} files` : undefined}>
                    {' '}· {r.tracked_total != null ? formatCompact(r.tracked_total) : '?'} files
                  </span>
                  <span title={r.head_date}> · {timeAgo(r.head_date)}</span>
                </div>
              )}
            </div>
            {!r.active && !r.error && (
              <button
                onClick={() => switchTo(r.name)}
                disabled={switching !== null}
                className="shrink-0 rounded-lg border border-ink-700 px-3 py-1.5 text-sm font-medium hover:bg-ink-800 disabled:opacity-50"
              >
                {switching === r.name ? 'Switching…' : 'Switch'}
              </button>
            )}
          </li>
        ))}
      </ul>
      {truncated && <div className="mt-2 text-xs">Showing the first 20 — more repositories exist next to the configured one.</div>}
    </Card>
  );
}
