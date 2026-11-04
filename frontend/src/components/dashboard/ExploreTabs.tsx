import { useState } from 'react';
import { GitCommitHorizontal } from 'lucide-react';
import type { Answer, Overview, RepoMapData, Status } from '../../api/types';
import { repoName } from '../../utils/repo';
import { timeAgo } from '../../utils/time';
import RepoMap from '../repos/RepoMap';
import Graph from './Graph';
import Card from '../ui/Card';

/** Repository map and contributor graph behind tabs, below the answer. */
export default function ExploreTabs({
  overview,
  status,
  repoMap,
  mapError,
  scope,
  liveFiles,
  answer,
  onEvidence,
}: {
  overview: Overview;
  status: Status | null;
  repoMap: RepoMapData | null;
  mapError: boolean;
  scope: string | null;
  liveFiles: string[];
  answer: Answer | null;
  onEvidence: (id: string) => void;
}) {
  const [tab, setTab] = useState<'map' | 'graph'>('map');
  return (
    <div>
      <div className="flex w-fit gap-1 rounded-lg bg-ink-850 p-1" role="tablist" aria-label="Explore">
        <TabButton active={tab === 'map'} onClick={() => setTab('map')}>
          Repository map
        </TabButton>
        <TabButton active={tab === 'graph'} onClick={() => setTab('graph')}>
          Contributor graph
        </TabButton>
      </div>
      <div className="mt-2">
        {tab === 'map' ? (
          <Card>
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
        ) : answer ? (
          <Graph answer={answer} liveFiles={liveFiles} onEvidence={onEvidence} />
        ) : (
          <Card pad="sm">
            <div className="px-3 py-6 text-center text-[13px] text-slate-500">
              Ask a question to see who connects to which code.
            </div>
          </Card>
        )}
      </div>
    </div>
  );
}

function TabButton({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: string;
}) {
  return (
    <button
      role="tab"
      aria-selected={active}
      onClick={onClick}
      className={`rounded-md px-3 py-1.5 text-[13px] font-medium ${
        active ? 'bg-ink-900 text-slate-900 shadow-sm' : 'text-slate-500 hover:text-slate-200'
      }`}
    >
      {children}
    </button>
  );
}
