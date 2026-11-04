import type { RefObject } from 'react';
import Button from '../ui/Button';
import Card from '../ui/Card';

export default function EmailPrompt({
  draftFor,
  draftQuestion,
  onDraftQuestionChange,
  draftBusy,
  draftError,
  onPrepare,
  onCancel,
  boxRef,
}: {
  draftFor: string;
  draftQuestion: string;
  onDraftQuestionChange: (q: string) => void;
  draftBusy: boolean;
  draftError: string | null;
  onPrepare: (suggested: boolean) => void;
  onCancel: () => void;
  boxRef: RefObject<HTMLDivElement>;
}) {
  return (
    <div ref={boxRef}>
      <Card>
        <h3 className="text-base font-semibold">Ask {draftFor} a question</h3>
        <textarea
          value={draftQuestion}
          onChange={(e) => onDraftQuestionChange(e.target.value)}
          rows={3}
          placeholder="What do you want to ask?"
          className="mt-2 w-full rounded-lg border border-ink-700 bg-ink-950 px-3 py-2 text-sm outline-none focus:border-teal-700"
        />
        {draftError && <div className="mt-2 text-sm text-red-300">{draftError}</div>}
        <div className="mt-2 flex flex-wrap gap-2">
          <Button onClick={() => onPrepare(false)} disabled={draftBusy}>
            {draftBusy ? 'Preparing…' : 'Prepare draft'}
          </Button>
          <Button variant="secondary" onClick={() => onPrepare(true)} disabled={draftBusy} className="text-slate-200">
            Suggest a question from the code
          </Button>
          <button
            onClick={onCancel}
            className="rounded-lg px-3 py-2 text-sm text-slate-400 hover:text-slate-200"
          >
            Cancel
          </button>
        </div>
      </Card>
    </div>
  );
}
