import type { ReactNode } from 'react';

/** Standard page-level card. Use `className` for additive layout only (e.g. mt-4). */
export default function Card({
  pad = 'md',
  elevated = false,
  flat = false,
  tone = 'default',
  className = '',
  children,
}: {
  pad?: 'sm' | 'md';
  elevated?: boolean;
  flat?: boolean;
  tone?: 'default' | 'teal';
  className?: string;
  children: ReactNode;
}) {
  return (
    <div
      className={`rounded-xl border bg-ink-900 ${tone === 'teal' ? 'border-teal-900' : 'border-ink-700'} ${
        pad === 'sm' ? 'p-4' : 'p-5'
      } ${flat ? '' : elevated ? 'shadow-md' : 'shadow-sm'}${className ? ` ${className}` : ''}`}
    >
      {children}
    </div>
  );
}
