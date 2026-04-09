'use client';

import { AnimatePresence, motion } from 'framer-motion';
import { useEffect, useMemo, useRef, useState } from 'react';
import { ChevronDown, ChevronUp, Gauge, Pause, Play, RotateCcw, ScrollText, SlidersHorizontal } from 'lucide-react';
import { usePresentationMode } from '@/components/PresentationModeProvider';

type PersistedSettings = {
  speed: number;
  panelOpen: boolean;
  controlsCollapsed?: boolean;
  speedCollapsed?: boolean;
};

const SETTINGS_KEY = 'autogit:auto-scroll-demo-settings';
const DEFAULT_SPEED = 48;
const MIN_SPEED = 12;
const MAX_SPEED = 260;

const SPEED_PRESETS = [
  { label: 'Cine', value: 22 },
  { label: 'Smooth', value: 48 },
  { label: 'Expo', value: 110 },
  { label: 'Fast', value: 180 },
  { label: 'Turbo', value: 240 },
];

function clampSpeed(value: number): number {
  if (Number.isNaN(value)) {
    return DEFAULT_SPEED;
  }

  return Math.min(Math.max(value, MIN_SPEED), MAX_SPEED);
}

export default function AutoScrollDemoController() {
  const { effectiveMode, motionTier, reducedMotion } = usePresentationMode();

  const [panelOpen, setPanelOpen] = useState(false);
  const [controlsCollapsed, setControlsCollapsed] = useState(false);
  const [speedCollapsed, setSpeedCollapsed] = useState(false);
  const [isRunning, setIsRunning] = useState(false);
  const [speed, setSpeed] = useState(DEFAULT_SPEED);
  const [direction, setDirection] = useState<1 | -1>(1);
  const [progress, setProgress] = useState(0);

  const rafRef = useRef<number | null>(null);
  const lastTsRef = useRef<number | null>(null);

  const autoplayBlocked = reducedMotion || motionTier === 'low';

  useEffect(() => {
    try {
      const storedRaw = window.localStorage.getItem(SETTINGS_KEY);
      if (storedRaw) {
        const stored = JSON.parse(storedRaw) as PersistedSettings;
        if (typeof stored.speed === 'number') {
          setSpeed(clampSpeed(stored.speed));
        }
        if (typeof stored.panelOpen === 'boolean') {
          setPanelOpen(stored.panelOpen);
        }
        if (typeof stored.controlsCollapsed === 'boolean') {
          setControlsCollapsed(stored.controlsCollapsed);
        }
        if (typeof stored.speedCollapsed === 'boolean') {
          setSpeedCollapsed(stored.speedCollapsed);
        }
      }
    } catch {
      // Ignore malformed local storage values.
    }

    const params = new URLSearchParams(window.location.search);
    const autoDemo = params.get('autodemo');
    const speedParam = params.get('autospeed');

    if (speedParam) {
      setSpeed(clampSpeed(Number(speedParam)));
      setPanelOpen(true);
    }

    if (autoDemo === '1') {
      setPanelOpen(true);
      setControlsCollapsed(false);
      setSpeedCollapsed(false);
      if (!autoplayBlocked) {
        setIsRunning(true);
      }
    }
  }, [autoplayBlocked]);

  useEffect(() => {
    const payload: PersistedSettings = { speed, panelOpen, controlsCollapsed, speedCollapsed };
    window.localStorage.setItem(SETTINGS_KEY, JSON.stringify(payload));
  }, [speed, panelOpen, controlsCollapsed, speedCollapsed]);

  useEffect(() => {
    const updateProgress = () => {
      const maxScroll = Math.max(document.documentElement.scrollHeight - window.innerHeight, 0);
      const current = Math.max(window.scrollY, 0);
      const nextProgress = maxScroll > 0 ? (current / maxScroll) * 100 : 0;
      setProgress(Math.min(Math.max(nextProgress, 0), 100));
    };

    updateProgress();
    window.addEventListener('scroll', updateProgress, { passive: true });

    return () => window.removeEventListener('scroll', updateProgress);
  }, []);

  useEffect(() => {
    if (!isRunning || autoplayBlocked) {
      return;
    }

    const tick = (ts: number) => {
      if (lastTsRef.current == null) {
        lastTsRef.current = ts;
      }

      const deltaSec = (ts - lastTsRef.current) / 1000;
      lastTsRef.current = ts;

      const maxScroll = Math.max(document.documentElement.scrollHeight - window.innerHeight, 0);
      if (maxScroll <= 0) {
        rafRef.current = window.requestAnimationFrame(tick);
        return;
      }

      let nextDirection = direction;
      let nextTop = window.scrollY + direction * speed * deltaSec;

      if (nextTop >= maxScroll) {
        nextTop = maxScroll;
        nextDirection = -1;
      } else if (nextTop <= 0) {
        nextTop = 0;
        nextDirection = 1;
      }

      if (nextDirection !== direction) {
        setDirection(nextDirection);
      }

      window.scrollTo({ top: nextTop, behavior: 'auto' });
      rafRef.current = window.requestAnimationFrame(tick);
    };

    rafRef.current = window.requestAnimationFrame(tick);

    return () => {
      if (rafRef.current != null) {
        window.cancelAnimationFrame(rafRef.current);
        rafRef.current = null;
      }
      lastTsRef.current = null;
    };
  }, [isRunning, speed, direction, autoplayBlocked]);

  useEffect(() => {
    if (!isRunning) {
      return;
    }

    const pause = () => setIsRunning(false);

    window.addEventListener('wheel', pause, { passive: true });
    window.addEventListener('touchstart', pause, { passive: true });
    window.addEventListener('keydown', pause);

    return () => {
      window.removeEventListener('wheel', pause);
      window.removeEventListener('touchstart', pause);
      window.removeEventListener('keydown', pause);
    };
  }, [isRunning]);

  useEffect(() => {
    if (autoplayBlocked && isRunning) {
      setIsRunning(false);
    }
  }, [autoplayBlocked, isRunning]);

  const statusText = useMemo(() => {
    if (autoplayBlocked) {
      return 'Auto-scroll disabled in reduced/safe motion mode';
    }

    return isRunning ? 'Live auto-tour running' : 'Auto-tour paused';
  }, [autoplayBlocked, isRunning]);

  const onReset = () => {
    setIsRunning(false);
    setDirection(1);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  return (
    <div className="fixed bottom-4 left-4 z-[66] flex flex-col items-start gap-2">
      <motion.button
        type="button"
        onClick={() => setPanelOpen((prev) => !prev)}
        className="rounded-xl border border-[rgba(0,212,255,0.35)] bg-[rgba(2,6,23,0.9)] px-3 py-2 text-xs font-semibold text-cyan-200 shadow-[0_0_20px_rgba(0,212,255,0.15)]"
        whileHover={{ y: -1, scale: 1.02 }}
        whileTap={{ scale: 0.98 }}
      >
        <span className="inline-flex items-center gap-2">
          <ScrollText className="h-4 w-4" />
          {panelOpen ? 'Hide Auto Tour' : 'Auto Tour'}
          {panelOpen ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
        </span>
      </motion.button>

      <AnimatePresence>
        {panelOpen && (
          <motion.div
            initial={{ opacity: 0, y: 14, scale: 0.97 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 10, scale: 0.98 }}
            transition={{ duration: 0.28, ease: [0.22, 1, 0.36, 1] }}
            className="w-[min(92vw,340px)] rounded-2xl border border-[rgba(0,212,255,0.28)] bg-[rgba(2,6,23,0.88)] p-3 text-[11px] text-[rgba(248,250,252,0.82)] shadow-[0_0_30px_rgba(0,212,255,0.16)] backdrop-blur-xl"
          >
            <p className="font-orbitron text-[11px] uppercase tracking-[0.16em] text-[rgba(248,250,252,0.78)]">
              Guided Website Tour
            </p>
            <p className="mt-1 text-[10px] text-[rgba(248,250,252,0.6)]">
              Mode: {effectiveMode} • {statusText}
            </p>

            <div className="mt-3 rounded-lg border border-[rgba(148,163,184,0.3)] bg-[rgba(15,23,42,0.55)] px-2.5 py-2 text-[10px]">
              <div className="flex items-center justify-between">
                <p className="font-semibold text-[rgba(248,250,252,0.8)]">Demo Controls</p>
                <button
                  type="button"
                  onClick={() => setControlsCollapsed((prev) => !prev)}
                  className="inline-flex items-center gap-1 text-cyan-200"
                >
                  {controlsCollapsed ? 'Expand' : 'Collapse'}
                  {controlsCollapsed ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronUp className="h-3.5 w-3.5" />}
                </button>
              </div>

              <AnimatePresence>
                {!controlsCollapsed && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 'auto' }}
                    exit={{ opacity: 0, height: 0 }}
                    transition={{ duration: 0.2 }}
                    className="overflow-hidden"
                  >
                    <div className="mt-2 grid grid-cols-3 gap-2">
                      <button
                        type="button"
                        onClick={() => setIsRunning(true)}
                        disabled={autoplayBlocked || isRunning}
                        className="rounded-lg border border-[rgba(16,185,129,0.45)] bg-[rgba(16,185,129,0.18)] px-2 py-2 text-[10px] font-semibold text-emerald-200 disabled:cursor-not-allowed disabled:opacity-45"
                      >
                        <span className="inline-flex items-center gap-1">
                          <Play className="h-3.5 w-3.5" />
                          Start
                        </span>
                      </button>
                      <button
                        type="button"
                        onClick={() => setIsRunning(false)}
                        disabled={!isRunning}
                        className="rounded-lg border border-[rgba(245,158,11,0.45)] bg-[rgba(245,158,11,0.18)] px-2 py-2 text-[10px] font-semibold text-amber-200 disabled:cursor-not-allowed disabled:opacity-45"
                      >
                        <span className="inline-flex items-center gap-1">
                          <Pause className="h-3.5 w-3.5" />
                          Pause
                        </span>
                      </button>
                      <button
                        type="button"
                        onClick={onReset}
                        className="rounded-lg border border-[rgba(124,58,237,0.45)] bg-[rgba(124,58,237,0.2)] px-2 py-2 text-[10px] font-semibold text-violet-200"
                      >
                        <span className="inline-flex items-center gap-1">
                          <RotateCcw className="h-3.5 w-3.5" />
                          Reset
                        </span>
                      </button>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>

            <div className="mt-2 rounded-lg border border-[rgba(148,163,184,0.3)] bg-[rgba(15,23,42,0.55)] px-2.5 py-2 text-[10px]">
              <div className="flex items-center justify-between">
                <p className="inline-flex items-center gap-1 font-semibold text-[rgba(248,250,252,0.8)]">
                  <SlidersHorizontal className="h-3.5 w-3.5" />
                  Speed Settings
                </p>
                <button
                  type="button"
                  onClick={() => setSpeedCollapsed((prev) => !prev)}
                  className="inline-flex items-center gap-1 text-cyan-200"
                >
                  {speedCollapsed ? 'Expand' : 'Collapse'}
                  {speedCollapsed ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronUp className="h-3.5 w-3.5" />}
                </button>
              </div>

              <AnimatePresence>
                {!speedCollapsed && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 'auto' }}
                    exit={{ opacity: 0, height: 0 }}
                    transition={{ duration: 0.2 }}
                    className="overflow-hidden"
                  >
                    <div className="mt-2 grid grid-cols-5 gap-1">
                      {SPEED_PRESETS.map((preset) => (
                        <button
                          key={preset.label}
                          type="button"
                          onClick={() => setSpeed(preset.value)}
                          className={`rounded-md border px-1 py-1 text-[9px] font-semibold transition-colors ${
                            speed === preset.value
                              ? 'border-cyan-300/60 bg-cyan-400/20 text-cyan-100'
                              : 'border-slate-600/70 bg-slate-900/40 text-slate-300 hover:border-cyan-300/50 hover:text-cyan-100'
                          }`}
                        >
                          {preset.label}
                        </button>
                      ))}
                    </div>

                    <div className="mt-2 rounded-lg border border-[rgba(148,163,184,0.3)] bg-[rgba(2,6,23,0.6)] p-2">
                      <div className="mb-1 flex items-center justify-between text-[10px]">
                        <span className="inline-flex items-center gap-1 text-[rgba(248,250,252,0.72)]">
                          <Gauge className="h-3.5 w-3.5" />
                          Scroll speed
                        </span>
                        <span className="font-semibold text-cyan-200">{speed} px/s</span>
                      </div>
                      <input
                        type="range"
                        min={MIN_SPEED}
                        max={MAX_SPEED}
                        step={2}
                        value={speed}
                        onChange={(event) => setSpeed(clampSpeed(Number(event.target.value)))}
                        className="h-2 w-full cursor-pointer accent-cyan-400"
                      />
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>

            <div className="mt-2 rounded-lg border border-[rgba(148,163,184,0.3)] bg-[rgba(15,23,42,0.55)] px-2.5 py-2 text-[10px]">
              <p>Scroll progress: {progress.toFixed(1)}%</p>
              <p className="text-[rgba(248,250,252,0.58)]">Tip: add ?autodemo=1&autospeed=110 for fast expo autoplay.</p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
