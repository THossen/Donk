/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        ink: {
          950: '#f7f8fa',
          900: '#ffffff',
          850: '#f1f5f9',
          800: '#e8eef5',
          700: '#d8e0ea',
        },
        slate: {
          50: '#f8fafc',
          100: '#172033',
          200: '#263449',
          300: '#3e4d63',
          400: '#64748b',
          500: '#64748b',
          600: '#475569',
          900: '#172033',
        },
        teal: {
          100: '#115e59',
          200: '#0f766e',
          300: '#0d9488',
          800: '#5eead4',
          900: '#99f6e4',
          950: '#ccfbf1',
        },
        sky: {
          200: '#0369a1',
          950: '#e0f2fe',
        },
        amber: {
          100: '#92400e',
          200: '#92400e',
          300: '#b45309',
          950: '#fef3c7',
        },
        red: {
          200: '#b91c1c',
          300: '#dc2626',
          900: '#fecaca',
          950: '#fef2f2',
        },
      },
      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'SFMono-Regular', 'monospace'],
      },
    },
  },
  plugins: [],
}
