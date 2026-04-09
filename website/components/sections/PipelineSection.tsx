'use client';

import { motion } from 'framer-motion';
import AnimatedPipelineGraph from '@/components/AnimatedPipelineGraph';
import { EVIDENCE_AS_OF, evidenceMetrics } from '@/data/evidenceMetrics';
import { usePresentationMode } from '@/components/PresentationModeProvider';

const SAFE_STAGE_GROUPS = [
  {
    title: 'Discovery',
    stages: ['Requirements extraction', 'Research', 'Perspective generation', 'Problem extraction'],
  },
  {
    title: 'Synthesis',
    stages: ['Solution generation', 'Critique', 'Consensus checks', 'Solution selection', 'Architecture spec'],
  },
  {
    title: 'Execution',
    stages: ['Code generation', 'Review', 'Testing', 'Feature verification', 'Strategy + fixing', 'Smoke test', 'Self eval', 'Goal eval', 'Git publishing'],
  },
];

function StaticPipelineFallback() {
  return (
    <div className="rounded-2xl border border-[rgba(14,165,233,0.28)] bg-[rgba(2,6,23,0.78)] p-5 md:p-7">
      <p className="mb-4 text-sm text-[rgba(248,250,252,0.7)]">
        Safe mode fallback: static pipeline map for low-motion and low-power demo conditions.
      </p>
      <div className="grid gap-4 md:grid-cols-3">
        {SAFE_STAGE_GROUPS.map((group, index) => (
          <div
            key={group.title}
            className="rounded-xl border border-[rgba(148,163,184,0.3)] bg-[rgba(15,23,42,0.55)] p-4"
          >
            <p className="mb-2 font-orbitron text-xs uppercase tracking-[0.12em] text-cyan-300">
              {index + 1}. {group.title}
            </p>
            <ul className="space-y-1 text-sm text-[rgba(248,250,252,0.8)]">
              {group.stages.map((stage) => (
                <li key={stage}>• {stage}</li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function PipelineSection() {
  const { motionTier } = usePresentationMode();
  const isLowMotion = motionTier === 'low';

  return (
    <section className="relative py-32">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <motion.h2
          className="font-orbitron font-bold text-4xl md:text-5xl mb-4 bg-gradient-to-r from-[#00D4FF] to-[#7C3AED] bg-clip-text text-transparent text-center"
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: '-100px' }}
          transition={{ duration: 0.6 }}
        >
          Pipeline Architecture
        </motion.h2>

        <motion.p
          className="mx-auto mb-8 max-w-4xl text-center text-lg text-[rgba(248,250,252,0.72)]"
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.45, delay: 0.15 }}
        >
          This section mirrors the real 19-stage Auto-GIT flow across discovery, synthesis, and execution loops.
          {isLowMotion
            ? ' Safe mode is active, so a static architecture map is shown for maximum readability.'
            : ' Live edge activations represent debate loops, validation gates, and autonomous repair cycles.'}
        </motion.p>

        <motion.div
          initial={{ opacity: 0, y: 24 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: '-80px' }}
          transition={{ duration: 0.55 }}
        >
          {isLowMotion ? <StaticPipelineFallback /> : <AnimatedPipelineGraph />}
        </motion.div>

        <div className="mt-6 rounded-xl border border-[rgba(0,212,255,0.2)] bg-[rgba(2,6,23,0.68)] px-4 py-3 text-center text-sm text-[rgba(248,250,252,0.72)]">
          Evidence snapshot ({EVIDENCE_AS_OF}): {evidenceMetrics.pipelineNodes.value} nodes from
          {' '}
          <span className="font-semibold text-[#00D4FF]">{evidenceMetrics.pipelineNodes.source}</span>
        </div>
      </div>
    </section>
  );
}
