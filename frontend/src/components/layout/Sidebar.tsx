import type { Status } from '../../api/types';
import Logo from './Logo';
import RepoStatus from './RepoStatus';
import { PAGES, type Page } from './navigation';

export default function Sidebar({
  page,
  onNavigate,
  status,
  statusError,
}: {
  page: Page;
  onNavigate: (p: Page) => void;
  status: Status | null;
  statusError: string | null;
}) {
  return (
    <aside className="hidden w-60 shrink-0 flex-col border-r border-ink-700 bg-ink-900 px-5 py-6 md:flex">
      <div className="flex items-center gap-2.5">
        <Logo size={30} />
        <div className="text-xl font-bold tracking-tight text-slate-900">Donk</div>
      </div>
      <div className="mt-1 text-xs tracking-wide text-slate-500">CODE OWNERSHIP, CLARIFIED</div>
      <nav className="mt-10 space-y-1 text-sm">
        {PAGES.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => onNavigate(id)}
            aria-current={page === id ? 'page' : undefined}
            className={`flex w-full items-center gap-2 rounded-lg px-3 py-2.5 font-medium ${
              page === id
                ? 'bg-ink-850 text-slate-900'
                : 'text-slate-500 hover:bg-ink-850 hover:text-slate-900'
            }`}
          >
            <Icon size={15} className={page === id ? 'text-teal-300' : 'text-slate-400'} /> {label}
          </button>
        ))}
      </nav>
      <div className="mt-auto space-y-4 text-xs text-slate-400">
        <RepoStatus status={status} error={statusError} />
        <div className="rounded-lg border border-ink-700 bg-ink-850 p-3 leading-relaxed">
          History is bounded: ≤{status?.history_limits.git_max_commits ?? 50} commits, ≤
          {status?.history_limits.git_max_blame_lines ?? 200} blame lines per file call.
        </div>
      </div>
    </aside>
  );
}
