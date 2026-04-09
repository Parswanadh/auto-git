'use client';

import { motion } from 'framer-motion';
import { useEffect, useMemo, useRef, useState } from 'react';

type PipelineNodeId =
  | 'requirements_extraction'
  | 'research'
  | 'generate_perspectives'
  | 'problem_extraction'
  | 'solution_generation'
  | 'critique'
  | 'consensus_check'
  | 'solution_selection'
  | 'architect_spec'
  | 'code_generation'
  | 'code_review_agent'
  | 'code_testing'
  | 'feature_verification'
  | 'strategy_reasoner'
  | 'code_fixing'
  | 'smoke_test'
  | 'pipeline_self_eval'
  | 'goal_achievement_eval'
  | 'git_publishing';

type PipelineNode = {
  id: PipelineNodeId;
  label: string;
  shortLabel: string;
  x: number;
  y: number;
  color: string;
};

type PipelineEdge = {
  id: string;
  source: PipelineNodeId;
  target: PipelineNodeId;
  kind: 'linear' | 'loop' | 'conditional';
};

const NODES: PipelineNode[] = [
  { id: 'requirements_extraction', label: 'Requirements', shortLabel: 'Req', x: 6, y: 8, color: '#00D4FF' },
  { id: 'research', label: 'Research', shortLabel: 'Research', x: 18, y: 8, color: '#00D4FF' },
  { id: 'generate_perspectives', label: 'Perspectives', shortLabel: 'Persp', x: 30, y: 8, color: '#7C3AED' },
  { id: 'problem_extraction', label: 'Problem Extraction', shortLabel: 'Problem', x: 42, y: 8, color: '#7C3AED' },
  { id: 'solution_generation', label: 'Solution Gen', shortLabel: 'Solution', x: 54, y: 8, color: '#7C3AED' },
  { id: 'critique', label: 'Critique', shortLabel: 'Critique', x: 66, y: 8, color: '#7C3AED' },
  { id: 'consensus_check', label: 'Consensus', shortLabel: 'Consensus', x: 78, y: 8, color: '#F59E0B' },
  { id: 'solution_selection', label: 'Selection', shortLabel: 'Select', x: 90, y: 8, color: '#10B981' },

  { id: 'architect_spec', label: 'Architect Spec', shortLabel: 'Spec', x: 82, y: 24, color: '#10B981' },
  { id: 'code_generation', label: 'Code Generation', shortLabel: 'Codegen', x: 70, y: 24, color: '#10B981' },
  { id: 'code_review_agent', label: 'Code Review', shortLabel: 'Review', x: 58, y: 24, color: '#F59E0B' },
  { id: 'code_testing', label: 'Code Testing', shortLabel: 'Test', x: 46, y: 24, color: '#F59E0B' },
  { id: 'feature_verification', label: 'Feature Verify', shortLabel: 'Verify', x: 34, y: 24, color: '#EF4444' },
  { id: 'strategy_reasoner', label: 'Strategy', shortLabel: 'Strategy', x: 22, y: 24, color: '#EF4444' },
  { id: 'code_fixing', label: 'Code Fixing', shortLabel: 'Fix', x: 10, y: 24, color: '#EF4444' },

  { id: 'smoke_test', label: 'Smoke Test', shortLabel: 'Smoke', x: 22, y: 40, color: '#10B981' },
  { id: 'pipeline_self_eval', label: 'Self Eval', shortLabel: 'Self', x: 42, y: 40, color: '#00D4FF' },
  { id: 'goal_achievement_eval', label: 'Goal Eval', shortLabel: 'Goal', x: 62, y: 40, color: '#00D4FF' },
  { id: 'git_publishing', label: 'Publish', shortLabel: 'Publish', x: 82, y: 40, color: '#00D4FF' },
];

