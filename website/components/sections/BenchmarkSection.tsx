'use client';

import { motion, useInView } from 'framer-motion';
import { useMemo, useRef } from 'react';
import {
  baselineSnapshot,
  EVIDENCE_AS_OF,
  evidenceMetrics,
  executedTestRunLedger,
  karpathyComparisonRubricWeights,
  phaseGateSnapshot,
} from '@/data/evidenceMetrics';

export default function BenchmarkSection() {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: '-100px' });

  const rubricRows = useMemo(
    () => [
      { label: 'Correctness', value: karpathyComparisonRubricWeights.correctness },
      { label: 'Reliability', value: karpathyComparisonRubricWeights.reliability },
      { label: 'Human Effort', value: karpathyComparisonRubricWeights.humanEffort },
      { label: 'Security/Ops', value: karpathyComparisonRubricWeights.securityOps },
      { label: 'Cost', value: karpathyComparisonRubricWeights.cost },
      { label: 'Reproducibility', value: karpathyComparisonRubricWeights.reproducibility },
    ],
    [],
  );

  const autogitStatus = phaseGateSnapshot.finalSuccess ? 'PASS' : 'NEEDS FIXES';
  const autogitStatusColor = phaseGateSnapshot.finalSuccess ? '#10B981' : '#F59E0B';

  const laneCounts = useMemo(() => {
    return executedTestRunLedger.reduce(
      (acc, row) => {
        if (row.lane === 'Auto-GIT run result') {
          acc.runResult += 1;
        } else if (row.lane === 'Auto-GIT E2E snapshot') {
          acc.e2eSnapshot += 1;
        } else if (row.lane === 'Karpathy baseline') {
          acc.baseline += 1;
        } else if (row.lane === 'Comparison snapshot') {
          acc.comparison += 1;
        }

        return acc;
      },
      {
        runResult: 0,
        e2eSnapshot: 0,
        baseline: 0,
        comparison: 0,
      },
    );
  }, []);

  const getStatusClass = (status: 'PASS' | 'NEEDS_FIXES' | 'MIXED') => {
    if (status === 'PASS') {
      return 'text-emerald-300';
    }

    if (status === 'MIXED') {
      return 'text-amber-300';
    }

    return 'text-rose-300';
  };

  return (
    <section className="relative py-24 lg:py-32" ref={ref}>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <motion.div
          initial={{ opacity: 0, y: 28 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.58 }}
          className="text-center mb-12"
        >
          <h2 className="font-orbitron font-bold text-3xl md:text-5xl mb-4 bg-gradient-to-r from-[#22D3EE] to-[#7C3AED] bg-clip-text text-transparent">
            Science Expo Benchmark Arena
          </h2>
          <p className="mx-auto max-w-4xl text-lg text-[rgba(248,250,252,0.72)]">
            Objective comparison lane: Auto-GIT pipeline vs Karpathy-style baseline workflow using the same test case and scoring rubric.
          </p>
        </motion.div>

        <div className="grid gap-6 lg:grid-cols-2">
          <motion.div
            initial={{ opacity: 0, x: -22 }}
            animate={isInView ? { opacity: 1, x: 0 } : {}}
            transition={{ duration: 0.45, delay: 0.1 }}
            className="rounded-2xl border border-[rgba(0,212,255,0.25)] bg-[rgba(2,6,23,0.78)] p-6"
          >
            <h3 className="font-orbitron text-lg text-[#00D4FF] mb-3">Auto-GIT Current Snapshot</h3>
            <div className="space-y-2 text-sm text-[rgba(248,250,252,0.72)]">
              <p>
                Pipeline nodes: <span className="text-[#22D3EE] font-semibold">{evidenceMetrics.pipelineNodes.value}</span>
              </p>
              <p>
                Error-memory entries: <span className="text-[#A78BFA] font-semibold">{evidenceMetrics.errorMemoryEntries.value}</span>
              </p>
              <p>
                Unit tests collected: <span className="text-[#F59E0B] font-semibold">{evidenceMetrics.unitTestsCollected.value}</span>
              </p>
              <p>
                Latest phase: <span className="text-[#CBD5E1] font-semibold">{phaseGateSnapshot.stage}</span>
              </p>
              <p>
                Latest hard failures: <span className="text-[#FB7185] font-semibold">{phaseGateSnapshot.hardFailures}</span>
              </p>
              <p>
                Run duration (s): <span className="text-[#22D3EE] font-semibold">{phaseGateSnapshot.durationSeconds}</span>
              </p>
              <p>
                Files generated: <span className="text-[#A78BFA] font-semibold">{phaseGateSnapshot.outputFilesGenerated}</span>
              </p>
              <p>
                Quality gate reason:{' '}
                <span className="text-[#FCA5A5] font-semibold">{phaseGateSnapshot.qualityGateReason}</span>
              </p>
              <p>
                Status:{' '}
                <span className="font-semibold" style={{ color: autogitStatusColor }}>
                  {autogitStatus}
                </span>
              </p>
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, x: 22 }}
            animate={isInView ? { opacity: 1, x: 0 } : {}}
            transition={{ duration: 0.45, delay: 0.2 }}
            className="rounded-2xl border border-[rgba(124,58,237,0.28)] bg-[rgba(2,6,23,0.78)] p-6"
          >
            <h3 className="font-orbitron text-lg text-[#A78BFA] mb-3">Karpathy-Style Baseline Lane</h3>
            <div className="space-y-2 text-sm text-[rgba(248,250,252,0.72)]">
              <p>
                Baseline mode: <span className="text-[#C4B5FD] font-semibold">{baselineSnapshot.mode}</span>
              </p>
              <p>
                Runtime (s): <span className="text-[#A78BFA] font-semibold">{baselineSnapshot.durationSeconds}</span>
              </p>
              <p>
                Syntax/runtime checks:{' '}
                <span className="text-[#22D3EE] font-semibold">
                  syntax={String(baselineSnapshot.syntaxOk)}, runtime={String(baselineSnapshot.runtimeOk)}
                </span>
              </p>
              <p>
                Fallback path used:{' '}
                <span className="text-[#F59E0B] font-semibold">{String(baselineSnapshot.fallbackUsed)}</span>
              </p>
              <p>Comparison framing: workflow-vs-workflow, not person-vs-person.</p>
              <p>Shared test case: Todo app with API + CLI + validation requirements.</p>
              <p>Measurement output: runtime, correctness, reliability, and reproducibility.</p>
              <p className="text-[rgba(248,250,252,0.56)]">{baselineSnapshot.fallbackReason}.</p>
            </div>
          </motion.div>
        </div>

        <motion.div
          initial={{ opacity: 0, y: 24 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.45, delay: 0.25 }}
          className="mt-6 rounded-2xl border border-[rgba(34,211,238,0.2)] bg-[rgba(3,7,18,0.8)] p-6"
        >
          <h3 className="font-orbitron text-[#22D3EE] text-base mb-3">Scoring Rubric (100 points)</h3>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {rubricRows.map((row) => (
              <div key={row.label} className="rounded-lg border border-[rgba(148,163,184,0.2)] bg-[rgba(15,23,42,0.6)] px-3 py-2 text-sm text-[rgba(248,250,252,0.75)]">
                <span className="font-semibold text-white">{row.label}</span>
                <span className="ml-2 text-[#22D3EE]">{Math.round(row.value * 100)}%</span>
              </div>
            ))}
          </div>

          <p className="mt-4 text-xs text-[rgba(248,250,252,0.54)]">
            Evidence snapshot date: {EVIDENCE_AS_OF}. Source metrics from {evidenceMetrics.pipelineNodes.source},{' '}
            {evidenceMetrics.errorMemoryEntries.source}, {phaseGateSnapshot.source}, and {baselineSnapshot.source}.
          </p>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 24 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.45, delay: 0.35 }}
          className="mt-6 rounded-2xl border border-[rgba(148,163,184,0.25)] bg-[rgba(2,6,23,0.82)] p-6"
        >
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h3 className="font-orbitron text-base text-sky-200">Executed Test Run Ledger (Artifact-Backed)</h3>
            <span className="rounded-md border border-[rgba(56,189,248,0.35)] bg-[rgba(56,189,248,0.14)] px-3 py-1 text-xs font-semibold text-cyan-200">
              {executedTestRunLedger.length} run artifacts listed
            </span>
          </div>

          <div className="mt-3 flex flex-wrap gap-2 text-xs text-[rgba(248,250,252,0.8)]">
            <span className="rounded-md border border-[rgba(148,163,184,0.32)] bg-[rgba(15,23,42,0.65)] px-2.5 py-1">
              Auto-GIT run_result: {laneCounts.runResult}
            </span>
            <span className="rounded-md border border-[rgba(148,163,184,0.32)] bg-[rgba(15,23,42,0.65)] px-2.5 py-1">
              E2E snapshots: {laneCounts.e2eSnapshot}
            </span>
            <span className="rounded-md border border-[rgba(148,163,184,0.32)] bg-[rgba(15,23,42,0.65)] px-2.5 py-1">
              Karpathy baseline: {laneCounts.baseline}
            </span>
            <span className="rounded-md border border-[rgba(148,163,184,0.32)] bg-[rgba(15,23,42,0.65)] px-2.5 py-1">
              Comparison snapshots: {laneCounts.comparison}
            </span>
          </div>

          <div className="mt-4 overflow-x-auto rounded-xl border border-[rgba(148,163,184,0.2)]">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="border-b border-[rgba(148,163,184,0.2)] bg-[rgba(15,23,42,0.85)] text-left">
                  <th className="px-3 py-2 font-orbitron text-[11px] text-slate-300">Artifact</th>
                  <th className="px-3 py-2 font-orbitron text-[11px] text-slate-300">Lane</th>
                  <th className="px-3 py-2 font-orbitron text-[11px] text-slate-300">Executed</th>
                  <th className="px-3 py-2 font-orbitron text-[11px] text-slate-300">Status</th>
                  <th className="px-3 py-2 font-orbitron text-[11px] text-slate-300">Summary</th>
                </tr>
              </thead>
              <tbody>
                {executedTestRunLedger.map((row) => (
                  <tr key={row.artifact} className="border-b border-[rgba(148,163,184,0.12)] align-top">
                    <td className="px-3 py-2 font-mono text-xs text-cyan-200">{row.artifact}</td>
                    <td className="px-3 py-2 text-xs text-slate-300">{row.lane}</td>
                    <td className="px-3 py-2 text-xs text-slate-400">{row.executedAt}</td>
                    <td className={`px-3 py-2 text-xs font-semibold ${getStatusClass(row.status)}`}>{row.status}</td>
                    <td className="px-3 py-2 text-xs text-[rgba(248,250,252,0.72)]">{row.summary}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </motion.div>
      </div>
    </section>
  );
}
