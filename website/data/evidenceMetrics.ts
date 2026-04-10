export const EVIDENCE_AS_OF = "2026-04-09";

export type EvidenceMetric = {
  key: string;
  label: string;
  value: number | string;
  source: string;
  note?: string;
};

export const evidenceMetrics: Record<string, EvidenceMetric> = {
  pipelineNodes: {
    key: "pipelineNodes",
    label: "Pipeline nodes",
    value: 19,
    source: "src/langraph_pipeline/workflow_enhanced.py",
    note: "Counted from workflow.add_node(...) registrations",
  },
  unitTestsCollected: {
    key: "unitTestsCollected",
    label: "Unit tests collected",
    value: 268,
    source: "tests/unit + pytest collection output",
    note: "Collected via .venv pytest --collect-only on 2026-04-09",
  },
  errorMemoryEntries: {
    key: "errorMemoryEntries",
    label: "Error-memory entries",
    value: 6044,
    source: "data/memory/codegen_errors.jsonl",
    note: "Counted by JSONL line count",
  },
  runArtifactsTracked: {
    key: "runArtifactsTracked",
    label: "Run artifacts tracked",
    value: 69,
    source: "logs + output run_result/phase_gate/e2e JSON artifacts",
    note: "Counted from repository root on 2026-04-10",
  },
  outputCheckpointFiles: {
    key: "outputCheckpointFiles",
    label: "Checkpoint files logged",
    value: 82,
    source: "logs/checkpoint_*.json",
    note: "Historical checkpoint snapshots across runs",
  },
  outputPipelineTraceFiles: {
    key: "outputPipelineTraceFiles",
    label: "Pipeline trace logs",
    value: 189,
    source: "logs/pipeline_trace_*.jsonl",
    note: "End-to-end execution traces",
  },
  outputE2ELogs: {
    key: "outputE2ELogs",
    label: "E2E log files",
    value: 12,
    source: "logs/e2e_*.(txt|log|json)",
    note: "Captured E2E run transcripts",
  },
  outputPytestLogs: {
    key: "outputPytestLogs",
    label: "Pytest logs",
    value: 2,
    source: "logs/pytest*.(txt|log)",
    note: "Latest archived pytest output logs",
  },
  outputTestRunVolumeTotal: {
    key: "outputTestRunVolumeTotal",
    label: "Output/test-run volume",
    value: 354,
    source: "Aggregate of run JSON + checkpoints + traces + E2E logs + pytest logs",
    note: "69 + 82 + 189 + 12 + 2",
  },
  sourcePythonLoc: {
    key: "sourcePythonLoc",
    label: "Python LOC in src",
    value: 68927,
    source: "src/**/*.py",
    note: "Summed from current workspace source files",
  },
};

export const phaseGateSnapshot = {
  asOfUnix: 1775720173,
  stage: "saved_locally_tests_failed",
  testsPassed: false,
  smokeTestPassed: true,
  hardFailures: 3,
  softWarnings: 24,
  correctnessPassed: false,
  publishEligible: false,
  finalSuccess: false,
  qualityGateReason: "correctness_gate_failed",
  durationSeconds: 1547.021,
  outputFilesGenerated: 8,
  runtimeFilesGenerated: 5,
  source:
    "logs/run_result_e2e_moderate_1775720173_20260409_130613.json + output/e2e_todo_app/e2e_result.json",
};

export const baselineSnapshot = {
  mode: "karpathy_style_single_shot",
  durationSeconds: 1.018,
  generationOk: true,
  syntaxOk: true,
  runtimeOk: true,
  generatedLines: 24,
  fallbackUsed: true,
  fallbackReason: "LLM unavailable; generated deterministic minimal baseline code",
  source: "output/benchmark_baseline/baseline_result.json",
};

export const karpathyComparisonRubricWeights = {
  correctness: 0.35,
  reliability: 0.2,
  humanEffort: 0.15,
  securityOps: 0.1,
  cost: 0.1,
  reproducibility: 0.1,
};
