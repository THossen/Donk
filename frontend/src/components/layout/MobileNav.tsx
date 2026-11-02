import Logo from './Logo';
import { PAGES, type Page } from './navigation';

export default function MobileNav({ page, onNavigate }: { page: Page; onNavigate: (p: Page) => void }) {
  return (
    <>
      <div className="mb-6 flex items-center justify-between md:hidden">
        <div className="flex items-center gap-2.5">
          <Logo size={28} />
          <div>
            <div className="text-lg font-bold tracking-tight text-slate-900">Donk</div>
            <div className="text-[10px] font-semibold uppercase tracking-[0.14em] text-slate-400">Code intelligence</div>
          </div>
        </div>
        <span className="rounded-full bg-teal-950 px-2.5 py-1 text-[11px] font-medium text-teal-200">Workspace</span>
      </div>
      <div className="mb-5 flex gap-2 md:hidden">
        {PAGES.map(({ id, shortLabel, icon: Icon }) => (
          <button
            key={id}
            onClick={() => onNavigate(id)}
            aria-current={page === id ? 'page' : undefined}
            className={`flex flex-1 items-center justify-center gap-2 rounded-lg border px-3 py-2.5 text-sm font-medium ${
              page === id
                ? 'border-ink-700 bg-ink-900 text-slate-900 shadow-sm'
                : 'border-transparent text-slate-500'
            }`}
          >
            <Icon size={15} className={page === id ? 'text-teal-300' : 'text-slate-400'} /> {shortLabel}
          </button>
        ))}
      </div>
    </>
  );
}
