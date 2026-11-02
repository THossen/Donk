const compact = new Intl.NumberFormat('en-US', { notation: 'compact' });

/** Dense-UI counts: 2817 -> "2.8K". Pair with title={exact} for precision. */
export function formatCompact(n: number): string {
  return compact.format(n);
}