const EDGES: PipelineEdge[] = [
  { id: 'requirements_extraction-research', source: 'requirements_extraction', target: 'research', kind: 'linear' },
  { id: 'research-generate_perspectives', source: 'research', target: 'generate_perspectives', kind: 'linear' },
  { id: 'generate_perspectives-problem_extraction', source: 'generate_perspectives', target: 'problem_extraction', kind: 'linear' },
  { id: 'problem_extraction-solution_generation', source: 'problem_extraction', target: 'solution_generation', kind: 'linear' },
  { id: 'solution_generation-critique', source: 'solution_generation', target: 'critique', kind: 'linear' },
  { id: 'critique-consensus_check', source: 'critique', target: 'consensus_check', kind: 'linear' },
  { id: 'consensus_check-solution_selection', source: 'consensus_check', target: 'solution_selection', kind: 'linear' },
  { id: 'consensus_check-solution_generation', source: 'consensus_check', target: 'solution_generation', kind: 'loop' },

  { id: 'solution_selection-architect_spec', source: 'solution_selection', target: 'architect_spec', kind: 'linear' },
  { id: 'architect_spec-code_generation', source: 'architect_spec', target: 'code_generation', kind: 'linear' },
  { id: 'code_generation-code_review_agent', source: 'code_generation', target: 'code_review_agent', kind: 'linear' },
  { id: 'code_review_agent-code_testing', source: 'code_review_agent', target: 'code_testing', kind: 'linear' },
  { id: 'code_testing-feature_verification', source: 'code_testing', target: 'feature_verification', kind: 'linear' },
  { id: 'feature_verification-strategy_reasoner', source: 'feature_verification', target: 'strategy_reasoner', kind: 'conditional' },
  { id: 'strategy_reasoner-code_fixing', source: 'strategy_reasoner', target: 'code_fixing', kind: 'linear' },
  { id: 'code_fixing-code_testing', source: 'code_fixing', target: 'code_testing', kind: 'loop' },

  { id: 'code_fixing-smoke_test', source: 'code_fixing', target: 'smoke_test', kind: 'linear' },
  { id: 'smoke_test-pipeline_self_eval', source: 'smoke_test', target: 'pipeline_self_eval', kind: 'linear' },
  { id: 'pipeline_self_eval-goal_achievement_eval', source: 'pipeline_self_eval', target: 'goal_achievement_eval', kind: 'linear' },
  { id: 'goal_achievement_eval-git_publishing', source: 'goal_achievement_eval', target: 'git_publishing', kind: 'linear' },
];

const EDGE_COLOR: Record<PipelineEdge['kind'], string> = {
  linear: 'rgba(34, 211, 238, 0.55)',
  loop: 'rgba(245, 158, 11, 0.72)',
  conditional: 'rgba(244, 63, 94, 0.72)',
};

function removeFromSet(current: Set<string>, value: string) {
  const next = new Set(current);
  next.delete(value);
  return next;
}

