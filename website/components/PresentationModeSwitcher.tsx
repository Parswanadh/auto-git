'use client';

import { AnimatePresence, motion } from 'framer-motion';
import { ChevronDown, ChevronUp, SlidersHorizontal } from 'lucide-react';
import { useEffect, useState } from 'react';
import { usePresentationMode, type PresentationMode } from '@/components/PresentationModeProvider';

const modeLabels: Record<PresentationMode, { title: string; subtitle: string }> = {
  frontier: {
    title: 'Frontier',
    subtitle: 'Signature visual mode',
  },
  evidence: {
    title: 'Evidence',
    subtitle: 'Judge-first clarity mode',
  },
  safe: {
    title: 'Safe',
    subtitle: 'Low-motion fallback mode',
  },
};

const modes: PresentationMode[] = ['frontier', 'evidence', 'safe'];
const COLLAPSE_KEY = 'autogit:presentation-mode-switcher-open';

export default function PresentationModeSwitcher() {
  const { selectedMode, effectiveMode, motionTier, reducedMotion, setSelectedMode } = usePresentationMode();
  const [panelOpen, setPanelOpen] = useState(false);

  useEffect(() => {
    try {
      const stored = window.localStorage.getItem(COLLAPSE_KEY);
      if (stored === '1') {
        setPanelOpen(true);
      }
      if (stored === '0') {
        setPanelOpen(false);
      }
    } catch {
      // Ignore local storage read failures.
    }
  }, []);

  useEffect(() => {
    window.localStorage.setItem(COLLAPSE_KEY, panelOpen ? '1' : '0');
  }, [panelOpen]);

  return (
    <div className="fixed bottom-4 right-4 z-[65] flex flex-col items-end gap-2">
      <motion.button
        type="button"
        onClick={() => setPanelOpen((prev) => !prev)}
        className="rounded-xl border border-[rgba(0,212,255,0.35)] bg-[rgba(2,6,23,0.9)] px-3 py-2 text-xs font-semibold text-cyan-200 shadow-[0_0_20px_rgba(0,212,255,0.15)]"
        whileHover={{ y: -1, scale: 1.02 }}
        whileTap={{ scale: 0.98 }}
      >
        <span className="inline-flex items-center gap-2">
          <SlidersHorizontal className="h-4 w-4" />
          {panelOpen ? 'Hide Modes' : 'Demo Modes'}
          {panelOpen ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
        </span>
      </motion.button>

      <AnimatePresence>
        {panelOpen && (
          <motion.aside
            initial={{ opacity: 0, y: 14, scale: 0.97 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 10, scale: 0.98 }}
            transition={{ duration: 0.28, ease: [0.22, 1, 0.36, 1] }}
            className="w-[min(92vw,340px)] rounded-2xl border border-[rgba(0,212,255,0.28)] bg-[rgba(2,6,23,0.88)] p-3 shadow-[0_0_30px_rgba(0,212,255,0.16)] backdrop-blur-xl"
            aria-label="Presentation mode switcher"
          >
            <p className="font-orbitron text-[11px] uppercase tracking-[0.16em] text-[rgba(248,250,252,0.74)]">
              Showcase Modes
            </p>
            <p className="mt-1 text-[11px] text-[rgba(248,250,252,0.62)]">
              Switch live between premium and fallback designs.
            </p>

            <div className="mt-3 grid grid-cols-3 gap-1.5">
              {modes.map((mode) => {
                const active = selectedMode === mode;

                return (
                  <button
                    key={mode}
                    type="button"
                    onClick={() => setSelectedMode(mode)}
                    className={`rounded-xl border px-2 py-2 text-left transition-all ${
                      active
                        ? 'border-[rgba(0,212,255,0.6)] bg-[rgba(0,212,255,0.2)] text-white shadow-[0_0_16px_rgba(0,212,255,0.2)]'
                        : 'border-[rgba(148,163,184,0.25)] bg-[rgba(15,23,42,0.62)] text-[rgba(248,250,252,0.7)] hover:border-[rgba(0,212,255,0.4)] hover:text-white'
                    }`}
                  >
                    <span className="block font-orbitron text-[10px] uppercase tracking-[0.12em]">
                      {modeLabels[mode].title}
                    </span>
                    <span className="mt-0.5 block text-[10px] leading-tight text-[rgba(248,250,252,0.58)]">
                      {modeLabels[mode].subtitle}
                    </span>
                  </button>
                );
              })}
            </div>

            <div className="mt-3 rounded-xl border border-[rgba(148,163,184,0.26)] bg-[rgba(15,23,42,0.45)] px-2.5 py-2 text-[10px] text-[rgba(248,250,252,0.66)]">
              <p>
                Effective mode: <span className="font-semibold text-[rgba(248,250,252,0.88)]">{modeLabels[effectiveMode].title}</span>
              </p>
              <p>
                Motion tier: <span className="font-semibold text-[rgba(248,250,252,0.88)]">{motionTier}</span>
                {reducedMotion ? ' (system reduced-motion active)' : ''}
              </p>
            </div>
          </motion.aside>
        )}
      </AnimatePresence>
    </div>
  );
}
