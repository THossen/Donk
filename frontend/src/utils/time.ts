/** Human relative time for git short dates, unix timestamps, or null. */
export function timeAgo(input: string | number | null | undefined): string {
  if (input === null || input === undefined || input === '') return '';
  let ms: number;
  if (typeof input === 'number') {
    ms = input < 1e12 ? input * 1000 : input;
  } else if (/^\d+(\.\d+)?$/.test(input.trim())) {
    const n = Number(input);
    ms = n < 1e12 ? n * 1000 : n;
  } else {
    const t = Date.parse(input);
    if (Number.isNaN(t)) return input;
    ms = t;
  }
  const days = (Date.now() - ms) / 86400000;
  if (days < 0) return 'today';
  if (days < 1) return 'today';
  if (days < 2) return 'yesterday';
  if (days < 7) return `${Math.floor(days)} days ago`;
  if (days < 30) {
    const w = Math.floor(days / 7);
    return w === 1 ? '1 week ago' : `${w} weeks ago`;
  }
  const d = new Date(ms);
  const sameYear = d.getFullYear() === new Date().getFullYear();
  return d.toLocaleDateString('en-US', sameYear ? { month: 'short', day: 'numeric' } : { month: 'short', day: 'numeric', year: 'numeric' });
}
