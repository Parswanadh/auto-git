/**
 * Sci-fi themed color palette for Auto-GIT website
 */

export const colors = {
  // Base colors
  background: '#030712',
  primary: '#00D4FF',
  secondary: '#7C3AED',
  success: '#10B981',
  warning: '#F59E0B',
  error: '#EF4444',
  text: '#F8FAFC',
  
  // Dimmed variants
  'primary-dim': 'rgba(0, 212, 255, 0.1)',
  'secondary-dim': 'rgba(124, 58, 237, 0.1)',
  'text-dim': 'rgba(248, 250, 252, 0.7)',
  'text-dimmer': 'rgba(248, 250, 252, 0.5)',
} as const;

export type Color = keyof typeof colors;

/**
 * Get a color value with optional opacity
 */
export function getColor(colorName: Color, opacity?: number): string {
  const color = colors[colorName];
  if (opacity === undefined) return color;
  
  // Handle hex colors
  if (color.startsWith('#')) {
    const r = parseInt(color.slice(1, 3), 16);
    const g = parseInt(color.slice(3, 5), 16);
    const b = parseInt(color.slice(5, 7), 16);
    return `rgba(${r}, ${g}, ${b}, ${opacity})`;
  }
  
  // Handle rgba colors - replace existing alpha
  if (color.startsWith('rgba')) {
    return color.replace(/[\d.]+\)$/, `${opacity})`);
  }
  
  return color;
}

/**
 * Gradient definitions
 */
export const gradients = {
  primary: 'linear-gradient(135deg, #00D4FF 0%, #7C3AED 100%)',
  secondary: 'linear-gradient(135deg, #7C3AED 0%, #00D4FF 100%)',
  success: 'linear-gradient(135deg, #10B981 0%, #059669 100%)',
  dark: 'linear-gradient(180deg, #030712 0%, #0a0f1e 100%)',
} as const;

export type Gradient = keyof typeof gradients;
