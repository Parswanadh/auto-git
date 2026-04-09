/**
 * Typography system for Auto-GIT website
 */

export const fonts = {
  orbitron: {
    name: 'Orbitron',
    weights: [400, 500, 600, 700, 800, 900] as const,
    style: 'sans-serif',
  },
  rajdhani: {
    name: 'Rajdhani',
    weights: [300, 400, 500, 600, 700] as const,
    style: 'sans-serif',
  },
  jetbrainsMono: {
    name: 'JetBrains Mono',
    weights: [300, 400, 500, 600] as const,
    style: 'monospace',
  },
} as const;

export type FontFamily = keyof typeof fonts;
export type FontWeight = 300 | 400 | 500 | 600 | 700 | 800 | 900;

/**
 * Font size scale
 */
export const fontSizes = {
  xs: '0.75rem',     // 12px
  sm: '0.875rem',    // 14px
  base: '1rem',      // 16px
  lg: '1.125rem',    // 18px
  xl: '1.25rem',     // 20px
  '2xl': '1.5rem',   // 24px
  '3xl': '1.875rem', // 30px
  '4xl': '2.25rem',  // 36px
  '5xl': '3rem',     // 48px
  '6xl': '3.75rem',  // 60px
  '7xl': '4.5rem',   // 72px
  '8xl': '6rem',     // 96px
  '9xl': '8rem',     // 128px
} as const;

export type FontSize = keyof typeof fontSizes;

/**
 * Line height scale
 */
export const lineHeights = {
  none: 1,
  tight: 1.25,
  snug: 1.375,
  normal: 1.5,
  relaxed: 1.625,
  loose: 2,
} as const;

export type LineHeight = keyof typeof lineHeights;

/**
 * Letter spacing scale
 */
export const letterSpacing = {
  tighter: '-0.05em',
  tight: '-0.025em',
  normal: '0',
  wide: '0.025em',
  wider: '0.05em',
  widest: '0.1em',
} as const;

export type LetterSpacing = keyof typeof letterSpacing;

/**
 * Text styles
 */
export const textStyles = {
  'display-xl': {
    fontSize: fontSizes['7xl'],
    fontWeight: 800,
    lineHeight: lineHeights.tight,
    letterSpacing: letterSpacing.tighter,
  },
  'display-lg': {
    fontSize: fontSizes['6xl'],
    fontWeight: 700,
    lineHeight: lineHeights.tight,
    letterSpacing: letterSpacing.tighter,
  },
  'display-md': {
    fontSize: fontSizes['5xl'],
    fontWeight: 700,
    lineHeight: lineHeights.tight,
  },
  'h1': {
    fontSize: fontSizes['4xl'],
    fontWeight: 700,
    lineHeight: lineHeights.tight,
  },
  'h2': {
    fontSize: fontSizes['3xl'],
    fontWeight: 600,
    lineHeight: lineHeights.snug,
  },
  'h3': {
    fontSize: fontSizes['2xl'],
    fontWeight: 600,
    lineHeight: lineHeights.snug,
  },
  'h4': {
    fontSize: fontSizes.xl,
    fontWeight: 600,
    lineHeight: lineHeights.snug,
  },
  'body-lg': {
    fontSize: fontSizes.lg,
    fontWeight: 400,
    lineHeight: lineHeights.relaxed,
  },
  'body': {
    fontSize: fontSizes.base,
    fontWeight: 400,
    lineHeight: lineHeights.normal,
  },
  'body-sm': {
    fontSize: fontSizes.sm,
    fontWeight: 400,
    lineHeight: lineHeights.normal,
  },
  'caption': {
    fontSize: fontSizes.xs,
    fontWeight: 400,
    lineHeight: lineHeights.normal,
    letterSpacing: letterSpacing.wide,
  },
  'code': {
    fontFamily: fonts.jetbrainsMono.name,
    fontSize: fontSizes.sm,
    fontWeight: 400,
    lineHeight: lineHeights.normal,
  },
} as const;

export type TextStyle = keyof typeof textStyles;
