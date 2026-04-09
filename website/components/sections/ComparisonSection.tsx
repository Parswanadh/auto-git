'use client';

import { motion, useInView } from 'framer-motion';
import { useRef } from 'react';
import {
  baselineSnapshot,
  EVIDENCE_AS_OF,
  evidenceMetrics,
  karpathyComparisonRubricWeights,
  phaseGateSnapshot,
} from '@/data/evidenceMetrics';

const features = [
  {
    feature: 'Workflow topology',
    baseline: 'Single-shot / low-automation coding loop',
    autogit: `${evidenceMetrics.pipelineNodes.value}-node orchestrated pipeline`,
  },
  {
    feature: 'Research strategy',
    baseline: 'Human-guided iterative research',
    autogit: 'Automated research + debate + synthesis nodes',
  },
  {
    feature: 'Repair loop',
    baseline: 'Manual retries and edits',
    autogit: 'Strategy -> Fix -> Re-test autonomous loop',
  },
  {
    feature: 'Persistent memory',
    baseline: 'Ad-hoc notes',
    autogit: `${evidenceMetrics.errorMemoryEntries.value} JSONL error-memory entries`,
  },
  {
    feature: 'Validation envelope',
    baseline: 'Task-dependent manual checks',
    autogit: 'Multi-stage static + runtime verification',
  },
  {
    feature: 'Current reliability snapshot',
    baseline: `duration=${baselineSnapshot.durationSeconds}s, runtime_ok=${String(baselineSnapshot.runtimeOk)}, fallback=${String(baselineSnapshot.fallbackUsed)}`,
    autogit: `phase=${phaseGateSnapshot.stage}, hard_failures=${phaseGateSnapshot.hardFailures}`,
  },
  {
    feature: 'Trace artifacts',
    baseline: 'Runner-dependent',
    autogit: `${evidenceMetrics.runArtifactsTracked.value} run JSON artifacts tracked`,
  },
];

export default function ComparisonSection() {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: '-100px' });

  return (
    <section className="relative py-24 lg:py-32" ref={ref}>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.6 }}
          className="text-center mb-12"
        >
          <h2 className="font-orbitron font-bold text-3xl md:text-5xl mb-4 bg-gradient-to-r from-[#00D4FF] to-[#7C3AED] bg-clip-text text-transparent">
            Auto-GIT vs Karpathy-Style Workflow
          </h2>
          <p className="mx-auto max-w-4xl text-sm text-[rgba(248,250,252,0.58)]">
            This section compares workflow styles, not people. Baseline framing uses publicly documented
            Karpathy-style iterative coding practices and benchmark methodology references.
            Evidence snapshot date: {EVIDENCE_AS_OF}.
          </p>
        </motion.div>

        {/* Comparison Table */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.6, delay: 0.2 }}
          className="overflow-x-auto bg-[rgba(3,7,18,0.8)] border border-[rgba(0,212,255,0.15)] rounded-xl"
        >
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[rgba(0,212,255,0.2)]">
                <th className="p-4 text-left text-[rgba(248,250,252,0.5)] font-orbitron text-xs uppercase tracking-wider">
                  Axis
                </th>
                <th className="p-4 text-center text-[rgba(248,250,252,0.4)] font-orbitron text-xs">
                  Karpathy-style baseline
                </th>
                <th className="p-4 text-center font-orbitron text-xs" style={{ color: '#00D4FF' }}>
                  Auto-GIT
                </th>
              </tr>
            </thead>
            <tbody>
              {features.map((row, i) => (
                <motion.tr
                  key={row.feature}
                  initial={{ opacity: 0, x: -10 }}
                  animate={isInView ? { opacity: 1, x: 0 } : {}}
                  transition={{ duration: 0.3, delay: 0.3 + i * 0.06 }}
                  className="border-b border-[rgba(0,212,255,0.05)] hover:bg-[rgba(0,212,255,0.03)] transition-colors"
                >
                  <td className="p-4 text-[rgba(248,250,252,0.7)] font-medium">{row.feature}</td>
                  <td className="p-4 text-center text-[rgba(248,250,252,0.4)] text-xs">{row.baseline}</td>
                  <td className="p-4 text-center text-[#10B981] text-xs font-semibold">{row.autogit}</td>
                </motion.tr>
              ))}
            </tbody>
          </table>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.5, delay: 0.35 }}
          className="mt-6 rounded-xl border border-[rgba(0,212,255,0.15)] bg-[rgba(3,7,18,0.78)] p-4"
        >
          <p className="mb-2 text-sm text-[rgba(248,250,252,0.7)]">Science Expo rubric weights used for tomorrow&apos;s benchmark report:</p>
          <div className="grid gap-2 text-xs text-[rgba(248,250,252,0.62)] md:grid-cols-3">
            <div>Correctness: {Math.round(karpathyComparisonRubricWeights.correctness * 100)}%</div>
            <div>Reliability: {Math.round(karpathyComparisonRubricWeights.reliability * 100)}%</div>
            <div>Human effort: {Math.round(karpathyComparisonRubricWeights.humanEffort * 100)}%</div>
            <div>Security/Ops: {Math.round(karpathyComparisonRubricWeights.securityOps * 100)}%</div>
            <div>Cost: {Math.round(karpathyComparisonRubricWeights.cost * 100)}%</div>
            <div>Reproducibility: {Math.round(karpathyComparisonRubricWeights.reproducibility * 100)}%</div>
          </div>
        </motion.div>
      </div>
    </section>
  );
}
