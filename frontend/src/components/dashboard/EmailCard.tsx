import { useState } from 'react';
import { AlertTriangle, ArrowUpRight, Mail, Send } from 'lucide-react';
import type { DraftAction } from '../../api/types';
import { sendAction } from '../../api/client';
import Button from '../ui/Button';

export default function EmailCard({
  draft,
  onDone,
  onCancel,
}: {
  draft: DraftAction;
  onDone: () => void;
  onCancel: () => void;
}) {
  const [subject, setSubject] = useState(draft.subject);
  const [body, setBody] = useState(draft.body);
  const [sending, setSending] = useState(false);
  const [result, setResult] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function send() {
    setSending(true);
    setError(null);
    try {
      const r = await sendAction(draft.id, {
        confirmed: true,
        idempotency_key: draft.idempotency_key,
        edited_subject: subject,
        edited_body: body,
      });
      setResult(String(r.human_status ?? r.status));
      onDone();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'send failed');
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="rounded-xl border border-teal-800 bg-ink-900 p-5 shadow-md">
      <div className="flex items-start gap-3">
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-teal-950 text-teal-200">
          <Mail size={17} />
        </div>
        <div>
          <div className="text-[11px] font-semibold uppercase tracking-[0.14em] text-teal-200">Ready to send</div>
          <h3 className="mt-0.5 text-base font-semibold text-slate-900">Review email draft</h3>
        </div>
      </div>
      <dl className="mt-4 space-y-2 rounded-lg bg-ink-850 p-3 text-sm">
        <div className="flex gap-2">
          <dt className="w-24 shrink-0 text-slate-500">To</dt>
          <dd className="font-medium text-slate-900">{draft.contributor} <span className="font-normal text-slate-500">(contributor identity)</span></dd>
        </div>
        <div className="flex gap-2">
          <dt className="w-24 shrink-0 text-slate-500">Delivers to</dt>
          <dd className="font-mono text-[13px] text-amber-200">{draft.delivers_to}</dd>
        </div>
      </dl>
      {draft.demo_mode && (
        <div className="mt-2 flex items-start gap-2 rounded-lg bg-amber-950/60 px-3 py-2 text-[13px] text-amber-100">
          <AlertTriangle size={15} className="mt-0.5 shrink-0" />
          <span>{draft.delivery_notice ?? 'Demo mode: this will go to your demo inbox, not to the contributor.'}</span>
        </div>
      )}
      <label className="mt-3 block text-xs font-medium text-slate-400">
        Subject
        <input
          value={subject}
          onChange={(e) => setSubject(e.target.value)}
          className="mt-1 w-full rounded-lg border border-ink-700 bg-ink-950 px-3 py-2.5 text-sm text-slate-900 outline-none focus:border-teal-700"
        />
      </label>
      <label className="mt-2 block text-xs font-medium text-slate-400">
        Message (editable)
        <textarea
          value={body}
          onChange={(e) => setBody(e.target.value)}
          rows={7}
          className="mt-1 w-full rounded-lg border border-ink-700 bg-ink-950 px-3 py-2.5 text-sm leading-relaxed text-slate-900 outline-none focus:border-teal-700"
        />
      </label>
      {error && <div className="mt-2 text-sm text-red-300">{error}</div>}
      {result && <div className="mt-2 text-sm text-teal-200">{result}</div>}
      <div className="mt-3 flex gap-2">
        <Button onClick={send} disabled={sending || result !== null} className="flex items-center gap-1.5">
          <Send size={14} /> {sending ? 'Sending…' : 'Send email'} <ArrowUpRight size={13} />
        </Button>
        <Button variant="secondary" onClick={onCancel} disabled={sending} className="text-slate-300">
          Cancel
        </Button>
      </div>
    </div>
  );
}
