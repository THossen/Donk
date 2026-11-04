/** Display name for a repo path (last segment). */
export function repoName(path?: string): string {
  return path?.split(/[\\/]/).filter(Boolean).pop() ?? 'Repository';
}

/** Shorten a path keeping the basename (plus parent dir when it fits). */
export function shortPath(p: string, max = 34): string {
  if (p.length <= max) return p;
  const parts = p.split('/');
  const base = parts.pop() ?? p;
  const parent = parts.pop();
  const tail = parent ? `${parent}/${base}` : base;
  return tail.length <= max - 2 ? `…/${tail}` : `…${p.slice(-(max - 2))}`;
}
