'use client';

import { motion } from 'framer-motion';
import AnimatedPipelineGraph from '@/components/AnimatedPipelineGraph';
import { EVIDENCE_AS_OF, evidenceMetrics } from '@/data/evidenceMetrics';

export default function PipelineSection() {
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
          This live graph mirrors the real 19-stage Auto-GIT flow. Nodes and edges fire continuously to represent debate loops,
          validation gates, and autonomous repair cycles.
        </motion.p>

        <motion.div
          initial={{ opacity: 0, y: 24 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: '-80px' }}
          transition={{ duration: 0.55 }}
        >
          <AnimatedPipelineGraph />
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
