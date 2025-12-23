/**
 * Design System Tokens - TypeScript constants for JS/TS usage
 * For CSS, prefer using variables directly: var(--color-accent)
 */

export const colors = {
  bg: {
    primary: '#09090b',
    secondary: '#0f0f11',
    tertiary: '#18181b',
    hover: '#27272a',
  },
  text: {
    primary: '#fafafa',
    secondary: '#a1a1aa',
    muted: '#71717a',
    disabled: '#52525b',
  },
  accent: {
    DEFAULT: '#6366f1',
    hover: '#818cf8',
    muted: '#4f46e5',
    glow: 'rgba(99, 102, 241, 0.15)',
  },
  success: '#22c55e',
  warning: '#f59e0b',
  error: '#ef4444',
  info: '#3b82f6',
  border: {
    DEFAULT: '#27272a',
    muted: '#18181b',
    accent: '#6366f1',
  },
} as const;

export const glass = {
  bg: 'rgba(255, 255, 255, 0.03)',
  bgHover: 'rgba(255, 255, 255, 0.05)',
  border: 'rgba(255, 255, 255, 0.08)',
  borderHover: 'rgba(255, 255, 255, 0.12)',
  blur: 20,
  blurStrong: 40,
} as const;

export const typography = {
  fontFamily: {
    sans: "'Inter', -apple-system, BlinkMacSystemFont, system-ui, sans-serif",
    mono: "'JetBrains Mono', 'Fira Code', Monaco, Consolas, monospace",
  },
  fontSize: {
    xs: '0.75rem',
    sm: '0.875rem',
    base: '1rem',
    lg: '1.125rem',
    xl: '1.25rem',
    '2xl': '1.5rem',
    '3xl': '2rem',
    '4xl': '2.5rem',
  },
  lineHeight: {
    tight: 1.25,
    normal: 1.5,
    relaxed: 1.75,
  },
} as const;

export const spacing = {
  1: '0.25rem',
  2: '0.5rem',
  3: '0.75rem',
  4: '1rem',
  5: '1.25rem',
  6: '1.5rem',
  8: '2rem',
  10: '2.5rem',
  12: '3rem',
  16: '4rem',
} as const;

export const animation = {
  easing: {
    outExpo: 'cubic-bezier(0.16, 1, 0.3, 1)',
    outQuart: 'cubic-bezier(0.25, 1, 0.5, 1)',
    inOut: 'cubic-bezier(0.4, 0, 0.2, 1)',
    spring: 'cubic-bezier(0.34, 1.56, 0.64, 1)',
  },
  duration: {
    fast: 150,
    normal: 250,
    slow: 400,
    slower: 600,
  },
} as const;

export const shadows = {
  sm: '0 1px 2px rgba(0, 0, 0, 0.3)',
  md: '0 4px 6px -1px rgba(0, 0, 0, 0.4), 0 2px 4px -2px rgba(0, 0, 0, 0.3)',
  lg: '0 10px 15px -3px rgba(0, 0, 0, 0.4), 0 4px 6px -4px rgba(0, 0, 0, 0.3)',
  glow: '0 0 20px rgba(99, 102, 241, 0.15)',
  glowLg: '0 0 40px rgba(99, 102, 241, 0.15)',
} as const;

export const radius = {
  sm: '0.375rem',
  md: '0.5rem',
  lg: '0.75rem',
  xl: '1rem',
  full: '9999px',
} as const;

export const breakpoints = {
  sm: 640,
  md: 768,
  lg: 1024,
  xl: 1280,
  '2xl': 1536,
} as const;

export const zIndex = {
  dropdown: 50,
  sticky: 100,
  modal: 200,
  popover: 300,
  tooltip: 400,
  toast: 500,
} as const;

/** Get computed value of a CSS variable */
export function getCSSVar(variable: string): string {
  if (typeof window === 'undefined') return '';
  return getComputedStyle(document.documentElement).getPropertyValue(variable).trim();
}

/** Set a CSS variable at runtime */
export function setCSSVar(variable: string, value: string): void {
  if (typeof window === 'undefined') return;
  document.documentElement.style.setProperty(variable, value);
}

// Framer Motion presets
export const motionVariants = {
  fadeIn: {
    initial: { opacity: 0 },
    animate: { opacity: 1 },
    exit: { opacity: 0 },
  },
  fadeInUp: {
    initial: { opacity: 0, y: 10 },
    animate: { opacity: 1, y: 0 },
    exit: { opacity: 0, y: -10 },
  },
  scaleIn: {
    initial: { opacity: 0, scale: 0.95 },
    animate: { opacity: 1, scale: 1 },
    exit: { opacity: 0, scale: 0.95 },
  },
  blurIn: {
    initial: { opacity: 0, filter: 'blur(10px)' },
    animate: { opacity: 1, filter: 'blur(0px)' },
    exit: { opacity: 0, filter: 'blur(10px)' },
  },
} as const;

export const defaultTransition = {
  duration: animation.duration.normal / 1000,
  ease: [0.16, 1, 0.3, 1],
} as const;

export const staggerContainer = {
  animate: {
    transition: {
      staggerChildren: 0.05,
    },
  },
} as const;

// Types
export type ColorKey = keyof typeof colors;
export type SpacingKey = keyof typeof spacing;
export type RadiusKey = keyof typeof radius;
