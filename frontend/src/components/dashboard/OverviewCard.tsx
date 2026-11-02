import { Folder, GitCommitHorizontal } from 'lucide-react';
import type { Overview, RepoMapData, Status } from '../../api/types';
import { repoName } from '../../utils/repo';
import { timeAgo } from '../../utils/time';
import RepoMap from '../repos/RepoMap';
import Card from '../ui/Card';

export default function OverviewCard({
  overview,
  status,
  repoMap,
  mapError,
  scope,
  liveFiles,
  onEvidence,
}: {
  overview: Overview;
  status: Status | null;
  repoMap: RepoMapData | null;
  mapError: boolean;
  scope: string | null;
  liveFiles: string[];
  onEvidence: (id: string) => void;
}) {
  return (
    <Card>
      <div className="flex items-center gap-2 text-sm font-medium text-slate-200">
        <Folder size={15} className="text-teal-300" /> {repoName(status?.repo.path)}
        <span className="font-mono text-xs font-normal tabular-nums text-slate-500">
          {overview.tracked_total.toLocaleString()} tracked files
        </span>
      </div>
      <div className="mt-3">
        {repoMap ? (
          <RepoMap data={repoMap} scope={scope} hitPaths={liveFiles} rootLabel={repoName(status?.repo.path)} />
        ) : mapError ? (
          <div className="flex flex-wrap gap-x-4 gap-y-1 font-mono text-xs text-slate-400">
            {overview.top_dirs.slice(0, 6).map(([d, n]) => (
              <span key={d}>
                {d}/ <span className="text-slate-500">{n.toLocaleString()}</span>
              </span>
            ))}
          </div>
        ) : (
          <div className="h-60 animate-pulse rounded-lg bg-ink-850" aria-label="Loading repository map" />
        )}
      </div>
      <ul className="mt-2 space-y-1">
        {overview.recent_commits.slice(0, 3).map((c) => (
          <li key={c.sha}>
            <button
              onClick={() => onEvidence(c.evidence_id)}
              className="flex w-full items-center gap-2 truncate rounded px-1 py-0.5 text-left text-[13px] text-slate-300 hover:bg-ink-800"
            >
              <GitCommitHorizontal size={13} className="shrink-0 text-slate-500" />
              <span className="shrink-0 font-mono text-xs text-teal-200">{c.sha.slice(0, 8)}</span>
              <span className="truncate">{c.subject}</span>
              <span className="ml-auto shrink-0 text-xs text-slate-500" title={c.date}>{c.author} · {timeAgo(c.date)}</span>
            </button>
          </li>
        ))}
      </ul>
    </Card>
  );
}
