'use client';

import { motion } from 'framer-motion';
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

export default function PresentationModeSwitcher() {
  const { selectedMode, effectiveMode, motionTier, reducedMotion, setSelectedMode } = usePresentationMode();

  return (
    <motion.aside
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, delay: 0.4 }}
      className="fixed bottom-4 right-4 z-[65] w-[min(92vw,340px)] rounded-2xl border border-[rgba(0,212,255,0.28)] bg-[rgba(2,6,23,0.88)] p-3 shadow-[0_0_30px_rgba(0,212,255,0.16)] backdrop-blur-xl"
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
  );
}
