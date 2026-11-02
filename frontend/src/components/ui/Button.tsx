import type { ButtonHTMLAttributes, ReactNode } from 'react';

const VARIANTS = {
  primary: 'bg-teal-700 text-white shadow-sm hover:bg-[#0a5a53] font-semibold',
  secondary: 'border border-ink-700 hover:bg-ink-800',
  accent: 'border border-teal-800 bg-teal-950 text-teal-100 hover:bg-teal-900 font-medium',
} as const;

const SIZES = {
  sm: 'px-2.5 py-1.5 text-xs',
  md: 'px-4 py-2 text-sm',
  lg: 'px-4 py-3 text-sm',
} as const;

/**
 * Shared button. Variants carry color only (except primary/accent text);
 * pass layout (flex, items-center, gap-*) and secondary text color via
 * `className`, which must not repeat the classes above.
 */
export default function Button({
  variant = 'primary',
  size = 'md',
  className = '',
  children,
  ...props
}: {
  variant?: keyof typeof VARIANTS;
  size?: keyof typeof SIZES;
  className?: string;
  children: ReactNode;
} & ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      className={`rounded-lg disabled:opacity-50 ${VARIANTS[variant]} ${SIZES[size]}${className ? ` ${className}` : ''}`}
      {...props}
    >
      {children}
    </button>
  );
}
