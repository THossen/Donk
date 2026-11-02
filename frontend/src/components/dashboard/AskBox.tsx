import { useEffect, type RefObject } from 'react';
import { ArrowUp, FolderGit2, KeyRound, Loader2 } from 'lucide-react';
import type { Status } from '../../api/types';
import Card from '../ui/Card';

const SUGGESTIONS = [
  'Who worked on auth?',
  'Who changed the server pairing code?',
  'Who wrote the provider integrations?',
];

export default function AskBox({
  question,
  onQuestionChange,
  asking,
  status,
  inputRef,
  onAsk,
  repoLabel,
  onRepoClick,
  onOpenPalette,
}: {
  question: string;
  onQuestionChange: (q: string) => void;
  asking: boolean;
  status: Status | null;
  inputRef: RefObject<HTMLTextAreaElement>;
  onAsk: (q: string) => void;
  repoLabel: string;
  onRepoClick: () => void;
  onOpenPalette: () => void;
}) {
  const isMac = typeof navigator !== 'undefined' && /Mac/i.test(navigator.platform);

  useEffect(() => {
    const el = inputRef.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
  }, [question, inputRef]);

  const submit = () => {
    if (question.trim() && !asking) onAsk(question);
  };

  return (
    <div>
      <Card
        elevated
        className="transition-shadow focus-within:border-teal-600 focus-within:shadow-[0_0_0_3px_rgb(20_184_166/0.18)]"
      >
        <label htmlFor="ask" className="sr-only">
          Ask about this codebase
        </label>
        <textarea
          id="ask"
          ref={inputRef}
          rows={2}
          value={question}
          onChange={(e) => onQuestionChange(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault();
              submit();
            }
          }}
          placeholder="Ask who wrote or changed any code…"
          disabled={asking}
          className="max-h-40 w-full resize-none bg-transparent text-[15px] leading-relaxed outline-none placeholder:text-slate-500"
        />
        <div className="mt-2 flex items-center justify-between gap-2">
          <button
            onClick={onRepoClick}
            title="Switch repository"
            className="flex min-w-0 items-center gap-1.5 rounded-full border border-ink-700 px-2.5 py-1 text-xs text-slate-300 hover:bg-ink-800"
          >
            <FolderGit2 size={13} className="shrink-0 text-teal-300" />
            <span className="truncate">{repoLabel}</span>
          </button>
          <div className="flex items-center gap-2">
            <button onClick={onOpenPalette} aria-label="Open command palette" className="hidden sm:block">
              <kbd className="rounded border border-ink-700 bg-ink-850 px-1.5 py-0.5 font-mono text-[11px] text-slate-400 hover:bg-ink-800">
                {isMac ? '⌘K' : 'Ctrl K'}
              </kbd>
            </button>
            <button
              onClick={submit}
              disabled={asking || !question.trim()}
              aria-label="Ask Donk"
              className="flex h-9 w-9 items-center justify-center rounded-full bg-teal-700 text-white shadow-sm hover:bg-[#0a5a53] disabled:opacity-50"
            >
              {asking ? <Loader2 size={16} className="animate-spin" /> : <ArrowUp size={16} />}
            </button>
          </div>
        </div>
      </Card>
      <div className="mt-2 flex flex-wrap gap-2">
        {SUGGESTIONS.map((s) => (
          <button
            key={s}
            onClick={() => {
              onQuestionChange(s);
              onAsk(s);
            }}
            disabled={asking}
            className="rounded-full border border-ink-700 px-3 py-1.5 text-[13px] text-slate-300 hover:border-teal-700 hover:bg-teal-950 hover:text-teal-100 disabled:opacity-50"
          >
            {s}
          </button>
        ))}
      </div>
      {status && !status.model_configured && (
        <div className="mt-2 flex items-start gap-2 text-[13px] text-slate-400">
          <KeyRound size={14} className="mt-0.5 shrink-0 text-amber-300" />
          <span>
            MODEL_API_KEY is not set — running deterministic local analysis. Set it in a private{' '}
            <span className="font-mono">.env</span> (see <span className="font-mono">.env.example</span>) to enable Muse investigation.
          </span>
        </div>
      )}
    </div>
  );
}
