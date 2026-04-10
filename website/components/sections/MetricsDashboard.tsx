'use client';

import React, { useRef, useState } from 'react';
import { motion, useInView } from 'framer-motion';
import CountUp from 'react-countup';
import { EVIDENCE_AS_OF, evidenceMetrics, phaseGateSnapshot } from '@/data/evidenceMetrics';
import { usePresentationMode } from '@/components/PresentationModeProvider';

const pipelineMetrics = [
  { value: Number(evidenceMetrics.sourcePythonLoc.value), label: 'Python LOC in src', suffix: '', color: '#00D4FF' },
  { value: Number(evidenceMetrics.pipelineNodes.value), label: 'Orchestrated pipeline nodes', suffix: '', color: '#10B981' },
  { value: Number(evidenceMetrics.runArtifactsTracked.value), label: 'Run artifacts tracked', suffix: '', color: '#F59E0B' },
  { value: Number(evidenceMetrics.unitTestsCollected.value), label: 'Collected unit tests', suffix: '', color: '#3B82F6' },
  { value: Number(evidenceMetrics.errorMemoryEntries.value), label: 'Error-memory entries', suffix: '', color: '#7C3AED' },
  { value: phaseGateSnapshot.hardFailures, label: 'Latest phase-gate hard failures', suffix: '', color: '#EF4444' },
];

const qualityMetrics = [
  { value: phaseGateSnapshot.testsPassed ? 1 : 0, label: 'Latest tests passed (1=yes)', color: '#10B981' },
  { value: phaseGateSnapshot.smokeTestPassed ? 1 : 0, label: 'Latest smoke test passed (1=yes)', color: '#00D4FF' },
  { value: phaseGateSnapshot.correctnessPassed ? 1 : 0, label: 'Latest correctness passed (1=yes)', color: '#7C3AED' },
  { value: phaseGateSnapshot.publishEligible ? 1 : 0, label: 'Latest publish-eligible (1=yes)', color: '#F59E0B' },
  { value: phaseGateSnapshot.finalSuccess ? 1 : 0, label: 'Latest final success (1=yes)', color: '#EF4444' },
];

const infraMetrics = [
  { value: Number(evidenceMetrics.pipelineNodes.value), label: 'Execution-policy wrapped nodes', color: '#3B82F6' },
  { value: 5, label: 'Validation stages', color: '#7C3AED' },
  { value: 4, label: 'Model profiles', color: '#10B981' },
  { value: Number(evidenceMetrics.runArtifactsTracked.value), label: 'Traceable run artifacts', color: '#F59E0B' },
  { value: Number(evidenceMetrics.unitTestsCollected.value), label: 'Unit test coverage points', color: '#00D4FF' },
];

const outputRunVolumeMetrics = [
  { value: Number(evidenceMetrics.outputTestRunVolumeTotal.value), label: 'Total output/test-run artifacts', color: '#22D3EE' },
  { value: Number(evidenceMetrics.runArtifactsTracked.value), label: 'Run JSON artifacts', color: '#38BDF8' },
  { value: Number(evidenceMetrics.outputCheckpointFiles.value), label: 'Checkpoint snapshots', color: '#A78BFA' },
  { value: Number(evidenceMetrics.outputPipelineTraceFiles.value), label: 'Pipeline trace files', color: '#10B981' },
  { value: Number(evidenceMetrics.outputE2ELogs.value), label: 'E2E log files', color: '#F59E0B' },
  { value: Number(evidenceMetrics.outputPytestLogs.value), label: 'Pytest log files', color: '#3B82F6' },
];

function MetricCard({ value, label, suffix = '', prefix = '', color, delay, isVisible, animateNumbers, durationFactor }: {
  value: number;
  label: string;
  suffix?: string;
  prefix?: string;
  color: string;
  delay: number;
  isVisible: boolean;
  animateNumbers: boolean;
  durationFactor: number;
}) {
  const displayValue = value.toLocaleString();

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={isVisible ? { opacity: 1, y: 0 } : {}}
      transition={{ duration: 0.4, delay }}
      className="bg-[rgba(3,7,18,0.8)] border border-[rgba(0,212,255,0.12)] rounded-lg md:rounded-xl p-3 sm:p-4 md:p-5 text-center hover-lift"
    >
      <div className="text-2xl sm:text-3xl md:text-4xl font-bold font-orbitron mb-2" style={{ color }}>
        {prefix}
        {isVisible && animateNumbers ? (
          <CountUp end={value} duration={1.7 * durationFactor} separator="," />
        ) : (
          displayValue
        )}
        {suffix}
      </div>
      <div className="text-xs text-[rgba(248,250,252,0.5)]">{label}</div>
    </motion.div>
  );
}

