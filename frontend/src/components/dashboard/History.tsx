import { useEffect, useState } from 'react';
import { History as HistoryIcon, RotateCcw, X } from 'lucide-react';
import { clearHistory, deleteHistoryItem, fetchHistory } from '../../api/client';
import type { HistoryItem } from '../../api/types';
import { timeAgo } from '../../utils/time';
import { repoName } from '../../utils/repo';
import Card from '../ui/Card';
import IconButton from '../ui/IconButton';

/** Recent questions on the dashboard. Hidden until the first ask. */
export default function History({ refreshKey, onRerun }: { refreshKey: number; onRerun: (q: string) => void }) {
  const [items, setItems] = useState<HistoryItem[]>([]);

  useEffect(() => {
    fetchHistory()
      .then((r) => setItems(r.questions))
      .catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [refreshKey]);

  async function remove(id: number) {
    try {
      await deleteHistoryItem(id);
      setItems((prev) => prev.filter((q) => q.id !== id));
    } catch {
      /* list refreshes on next ask */
    }
  }

  async function clearAll() {
    try {
      await clearHistory();
      setItems([]);
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
          <HistoryIcon size={15} /> Recent questions
        </div>
        <button onClick={clearAll} className="text-xs text-slate-500 hover:text-slate-200">
          Clear all
        </button>
      </div>
      <ul className="max-h-56 space-y-1 overflow-y-auto">
        {items.map((q) => (
          <li
            key={q.id}
            className="group flex items-center gap-2 rounded-lg px-2 py-1.5 text-[13px] hover:bg-ink-850"
          >
            <button
              onClick={() => onRerun(q.question)}
              title={`Re-run: ${q.question}`}
              className="flex min-w-0 flex-1 items-center gap-2 text-left"
            >
              <RotateCcw size={13} className="shrink-0 text-slate-500" />
              <span className="truncate font-medium text-slate-100">{q.question}</span>
              <span className="shrink-0 text-xs text-slate-500">
                {repoName(q.repo)} · {timeAgo(q.created_at)}
              </span>
            </button>
            <span className="shrink-0 opacity-0 transition-opacity group-hover:opacity-100">
              <IconButton label="Remove from history" onClick={() => remove(q.id)} className="text-slate-500 hover:text-slate-200">
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
