/** Display name for a repo path (last segment). */
export function repoName(path?: string): string {
  return path?.split(/[\\/]/).filter(Boolean).pop() ?? 'Repository';
}
