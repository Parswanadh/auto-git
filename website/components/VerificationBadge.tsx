'use client';

import { motion } from 'framer-motion';
import { CheckCircle2 } from 'lucide-react';
import { EVIDENCE_AS_OF } from '@/data/evidenceMetrics';

export default function VerificationBadge() {
  return (
    <motion.div
      className="fixed bottom-4 right-4 z-40 hidden rounded-full border border-[rgba(16,185,129,0.4)] bg-[rgba(2,6,23,0.88)] px-3 py-2 text-[10px] text-[rgba(248,250,252,0.7)] shadow-[0_0_18px_rgba(16,185,129,0.2)] backdrop-blur-md md:flex md:items-center md:gap-2"
      initial={{ opacity: 0, y: 12, scale: 0.92 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ duration: 0.45, delay: 1.1 }}
      aria-label="Evidence verification stamp"
    >
      <motion.span
        animate={{ rotate: [0, 360] }}
        transition={{ duration: 7, repeat: Infinity, ease: 'linear' }}
      >
        <CheckCircle2 size={16} color="#10B981" />
      </motion.span>
      <span>Verified numbers · {EVIDENCE_AS_OF}</span>
    </motion.div>
  );
}
