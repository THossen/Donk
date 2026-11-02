import type { AskEvent } from '../api/types';

export function shortEvidence(id: string): string {
  if (id.startsWith('c:')) return `commit ${id.slice(2, 12)}`;
  const parts = id.split(':');
  if (parts[0] === 'h' && parts.length === 3) {
    const p = decodeURIComponent(parts[1]);
    return `${p.split('/').pop()}:${parts[2]}`;
  }
  if ((parts[0] === 's' || parts[0] === 'b') && parts.length === 4) {
    const p = decodeURIComponent(parts[1]);
    return `${p.split('/').pop()}:${parts[2]}+${parts[3]}`;
  }
  return id;
}

/** File paths referenced by streaming tool-result events (for map highlights). */
export function filesFromEvents(evts: AskEvent[]): string[] {
  const files = new Set<string>();
  for (const e of evts) {
    if (e.type === 'result') {
      for (const id of e.evidence_ids) {
        const parts = id.split(':');
        if ((parts[0] === 's' || parts[0] === 'b' || parts[0] === 'h') && parts.length >= 3) {
          try {
            files.add(decodeURIComponent(parts[1]));
          } catch {
            /* ignore */
          }
        }
      }
    }
  }
  return [...files].slice(0, 12);
}
