import { FolderGit2 } from 'lucide-react';
import type { Overview, Status } from '../../api/types';
import { repoName } from '../../utils/repo';
import { timeAgo } from '../../utils/time';

/** One-line repo context: what is being investigated, at which HEAD. */
export default function RepoStrip({
  overview,
  status,
  onRepoClick,
}: {
  overview: Overview;
  status: Status | null;
  onRepoClick: () => void;
}) {
  const head = overview.head;
  return (
    <button
      onClick={onRepoClick}
      title="Switch repository"
      className="flex w-full items-center gap-2 rounded-lg border border-ink-700 bg-ink-900 px-3 py-2 text-left text-[13px] hover:bg-ink-850"
    >
      <FolderGit2 size={14} className="shrink-0 text-teal-300" />
      <span className="truncate font-medium text-slate-200">{repoName(status?.repo.path)}</span>
      <span className="shrink-0 font-mono text-xs tabular-nums text-slate-500">
        {overview.tracked_total.toLocaleString()} files
      </span>
      <span
        className="hidden min-w-0 flex-1 truncate text-slate-500 sm:block"
        title={`${head.sha} · ${head.author} · ${head.date}`}
      >
        <span className="font-mono text-xs text-teal-200">{head.sha.slice(0, 8)}</span>{' '}
        {head.subject} · {head.author} · {timeAgo(head.date)}
      </span>
    </button>
  );
}
