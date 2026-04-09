'use client';

import { motion } from 'framer-motion';
import { useEffect, useMemo, useRef, useState } from 'react';
import { usePresentationMode } from '@/components/PresentationModeProvider';

type AmbientNode = {
  id: string;
  x: number;
  y: number;
};

type AmbientEdge = {
  id: string;
  source: string;
  target: string;
};

const AMBIENT_NODES: AmbientNode[] = [
  { id: 'n1', x: 6, y: 14 },
  { id: 'n2', x: 14, y: 8 },
  { id: 'n3', x: 23, y: 16 },
  { id: 'n4', x: 31, y: 10 },
  { id: 'n5', x: 40, y: 18 },
  { id: 'n6', x: 49, y: 12 },
  { id: 'n7', x: 58, y: 20 },
  { id: 'n8', x: 67, y: 14 },
  { id: 'n9', x: 76, y: 22 },
  { id: 'n10', x: 85, y: 16 },
  { id: 'n11', x: 18, y: 32 },
  { id: 'n12', x: 36, y: 36 },
  { id: 'n13', x: 54, y: 34 },
  { id: 'n14', x: 72, y: 38 },
  { id: 'n15', x: 90, y: 32 },
];

const AMBIENT_EDGES: AmbientEdge[] = [
  { id: 'n1-n2', source: 'n1', target: 'n2' },
  { id: 'n2-n3', source: 'n2', target: 'n3' },
  { id: 'n3-n4', source: 'n3', target: 'n4' },
  { id: 'n4-n5', source: 'n4', target: 'n5' },
  { id: 'n5-n6', source: 'n5', target: 'n6' },
  { id: 'n6-n7', source: 'n6', target: 'n7' },
  { id: 'n7-n8', source: 'n7', target: 'n8' },
  { id: 'n8-n9', source: 'n8', target: 'n9' },
  { id: 'n9-n10', source: 'n9', target: 'n10' },
  { id: 'n2-n11', source: 'n2', target: 'n11' },
  { id: 'n4-n12', source: 'n4', target: 'n12' },
  { id: 'n6-n13', source: 'n6', target: 'n13' },
  { id: 'n8-n14', source: 'n8', target: 'n14' },
  { id: 'n10-n15', source: 'n10', target: 'n15' },
  { id: 'n11-n12', source: 'n11', target: 'n12' },
  { id: 'n12-n13', source: 'n12', target: 'n13' },
  { id: 'n13-n14', source: 'n13', target: 'n14' },
  { id: 'n14-n15', source: 'n14', target: 'n15' },
];

export default function PipelineAmbientBackground() {
  const { effectiveMode, motionTier } = usePresentationMode();
  const [activeEdges, setActiveEdges] = useState<Set<string>>(new Set());
  const [isPageVisible, setIsPageVisible] = useState(true);
  const timeoutIdsRef = useRef<number[]>([]);
  const animationEnabled = motionTier !== 'low';
  const intervalMs = effectiveMode === 'frontier' ? 700 : 1200;
  const edgeLifetimeMs = effectiveMode === 'frontier' ? 1100 : 800;
  const burstChance = effectiveMode === 'frontier' ? 0.22 : 0.1;

  const nodeMap = useMemo(() => {
    return new Map(AMBIENT_NODES.map((node) => [node.id, node]));
  }, []);

  useEffect(() => {
    const onVisibilityChange = () => setIsPageVisible(document.visibilityState === 'visible');

    onVisibilityChange();
    document.addEventListener('visibilitychange', onVisibilityChange);

    return () => document.removeEventListener('visibilitychange', onVisibilityChange);
  }, []);

  useEffect(() => {
    if (!animationEnabled || !isPageVisible) {
      setActiveEdges(new Set());
      return;
    }

    const activate = () => {
      const edge = AMBIENT_EDGES[Math.floor(Math.random() * AMBIENT_EDGES.length)];

      setActiveEdges((prev) => {
        const next = new Set(prev);
        next.add(edge.id);
        return next;
      });

      const timeoutId = window.setTimeout(() => {
        setActiveEdges((prev) => {
          const next = new Set(prev);
          next.delete(edge.id);
          return next;
        });
      }, edgeLifetimeMs);

      timeoutIdsRef.current.push(timeoutId);
    };

    const intervalId = window.setInterval(() => {
      const burst = Math.random() < burstChance ? 2 : 1;
      for (let i = 0; i < burst; i += 1) {
        const t = window.setTimeout(activate, i * 200);
        timeoutIdsRef.current.push(t);
      }
    }, intervalMs);

    return () => {
      window.clearInterval(intervalId);
      timeoutIdsRef.current.forEach((id) => window.clearTimeout(id));
      timeoutIdsRef.current = [];
    };
  }, [animationEnabled, isPageVisible, intervalMs, edgeLifetimeMs, burstChance]);

  if (!animationEnabled) {
    return (
      <div className="pointer-events-none fixed inset-0 z-0 opacity-20" aria-hidden>
        <svg viewBox="0 0 96 42" className="h-full w-full">
          {AMBIENT_EDGES.map((edge) => {
            const source = nodeMap.get(edge.source);
            const target = nodeMap.get(edge.target);

            if (!source || !target) {
              return null;
            }

            return (
              <line
                key={edge.id}
                x1={source.x}
                y1={source.y}
                x2={target.x}
                y2={target.y}
                stroke="rgba(71,85,105,0.35)"
                strokeWidth={0.22}
                strokeLinecap="round"
              />
            );
          })}

          {AMBIENT_NODES.map((node) => (
            <circle
              key={node.id}
              cx={node.x}
              cy={node.y}
              r={0.34}
              fill="rgba(148,163,184,0.35)"
            />
          ))}
        </svg>
      </div>
    );
  }

  return (
    <div className="pointer-events-none fixed inset-0 z-0 opacity-35" aria-hidden>
      <svg viewBox="0 0 96 42" className="h-full w-full">
        {AMBIENT_EDGES.map((edge) => {
          const source = nodeMap.get(edge.source);
          const target = nodeMap.get(edge.target);

          if (!source || !target) {
            return null;
          }

          const isActive = activeEdges.has(edge.id);

          return (
            <motion.line
              key={edge.id}
              x1={source.x}
              y1={source.y}
              x2={target.x}
              y2={target.y}
              stroke={isActive ? 'rgba(34,211,238,0.7)' : 'rgba(71,85,105,0.28)'}
              strokeWidth={isActive ? 0.44 : 0.25}
              strokeLinecap="round"
              animate={{
                strokeOpacity: isActive ? [0.22, 0.9, 0.35] : 0.3,
              }}
              transition={{ duration: 0.7 }}
            />
          );
        })}

        {AMBIENT_NODES.map((node) => {
          const linkedActive = Array.from(activeEdges).some((edgeId) => edgeId.includes(node.id));

          return (
            <motion.circle
              key={node.id}
              cx={node.x}
              cy={node.y}
              r={linkedActive ? 0.58 : 0.38}
              fill={linkedActive ? 'rgba(103,232,249,0.8)' : 'rgba(148,163,184,0.4)'}
              animate={{ opacity: linkedActive ? [0.45, 1, 0.6] : [0.22, 0.45, 0.22] }}
              transition={{ duration: linkedActive ? 0.6 : 2.6, repeat: Infinity }}
            />
          );
        })}
      </svg>
    </div>
  );
}
