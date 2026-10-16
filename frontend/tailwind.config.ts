import type { Config } from 'tailwindcss'

export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        canvas: '#F4F6F8', sidebar: '#17232F', ink: '#202B36', muted: '#667382', line: '#DCE2E8',
        primary: '#315B78', 'primary-hover': '#274A63', ok: '#28745A', warn: '#A66A16', crit: '#B43C3C',
        tint: '#EAF1F6', badge: '#EDF1F4',
      },
      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui', 'Segoe UI', 'Arial', 'sans-serif'],
        mono: ['JetBrains Mono', 'ui-monospace', 'Consolas', 'monospace'],
      },
      borderRadius: { card: '8px' },
    },
  },
  plugins: [],
} satisfies Config
