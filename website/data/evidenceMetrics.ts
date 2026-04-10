export const EVIDENCE_AS_OF = "2026-04-10";

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
  outputTopLevelDirs: {
    key: "outputTopLevelDirs",
    label: "Output top-level directories",
    value: 60,
    source: "output/* directory scan",
    note: "Counted from repository root on 2026-04-10",
  },
  outputTopLevelTestDirs: {
    key: "outputTopLevelTestDirs",
    label: "Output test-oriented directories",
    value: 8,
    source: "output/* names matching test|e2e|benchmark",
    note: "benchmark_baseline, e2e_*, *_test, test_*",
  },
  outputTotalFiles: {
    key: "outputTotalFiles",
    label: "Output total files",
    value: 1067,
    source: "output/**/* recursive file scan",
    note: "All files under output/",
  },
  outputJsonFiles: {
    key: "outputJsonFiles",
    label: "Output JSON files",
    value: 23,
    source: "output/**/*.json",
    note: "Structured run and result artifacts",
  },
  outputMarkdownFiles: {
    key: "outputMarkdownFiles",
    label: "Output markdown files",
    value: 204,
    source: "output/**/*.md",
    note: "Reports, READMEs, and generated documentation",
  },
  outputPythonFiles: {
    key: "outputPythonFiles",
    label: "Output Python files",
    value: 552,
    source: "output/**/*.py",
    note: "Generated source and helper scripts",
  },
  outputResearchReports: {
    key: "outputResearchReports",
    label: "Output research reports",
    value: 69,
    source: "output/**/RESEARCH_REPORT.md",
    note: "Research reports captured across generated projects",
  },
  outputTestFiles: {
    key: "outputTestFiles",
    label: "Output test-related files",
    value: 107,
    source: "output/**/* names/paths matching test patterns",
    note: "Includes filenames and directories with test markers",
  },
  outputE2EJson: {
    key: "outputE2EJson",
    label: "Output E2E JSON files",
    value: 2,
    source: "output/**/e2e*.json",
    note: "Canonical E2E result snapshots",
  },
  outputBenchmarkFiles: {
    key: "outputBenchmarkFiles",
    label: "Output benchmark files",
    value: 2,
    source: "output/**/* names containing benchmark",
    note: "benchmark_comparison and benchmark_report",
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

export type TestRunLedgerEntry = {
  artifact: string;
  lane: "Auto-GIT run result" | "Auto-GIT E2E snapshot" | "Karpathy baseline" | "Comparison snapshot";
  executedAt: string;
  status: "PASS" | "NEEDS_FIXES" | "MIXED";
  summary: string;
};

export const executedTestRunLedger: TestRunLedgerEntry[] = [
  {
    artifact: "logs/run_result_lineage_smoke_1_20260331_094653.json",
    lane: "Auto-GIT run result",
    executedAt: "2026-03-31 09:47",
    status: "NEEDS_FIXES",
    summary: "lineage smoke run; ended at requirements_extracted; tests failed",
  },
  {
    artifact: "logs/run_result_e2e_moderate_1774925402_20260331_095229.json",
    lane: "Auto-GIT run result",
    executedAt: "2026-03-31 09:58",
    status: "NEEDS_FIXES",
    summary: "e2e moderate lane; stage=saved_locally_tests_failed",
  },
  {
    artifact: "logs/run_result_complex_archcap_20260331_101427_20260331_101431.json",
    lane: "Auto-GIT run result",
    executedAt: "2026-03-31 10:21",
    status: "NEEDS_FIXES",
    summary: "complex archcap lane; stage=architect_spec_complete; tests failed",
  },
  {
    artifact: "logs/run_result_e2e_moderate_1774971416_20260331_210657.json",
    lane: "Auto-GIT run result",
    executedAt: "2026-03-31 21:46",
    status: "NEEDS_FIXES",
    summary: "e2e moderate lane; contradiction_detected warning; tests failed",
  },
  {
    artifact: "logs/run_result_complex_perplexica_20260331_214807_20260331_214810.json",
    lane: "Auto-GIT run result",
    executedAt: "2026-03-31 22:48",
    status: "NEEDS_FIXES",
    summary: "complex perplexica lane; stage=saved_locally_tests_failed",
  },
  {
    artifact: "logs/run_result_e2e_moderate_1774978952_20260331_231232.json",
    lane: "Auto-GIT run result",
    executedAt: "2026-03-31 23:37",
    status: "NEEDS_FIXES",
    summary: "e2e moderate lane; quality_gate_reason=correctness_gate_failed",
  },
  {
    artifact: "logs/run_result_complex_perplexica_20260331_233931_20260331_233934.json",
    lane: "Auto-GIT run result",
    executedAt: "2026-04-01 00:43",
    status: "NEEDS_FIXES",
    summary: "complex perplexica rerun; stage=saved_locally_tests_failed",
  },
  {
    artifact: "logs/run_result_thread-01_run999.json",
    lane: "Auto-GIT run result",
    executedAt: "2026-04-09 13:03",
    status: "PASS",
    summary: "thread lane; stage=published; tests passed",
  },
  {
    artifact: "logs/run_result_e2e_moderate_1775720173_20260409_130613.json",
    lane: "Auto-GIT run result",
    executedAt: "2026-04-09 13:32",
    status: "NEEDS_FIXES",
    summary: "latest e2e moderate lane; stage=saved_locally_tests_failed",
  },
  {
    artifact: "output/e2e_todo_app/e2e_result_old_paid.json",
    lane: "Auto-GIT E2E snapshot",
    executedAt: "2026-04-09",
    status: "NEEDS_FIXES",
    summary: "old paid snapshot; tests failed; fix_attempts=12; self_eval=5",
  },
  {
    artifact: "output/e2e_todo_app/e2e_result.json",
    lane: "Auto-GIT E2E snapshot",
    executedAt: "2026-04-09",
    status: "NEEDS_FIXES",
    summary: "canonical e2e snapshot; quality_gate_reason=correctness_gate_failed",
  },
  {
    artifact: "output/benchmark_baseline/baseline_result.json",
    lane: "Karpathy baseline",
    executedAt: "2026-04-09",
    status: "MIXED",
    summary: "single-shot baseline; syntax/runtime true; fallback_used=true",
  },
  {
    artifact: "output/benchmark_comparison.json",
    lane: "Comparison snapshot",
    executedAt: "2026-04-09 11:14",
    status: "MIXED",
    summary: "combined benchmark snapshot; Auto-GIT needs_attention vs baseline runtime_ok=true",
  },
];
