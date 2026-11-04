import { useEffect, useState } from 'react';
import { FolderOpen, MessagesSquare, X } from 'lucide-react';
import { clearInvestigations, deleteInvestigation, fetchInvestigations } from '../../api/client';
import type { InvestigationSummary } from '../../api/types';
import { timeAgo } from '../../utils/time';
import { repoName } from '../../utils/repo';
import Card from '../ui/Card';
import IconButton from '../ui/IconButton';

/** Past investigations: click one to reopen its answers and keep asking. */
export default function Investigations({
  refreshKey,
  activeId,
  onOpen,
  onDeleted,
}: {
  refreshKey: number;
  activeId: string | null;
  onOpen: (id: string) => void;
  onDeleted: (id: string | null) => void;
}) {
  const [items, setItems] = useState<InvestigationSummary[]>([]);

  useEffect(() => {
    fetchInvestigations()
      .then((r) => setItems(r.investigations))
      .catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [refreshKey]);

  async function remove(id: string) {
    try {
      await deleteInvestigation(id);
      setItems((prev) => prev.filter((q) => q.id !== id));
      onDeleted(id);
    } catch {
      /* list refreshes on next ask */
    }
  }

  async function clearAll() {
    try {
      await clearInvestigations();
      setItems([]);
      onDeleted(null);
    } catch {
      /* list refreshes on next ask */
    }
  }

  if (items.length === 0) return null;

  return (
    <div className="mt-4">
      <Card pad="sm">
        <div className="mb-2 flex items-center justify-between">
          <div className="flex items-center gap-2 text-sm font-medium text-slate-200">
            <MessagesSquare size={15} /> Past investigations
          </div>
          <button onClick={clearAll} className="text-xs text-slate-500 hover:text-slate-200">
            Clear all
          </button>
        </div>
        <ul className="max-h-56 space-y-1 overflow-y-auto">
          {items.map((inv) => (
            <li
              key={inv.id}
              className={`group flex items-center gap-2 rounded-lg px-2 py-1.5 text-[13px] hover:bg-ink-850 ${
                inv.id === activeId ? 'bg-ink-850' : ''
              }`}
            >
              <button
                onClick={() => onOpen(inv.id)}
                title={`Reopen: ${inv.title}`}
                className="flex min-w-0 flex-1 items-center gap-2 text-left"
              >
                <FolderOpen size={13} className="shrink-0 text-slate-500" />
                <span className="truncate font-medium text-slate-100">{inv.title || 'Untitled investigation'}</span>
                <span className="shrink-0 text-xs text-slate-500">
                  {inv.turn_count} turn{inv.turn_count === 1 ? '' : 's'} · {repoName(inv.repo)} · {timeAgo(inv.updated_at)}
                </span>
              </button>
              <span className="shrink-0 opacity-0 transition-opacity group-hover:opacity-100">
                <IconButton label="Delete investigation" onClick={() => remove(inv.id)} className="text-slate-500 hover:text-slate-200">
                  <X size={13} />
                </IconButton>
              </span>
            </li>
          ))}
        </ul>
      </Card>
    </div>
  );
}
