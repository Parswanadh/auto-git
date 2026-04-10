'use client';

import {
  useCallback,
  createContext,
  type Dispatch,
  type ReactNode,
  type SetStateAction,
  useContext,
  useEffect,
  useMemo,
  useState,
} from 'react';

export type PresentationMode = 'frontier' | 'evidence' | 'safe';
export type MotionTier = 'high' | 'medium' | 'low';

type PresentationModeContextValue = {
  selectedMode: PresentationMode;
  effectiveMode: PresentationMode;
  motionTier: MotionTier;
  reducedMotion: boolean;
  setSelectedMode: Dispatch<SetStateAction<PresentationMode>>;
};

const DEFAULT_MODE: PresentationMode = 'evidence';

const PresentationModeContext = createContext<PresentationModeContextValue | null>(null);

function hasConstrainedDeviceProfile(): boolean {
  if (typeof window === 'undefined') {
    return false;
  }

  const nav = window.navigator as Navigator & {
    deviceMemory?: number;
    connection?: { saveData?: boolean };
  };

  const lowMemory = typeof nav.deviceMemory === 'number' && nav.deviceMemory <= 4;
  const lowCoreCount = typeof nav.hardwareConcurrency === 'number' && nav.hardwareConcurrency <= 4;
  const saveDataOn = Boolean(nav.connection?.saveData);

  return lowMemory || lowCoreCount || saveDataOn;
}

function getMotionTier(effectiveMode: PresentationMode, reducedMotion: boolean): MotionTier {
  if (effectiveMode === 'safe' || reducedMotion) {
    return 'low';
  }

  return hasConstrainedDeviceProfile() ? 'medium' : 'high';
}

export default function PresentationModeProvider({ children }: { children: ReactNode }) {
  const [selectedMode] = useState<PresentationMode>(DEFAULT_MODE);
  const [reducedMotion, setReducedMotion] = useState(false);

  // Mode switching is intentionally disabled; site defaults to judge/evidence mode.
  const setSelectedMode = useCallback<Dispatch<SetStateAction<PresentationMode>>>(() => {
    return;
  }, []);

  useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
    const sync = () => setReducedMotion(mediaQuery.matches);

    sync();
    mediaQuery.addEventListener('change', sync);

    return () => mediaQuery.removeEventListener('change', sync);
  }, []);

  const effectiveMode: PresentationMode = useMemo(() => {
    if (reducedMotion) {
      return 'safe';
    }

    return DEFAULT_MODE;
  }, [reducedMotion]);

  const motionTier = useMemo(() => getMotionTier(effectiveMode, reducedMotion), [effectiveMode, reducedMotion]);

  useEffect(() => {
    const root = document.documentElement;

    root.setAttribute('data-presentation-mode', effectiveMode);
    root.setAttribute('data-motion-tier', motionTier);
  }, [effectiveMode, motionTier]);

  const value = useMemo<PresentationModeContextValue>(
    () => ({
      selectedMode,
      effectiveMode,
      motionTier,
      reducedMotion,
      setSelectedMode,
    }),
    [selectedMode, effectiveMode, motionTier, reducedMotion, setSelectedMode],
  );

  return <PresentationModeContext.Provider value={value}>{children}</PresentationModeContext.Provider>;
}

export function usePresentationMode(): PresentationModeContextValue {
  const context = useContext(PresentationModeContext);
  if (!context) {
    throw new Error('usePresentationMode must be used inside PresentationModeProvider');
  }

  return context;
}
