import { Database, GitBranch } from 'lucide-react';
import type { Status } from '../../api/types';
import { repoName } from '../../utils/repo';
import { timeAgo } from '../../utils/time';

export default function RepoStatus({ status, error }: { status: Status | null; error: string | null }) {
  if (error) return <div className="text-red-300">Backend unreachable ({error})</div>;
  if (!status) return <div className="text-slate-500">Loading repo…</div>;
  if (status.repo.error) return <div className="text-amber-200">Repo: {status.repo.error}</div>;
  return (
    <div className="space-y-1.5">
      <div className="mb-2 text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-400">Connected repository</div>
      <div className="flex items-center gap-1.5 font-medium text-slate-300">
        <Database size={13} /> {repoName(status.repo.path)}
      </div>
      <div className="flex items-center gap-1.5 font-mono text-[11px]">
        <GitBranch size={12} /> {status.repo.head_short} · <span title={status.repo.head_date}>{timeAgo(status.repo.head_date)}</span>
      </div>
      <div className="truncate text-[11px]" title={status.repo.head_subject}>
        {status.repo.head_subject}
      </div>
      <div className="text-[11px]">
        {status.demo_mode ? 'Demo mode · ' : ''}{status.email_mode === 'smtp' ? 'SMTP sending' : 'Outbox (no external mail)'}
      </div>
    </div>
  );
}
