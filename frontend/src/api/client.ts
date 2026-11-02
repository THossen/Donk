import type { AskEvent, DraftAction, HistoryItem, Overview, ProposeEmailInput, RepoList, RepoMapData, SendActionInput, Status } from './types';

export async function fetchStatus(): Promise<Status> {
  const r = await fetch('/api/status');
  if (!r.ok) throw new Error('status failed');
  return r.json();
}

export async function fetchOverview(): Promise<Overview> {
  const r = await fetch('/api/repo/overview');
  if (!r.ok) throw new Error('overview failed');
  return r.json();
}

export async function* askDonk(question: string): AsyncGenerator<AskEvent> {
  const r = await fetch('/api/ask', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question }),
  });
  if (!r.ok || !r.body) throw new Error(`ask failed: ${r.status}`);
  const reader = r.body.getReader();
  const decoder = new TextDecoder();
  let buf = '';
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    let idx: number;
    while ((idx = buf.indexOf('\n\n')) >= 0) {
      const chunk = buf.slice(0, idx);
      buf = buf.slice(idx + 2);
      for (const line of chunk.split('\n')) {
        const t = line.trim();
        if (t.startsWith('data:')) {
          try {
            yield JSON.parse(t.slice(5).trim()) as AskEvent;
          } catch {
            /* ignore partial */
          }
        }
      }
    }
  }
}

export async function fetchRepoMap(): Promise<RepoMapData> {
  const r = await fetch('/api/repo/map');
  if (!r.ok) throw new Error('repo map failed');
  return r.json();
}

export async function fetchRepos(): Promise<RepoList> {
  const r = await fetch('/api/repos');
  if (!r.ok) throw new Error('repository list failed');
  return r.json();
}

export async function selectRepo(name: string): Promise<{ active: string }> {
  const r = await fetch('/api/repos/select', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name }),
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function fetchEvidence(id: string): Promise<Record<string, unknown>> {
  const r = await fetch(`/api/evidence?id=${encodeURIComponent(id)}`);
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function proposeEmail(input: ProposeEmailInput): Promise<DraftAction> {
  const r = await fetch('/api/email/propose', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function sendAction(id: string, input: SendActionInput): Promise<Record<string, unknown>> {
  const r = await fetch(`/api/actions/${id}/send`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function fetchActivity(): Promise<{ actions: Record<string, unknown>[] }> {
  const r = await fetch('/api/activity');
  if (!r.ok) throw new Error('activity failed');
  return r.json();
}

export async function fetchAction(id: string): Promise<DraftAction> {
  const r = await fetch(`/api/actions/${id}`);
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function discardAction(id: string): Promise<Record<string, unknown>> {
  const r = await fetch(`/api/actions/${id}/discard`, { method: 'POST' });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function fetchHistory(): Promise<{ questions: HistoryItem[] }> {
  const r = await fetch('/api/history');
  if (!r.ok) throw new Error('history failed');
  return r.json();
}

export async function deleteHistoryItem(id: number): Promise<void> {
  const r = await fetch(`/api/history/${id}`, { method: 'DELETE' });
  if (!r.ok) throw new Error(await r.text());
}

export async function clearHistory(): Promise<void> {
  const r = await fetch('/api/history', { method: 'DELETE' });
  if (!r.ok) throw new Error(await r.text());
}
