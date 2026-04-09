'use client';

import {
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

const STORAGE_KEY = 'autogit:presentation-mode';
const MODE_SET = new Set<PresentationMode>(['frontier', 'evidence', 'safe']);

const PresentationModeContext = createContext<PresentationModeContextValue | null>(null);

function parseMode(value: string | null | undefined): PresentationMode | null {
  if (!value) {
    return null;
  }

  return MODE_SET.has(value as PresentationMode) ? (value as PresentationMode) : null;
}

function readInitialModeFromUrl(): PresentationMode | null {
  if (typeof window === 'undefined') {
    return null;
  }

  const value = new URLSearchParams(window.location.search).get('mode');
  return parseMode(value);
}

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
  const [selectedMode, setSelectedMode] = useState<PresentationMode>('frontier');
  const [reducedMotion, setReducedMotion] = useState(false);

  useEffect(() => {
    const modeFromUrl = readInitialModeFromUrl();
    if (modeFromUrl) {
      setSelectedMode(modeFromUrl);
      return;
    }

    const modeFromStorage = parseMode(window.localStorage.getItem(STORAGE_KEY));
    if (modeFromStorage) {
      setSelectedMode(modeFromStorage);
    }
  }, []);

  useEffect(() => {
    window.localStorage.setItem(STORAGE_KEY, selectedMode);
  }, [selectedMode]);

  useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
    const sync = () => setReducedMotion(mediaQuery.matches);

    sync();
    mediaQuery.addEventListener('change', sync);

    return () => mediaQuery.removeEventListener('change', sync);
  }, []);

  const effectiveMode: PresentationMode = useMemo(() => {
    if (selectedMode === 'safe' || reducedMotion) {
      return 'safe';
    }

    return selectedMode;
  }, [selectedMode, reducedMotion]);

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
    [selectedMode, effectiveMode, motionTier, reducedMotion],
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
