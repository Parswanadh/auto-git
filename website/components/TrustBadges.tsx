'use client';

import { motion } from 'framer-motion';
import { EVIDENCE_AS_OF, evidenceMetrics } from '@/data/evidenceMetrics';

const badges = [
  {
    icon: '✓',
    text: 'Pipeline Orchestration Verified',
    color: '#10B981',
  },
  {
    icon: '⚙️',
    text: `${evidenceMetrics.pipelineNodes.value} Nodes Registered`,
    color: '#00D4FF',
  },
  {
    icon: '🧠',
    text: `${evidenceMetrics.errorMemoryEntries.value} Error-Memory Entries`,
    color: '#7C3AED',
  },
  {
    icon: '🧪',
    text: `${evidenceMetrics.unitTestsCollected.value} Unit Tests Collected`,
    color: '#F59E0B',
  },
  {
    icon: '📊',
    text: `${evidenceMetrics.outputTestRunVolumeTotal.value} Output/Test Artifacts Logged`,
    color: '#22D3EE',
  },
];

export default function TrustBadges() {
  return (
    <motion.div
      className="mx-auto mb-6 flex max-w-6xl flex-wrap items-center justify-center gap-3"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, delay: 0.25 }}
      aria-label="Evidence-backed trust badges"
    >
      {badges.map((badge, index) => (
        <motion.div
          key={badge.text}
          className="flex items-center gap-2 rounded-full border px-4 py-2 text-xs font-semibold md:text-sm"
          style={{
            borderColor: `${badge.color}40`,
            color: badge.color,
            background: `${badge.color}12`,
          }}
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.38, delay: 0.32 + index * 0.08 }}
          whileHover={{ scale: 1.03, y: -1 }}
        >
          <span>{badge.icon}</span>
          <span>{badge.text}</span>
        </motion.div>
      ))}
      <span className="ml-2 text-xs text-[rgba(248,250,252,0.52)]">Evidence snapshot: {EVIDENCE_AS_OF}</span>
    </motion.div>
  );
}
