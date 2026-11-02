import type { ReactNode } from 'react';

/** Borderless icon-only button (refresh, close, ...). */
export default function IconButton({
  label,
  onClick,
  className = '',
  children,
}: {
  label: string;
  onClick: () => void;
  className?: string;
  children: ReactNode;
}) {
  return (
    <button onClick={onClick} aria-label={label} className={`rounded p-1 hover:bg-ink-800${className ? ` ${className}` : ''}`}>
      {children}
    </button>
  );
}