export default function AnimatedPipelineGraph({ className }: { className?: string }) {
  const [isRunning, setIsRunning] = useState(true);
  const [activeEdges, setActiveEdges] = useState<Set<string>>(new Set());
  const [activeNodes, setActiveNodes] = useState<Set<PipelineNodeId>>(new Set());
  const [sparkKey, setSparkKey] = useState(0);
  const timeoutIdsRef = useRef<number[]>([]);

  const nodeMap = useMemo(() => {
    return new Map(NODES.map((node) => [node.id, node]));
  }, []);

  useEffect(() => {
    if (!isRunning) {
      return;
    }

    const activateEdge = () => {
      const edge = EDGES[Math.floor(Math.random() * EDGES.length)];

      setActiveEdges((prev) => {
        const next = new Set(prev);
        next.add(edge.id);
        return next;
      });

      setActiveNodes((prev) => {
        const next = new Set(prev);
        next.add(edge.source);
        next.add(edge.target);
        return next;
      });

      setSparkKey((value) => value + 1);

      const edgeTimeout = window.setTimeout(() => {
        setActiveEdges((prev) => removeFromSet(prev, edge.id));
      }, 850);

      const nodeTimeout = window.setTimeout(() => {
        setActiveNodes((prev) => {
          const next = new Set(prev);
          next.delete(edge.source);
          next.delete(edge.target);
          return next;
        });
      }, 1050);

      timeoutIdsRef.current.push(edgeTimeout, nodeTimeout);
    };

    activateEdge();

    const intervalId = window.setInterval(() => {
      const burst = Math.random() < 0.3 ? 2 : 1;
      for (let i = 0; i < burst; i += 1) {
        const delay = i * 130;
        const burstTimeout = window.setTimeout(activateEdge, delay);
        timeoutIdsRef.current.push(burstTimeout);
      }
    }, 460);

    return () => {
      window.clearInterval(intervalId);
      timeoutIdsRef.current.forEach((id) => window.clearTimeout(id));
      timeoutIdsRef.current = [];
    };
  }, [isRunning]);

  return (
    <div
      className={`relative overflow-hidden rounded-2xl border border-[rgba(0,212,255,0.24)] bg-[rgba(2,6,23,0.75)] p-4 md:p-6 ${className ?? ''}`}
      aria-label="Animated Auto-GIT 19 node pipeline graph"
    >
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_25%_20%,rgba(0,212,255,0.16),transparent_40%),radial-gradient(circle_at_75%_80%,rgba(124,58,237,0.18),transparent_45%)]" />

      <div className="relative z-20 mb-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-xs uppercase tracking-[0.2em] text-[rgba(248,250,252,0.55)]">Live Pipeline Flow</p>
          <p className="font-orbitron text-sm text-[rgba(248,250,252,0.85)]">19 nodes with random edge activations</p>
        </div>
        <button
          type="button"
          onClick={() => setIsRunning((prev) => !prev)}
          className="rounded-lg border border-[rgba(0,212,255,0.35)] bg-[rgba(0,212,255,0.12)] px-4 py-2 text-xs font-semibold uppercase tracking-widest text-[#00D4FF] transition-colors hover:bg-[rgba(0,212,255,0.2)]"
        >
          {isRunning ? 'Pause flow' : 'Resume flow'}
        </button>
      </div>

      <svg viewBox="0 0 96 48" className="relative z-10 h-[360px] w-full md:h-[460px]" role="img">
        <defs>
          <filter id="nodeGlow" x="-100%" y="-100%" width="300%" height="300%">
            <feGaussianBlur stdDeviation="1.2" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        {EDGES.map((edge) => {
          const source = nodeMap.get(edge.source);
          const target = nodeMap.get(edge.target);

          if (!source || !target) {
            return null;
          }

          const isActive = activeEdges.has(edge.id);
          const edgeStroke = EDGE_COLOR[edge.kind];

          return (
            <g key={edge.id}>
              <motion.line
                x1={source.x}
                y1={source.y}
                x2={target.x}
                y2={target.y}
                stroke={edgeStroke}
                strokeWidth={isActive ? 1.35 : 0.65}
                strokeLinecap="round"
                strokeDasharray={isActive ? '2.4 1.6' : '1.5 1.5'}
                animate={{
                  strokeOpacity: isActive ? 1 : 0.28,
                  strokeDashoffset: isActive ? [8, 0] : 0,
                }}
                transition={{
                  duration: isActive ? 0.8 : 0.25,
                  ease: 'linear',
                }}
              />

              {isActive && (
                <motion.circle
                  key={`${edge.id}-${sparkKey}`}
                  r={0.58}
                  fill="#F8FAFC"
                  filter="url(#nodeGlow)"
                  initial={{ cx: source.x, cy: source.y, opacity: 0 }}
                  animate={{
                    cx: [source.x, target.x],
                    cy: [source.y, target.y],
                    opacity: [0, 1, 1, 0],
                  }}
                  transition={{ duration: 0.82, ease: 'linear' }}
                />
              )}
            </g>
          );
        })}

        {NODES.map((node, index) => {
          const isActive = activeNodes.has(node.id);

          return (
            <g key={node.id}>
              <motion.circle
                cx={node.x}
                cy={node.y}
                r={isActive ? 2.25 : 1.82}
                fill={node.color}
                stroke="rgba(248,250,252,0.66)"
                strokeWidth={isActive ? 0.42 : 0.24}
                filter="url(#nodeGlow)"
                animate={{
                  opacity: isActive ? [0.95, 1, 0.85] : 0.74,
                }}
                transition={{ duration: 0.34 }}
              />

              <text
                x={node.x}
                y={node.y + 0.45}
                textAnchor="middle"
                fontSize="0.88"
                fill="rgba(2,6,23,0.86)"
                fontWeight="700"
              >
                {index + 1}
              </text>

              <text
                x={node.x}
                y={node.y + 3.95}
                textAnchor="middle"
                fontSize="1.16"
                fill="rgba(248,250,252,0.86)"
                className="hidden md:block"
              >
                {node.label}
              </text>

              <text
                x={node.x}
                y={node.y + 3.95}
                textAnchor="middle"
                fontSize="1.06"
                fill="rgba(248,250,252,0.86)"
                className="md:hidden"
              >
                {node.shortLabel}
              </text>
            </g>
          );
        })}
      </svg>

      <div className="relative z-20 mt-3 grid gap-2 text-xs text-[rgba(248,250,252,0.64)] md:grid-cols-3">
        <div className="rounded-lg border border-[rgba(34,211,238,0.25)] bg-[rgba(15,23,42,0.5)] px-3 py-2">
          <span className="font-semibold text-[#22D3EE]">Linear edges:</span> main stage progression
        </div>
        <div className="rounded-lg border border-[rgba(245,158,11,0.25)] bg-[rgba(15,23,42,0.5)] px-3 py-2">
          <span className="font-semibold text-[#F59E0B]">Loop edges:</span> consensus and code-fix retries
        </div>
        <div className="rounded-lg border border-[rgba(244,63,94,0.25)] bg-[rgba(15,23,42,0.5)] px-3 py-2">
          <span className="font-semibold text-[#F43F5E]">Conditional edges:</span> route based on verification failures
        </div>
      </div>
    </div>
  );
}
