import { useEffect, useMemo, useRef, useState } from 'react';
import { CheckCircle2, FolderGit2, Loader2, Search } from 'lucide-react';
import type { RepoEntry } from '../../api/types';
import { fetchRepos, selectRepo } from '../../api/client';
import { PAGES, type Page } from '../layout/navigation';

interface Item {
  key: string;
  section: string;
  label: string;
  hint?: string;
  disabled?: boolean;
  icon: React.ReactNode;
  run: () => void;
}

export default function CommandPalette({
  open,
  onClose,
  onAsk,
  onNavigate,
  onSwitched,
}: {
  open: boolean;
  onClose: () => void;
  onAsk: (q: string) => void;
  onNavigate: (p: Page) => void;
  onSwitched: () => void;
}) {
  const [query, setQuery] = useState('');
  const [active, setActive] = useState(0);
  const [repos, setRepos] = useState<RepoEntry[] | null>(null);
  const [reposError, setReposError] = useState<string | null>(null);
  const [switching, setSwitching] = useState<string | null>(null);
  const [switchError, setSwitchError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const itemRefs = useRef<(HTMLButtonElement | null)[]>([]);

  useEffect(() => {
    if (!open) return;
    setQuery('');
    setActive(0);
    setSwitchError(null);
    inputRef.current?.focus();
    fetchRepos()
      .then((r) => {
        setRepos(r.repos);
        setReposError(null);
      })
      .catch((e) => setReposError(e instanceof Error ? e.message : 'failed'));
  }, [open ]);

  async function switchTo(name: string) {
    setSwitching(name);
    setSwitchError(null);
    try {
      await selectRepo(name);
      onSwitched();
      onClose();
    } catch (e) {
      setSwitchError(e instanceof Error ? e.message : 'switch failed');
    } finally {
      setSwitching(null);
    }
  }

  const items = useMemo<Item[]>(() => {
    const q = query.trim().toLowerCase();
    const list: Item[] = [];
    if (query.trim()) {
      const short = query.trim().length > 60 ? query.trim().slice(0, 59) + '…' : query.trim();
      list.push({
        key: 'ask',
        section: 'Ask',
        label: `Ask Donk: “${short}”`,
        icon: <Search size={15} className="text-teal-300" />,
        run: () => onAsk(query.trim()),
      });
    }
    for (const p of PAGES) {
      if (q && !p.label.toLowerCase().includes(q)) continue;
      const Icon = p.icon;
      list.push({
        key: `go-${p.id}`,
        section: 'Go to',
        label: p.label,
        icon: <Icon size={15} className="text-slate-400" />,
        run: () => {
          onNavigate(p.id);
          onClose();
        },
      });
    }
    if (repos) {
      for (const r of repos) {
        if (q && !r.name.toLowerCase().includes(q)) continue;
        list.push({
          key: `repo-${r.name}`,
          section: 'Repositories',
          label: r.name,
          hint: r.active ? 'Current' : r.error ? 'Unavailable' : `${r.tracked_total?.toLocaleString() ?? '?'} files`,
          disabled: r.active || !!r.error || switching !== null,
          icon:
            switching === r.name ? (
              <Loader2 size={15} className="animate-spin text-teal-300" />
            ) : r.active ? (
              <CheckCircle2 size={15} className="text-teal-300" />
            ) : (
              <FolderGit2 size={15} className="text-slate-400" />
            ),
          run: () => {
            if (!r.active && !r.error) switchTo(r.name);
            else onClose();
          },
        });
      }
    }
    return list;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [query, repos, switching]);

  useEffect(() => {
    setActive(0);
  }, [query]);

  useEffect(() => {
    itemRefs.current[active]?.scrollIntoView({ block: 'nearest' });
  }, [active]);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        onClose();
      } else if (e.key === 'ArrowDown') {
        e.preventDefault();
        setActive((a) => (items.length ? (a + 1) % items.length : 0));
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        setActive((a) => (items.length ? (a - 1 + items.length) % items.length : 0));
      } else if (e.key === 'Enter') {
        e.preventDefault();
        const item = items[active];
        if (item && !item.disabled) item.run();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open, items, active, onClose]);

  if (!open) return null;

  let lastSection = '';
  return (
    <div className="fixed inset-0 z-50" role="dialog" aria-label="Command palette">
      <div className="absolute inset-0 bg-black/40" onClick={onClose} aria-hidden="true" />
      <div className="relative mx-auto mt-[10vh] w-[min(36rem,calc(100%-2rem))] overflow-hidden rounded-xl border border-ink-700 bg-ink-900 shadow-lg">
        <div className="flex items-center gap-2 border-b border-ink-700 px-4">
          <Search size={16} className="shrink-0 text-slate-400" />
          <input
            ref={inputRef}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Type a question, or search pages and repos…"
            className="w-full bg-transparent py-3.5 text-[15px] outline-none placeholder:text-slate-500"
          />
          <kbd className="shrink-0 rounded border border-ink-700 bg-ink-850 px-1.5 py-0.5 font-mono text-[11px] text-slate-400">
            esc
          </kbd>
        </div>
        {(reposError ?? switchError) && (
          <div className="border-b border-ink-700 px-4 py-2 text-sm text-red-300">{reposError ?? switchError}</div>
        )}
        <ul className="max-h-72 overflow-y-auto p-2">
          {items.length === 0 && !reposError && (
            <li className="px-3 py-6 text-center text-sm text-slate-500">
              {repos === null ? 'Loading…' : 'No matches'}
            </li>
          )}
          {items.map((item, i) => {
            const header = item.section !== lastSection ? item.section : null;
            lastSection = item.section;
            return (
              <li key={item.key}>
                {header && (
                  <div className="px-3 pb-1 pt-2 text-[11px] font-semibold uppercase tracking-wide text-slate-500">
                    {header}
                  </div>
                )}
                <button
                  ref={(el) => {
                    itemRefs.current[i] = el;
                  }}
                  onClick={() => {
                    if (!item.disabled) item.run();
                  }}
                  onMouseEnter={() => setActive(i)}
                  disabled={item.disabled}
                  className={`flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-left text-sm ${
                    i === active ? 'bg-ink-850' : ''
                  } ${item.disabled ? 'opacity-60' : ''}`}
                >
                  <span className="shrink-0">{item.icon}</span>
                  <span className="truncate">{item.label}</span>
                  {item.hint && <span className="ml-auto shrink-0 text-xs text-slate-500">{item.hint}</span>}
                </button>
              </li>
            );
          })}
        </ul>
        <div className="flex items-center gap-3 border-t border-ink-700 px-4 py-2 font-mono text-[11px] text-slate-500">
          <span>↑↓ navigate</span>
          <span>↵ run</span>
          <span>esc close</span>
        </div>
      </div>
    </div>
  );
}
