import type { ReactNode } from 'react';

const TONES = {
  teal: 'bg-teal-950 text-teal-200',
  sky: 'bg-sky-950 text-sky-200',
  red: 'bg-red-950 text-red-200',
  amber: 'bg-amber-950 text-amber-200',
  gray: 'bg-ink-700 text-slate-300',
} as const;

/** Small rounded status badge. */
export default function Pill({
  tone,
  size = 'sm',
  title,
  className = '',
  children,
}: {
  tone: keyof typeof TONES;
  size?: 'sm' | 'md';
  title?: string;
  className?: string;
  children: ReactNode;
}) {
  return (
    <span
      title={title}
      className={`rounded-full text-xs font-medium ${TONES[tone]} ${size === 'sm' ? 'px-2 py-0.5' : 'px-2.5 py-1'}${
        className ? ` ${className}` : ''
      }`}
    >
      {children}
    </span>
  );
}