function MetricsDashboard() {
  const { motionTier, effectiveMode } = usePresentationMode();
  const ref = useRef(null);
  const [outputPanelOpen, setOutputPanelOpen] = useState(true);
  const isInView = useInView(ref, { once: true, margin: '-100px' });
  const animateNumbers = motionTier !== 'low';
  const durationFactor = effectiveMode === 'evidence' ? 0.6 : 1;

  return (
    <section className="relative py-24 lg:py-32" ref={ref}>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.6 }}
          className="text-center mb-16"
        >
          <h2 className="font-orbitron font-bold text-3xl md:text-5xl mb-4 bg-gradient-to-r from-[#00D4FF] to-[#7C3AED] bg-clip-text text-transparent">
            The Numbers
          </h2>
          <p className="mx-auto max-w-3xl text-sm text-[rgba(248,250,252,0.58)]">
            Evidence snapshot date: {EVIDENCE_AS_OF}. Sources include
            {' '}
            <span className="text-[#00D4FF]">src/langraph_pipeline/workflow_enhanced.py</span>,
            {' '}
            <span className="text-[#00D4FF]">data/memory/codegen_errors.jsonl</span>,
            {' '}
            and
            {' '}
            <span className="text-[#00D4FF]">{phaseGateSnapshot.source}</span>.
          </p>
        </motion.div>

        {/* Pipeline Metrics */}
        <motion.h3
          initial={{ opacity: 0 }}
          animate={isInView ? { opacity: 1 } : {}}
          transition={{ delay: 0.2 }}
          className="font-orbitron font-semibold text-sm text-[rgba(248,250,252,0.4)] uppercase tracking-widest mb-4 text-center"
        >
          Pipeline Metrics
        </motion.h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-2 sm:gap-3 mb-8 sm:mb-12">
          {pipelineMetrics.map((m, i) => (
            <MetricCard
              key={m.label}
              {...m}
              delay={0.1 + i * 0.08}
              isVisible={isInView}
              animateNumbers={animateNumbers}
              durationFactor={durationFactor}
            />
          ))}
        </div>

        {/* Quality Metrics */}
        <motion.h3
          initial={{ opacity: 0 }}
          animate={isInView ? { opacity: 1 } : {}}
          transition={{ delay: 0.5 }}
          className="font-orbitron font-semibold text-sm text-[rgba(248,250,252,0.4)] uppercase tracking-widest mb-4 text-center"
        >
          Quality Metrics
        </motion.h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-2 sm:gap-3 mb-8 sm:mb-12">
          {qualityMetrics.map((m, i) => (
            <MetricCard
              key={m.label}
              {...m}
              delay={0.5 + i * 0.08}
              isVisible={isInView}
              animateNumbers={animateNumbers}
              durationFactor={durationFactor}
            />
          ))}
        </div>

        {/* Infrastructure Metrics */}
        <motion.h3
          initial={{ opacity: 0 }}
          animate={isInView ? { opacity: 1 } : {}}
          transition={{ delay: 0.8 }}
          className="font-orbitron font-semibold text-sm text-[rgba(248,250,252,0.4)] uppercase tracking-widest mb-4 text-center"
        >
          Infrastructure Metrics
        </motion.h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-2 sm:gap-3">
          {infraMetrics.map((m, i) => (
            <MetricCard
              key={m.label}
              {...m}
              delay={0.8 + i * 0.08}
              isVisible={isInView}
              animateNumbers={animateNumbers}
              durationFactor={durationFactor}
            />
          ))}
        </div>

        {/* Output/Test Run Volume */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ delay: 1.05, duration: 0.45 }}
          className="mt-8 rounded-xl border border-[rgba(34,211,238,0.22)] bg-[rgba(2,6,23,0.72)] p-4 sm:p-5"
        >
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h3 className="font-orbitron font-semibold text-sm uppercase tracking-widest text-[rgba(248,250,252,0.7)]">
              Output and Test Run Volume
            </h3>
            <button
              type="button"
              onClick={() => setOutputPanelOpen((prev) => !prev)}
              className="rounded-lg border border-[rgba(56,189,248,0.4)] bg-[rgba(56,189,248,0.12)] px-3 py-1.5 text-xs font-semibold text-cyan-200 transition-colors hover:bg-[rgba(56,189,248,0.22)]"
            >
              {outputPanelOpen ? 'Collapse' : 'Expand'}
            </button>
          </div>

          {outputPanelOpen && (
            <>
              <p className="mt-2 text-xs text-[rgba(248,250,252,0.6)]">
                Large historical run volume is now surfaced directly in the graph: run results, checkpoints, traces, and test logs.
              </p>
              <div className="mt-4 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2 sm:gap-3">
                {outputRunVolumeMetrics.map((m, i) => (
                  <MetricCard
                    key={m.label}
                    value={m.value}
                    label={m.label}
                    color={m.color}
                    delay={1.12 + i * 0.06}
                    isVisible={isInView}
                    animateNumbers={animateNumbers}
                    durationFactor={durationFactor}
                  />
                ))}
              </div>
            </>
          )}
        </motion.div>
      </div>
    </section>
  );
}

export default React.memo(MetricsDashboard);
