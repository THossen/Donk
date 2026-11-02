import { useId } from 'react';

export default function Logo({ size = 30 }: { size?: number }) {
  const uid = useId().replace(/:/g, '');
  return (
    <svg width={size} height={size} viewBox="0 0 64 64" role="img" aria-label="Donk logo" className="donk-logo">
      <defs>
        <linearGradient id={`donk-sheen-grad-${uid}`} x1="0" y1="0" x2="1" y2="0">
          <stop offset="0" stopColor="#ffffff" stopOpacity="0" />
          <stop offset="0.5" stopColor="#ffffff" stopOpacity="0.55" />
          <stop offset="1" stopColor="#ffffff" stopOpacity="0" />
        </linearGradient>
        <clipPath id={`donk-sheen-clip-${uid}`}>
          <rect width="64" height="64" rx="14" />
        </clipPath>
      </defs>
      <rect width={64} height={64} rx={14} fill="#0d9488" />
      <path
        d="M45 56 C45 48 46.5 40 47 33 L44.5 11 L40.5 27 Q39.5 28.5 38.5 27 L35 12 L31 28 C30 29.5 29 30.5 28 31.5 C24 36 20 41 16.5 45.5 Q13.5 48.5 14.5 51 C15.5 53 18 54 21 54 C24 54 27 52.5 30 51 C33 49.5 35 52 36.5 56"
        fill="none"
        stroke="#ffffff"
        strokeWidth={3.8}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <circle cx={29.5} cy={38} r={2} fill="#ffffff" />
      <circle cx={16.5} cy={50} r={1.2} fill="#ffffff" />
      <g clipPath={`url(#donk-sheen-clip-${uid})`}>
        <g transform="rotate(18 32 32)">
          <rect className="donk-sheen" x={18} y={-20} width={16} height={110} fill={`url(#donk-sheen-grad-${uid})`} />
        </g>
      </g>
    </svg>
  );
}
