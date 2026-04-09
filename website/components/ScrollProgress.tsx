'use client';

import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { usePresentationMode } from '@/components/PresentationModeProvider';

export default function ScrollProgress() {
  const { motionTier } = usePresentationMode();
  const [scrollProgress, setScrollProgress] = useState(0);

  useEffect(() => {
    let ticking = false;

    const updateProgress = () => {
      const totalHeight = document.documentElement.scrollHeight - window.innerHeight;
      const progress = totalHeight > 0 ? (window.scrollY / totalHeight) * 100 : 0;
      setScrollProgress(Math.min(progress, 100));
      ticking = false;
    };

    const handleScroll = () => {
      if (ticking) {
        return;
      }

      ticking = true;
      window.requestAnimationFrame(updateProgress);
    };

    updateProgress();
    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  if (motionTier === 'low') {
    return <div className="fixed left-0 right-0 top-0 z-[60] h-[2px] bg-[rgba(148,163,184,0.5)]" aria-hidden />;
  }

  return (
    <motion.div
      className="fixed top-0 left-0 right-0 h-1 z-[60] origin-left"
      initial={{ scaleX: 0 }}
      animate={{ scaleX: 1 }}
      transition={{ duration: 0.5 }}
    >
      <motion.div
        className="h-full w-full"
        style={{
          background: 'linear-gradient(90deg, #00D4FF 0%, #7C3AED 50%, #10B981 100%)',
          transform: `scaleX(${scrollProgress / 100})`,
          transformOrigin: 'left center',
          willChange: 'transform',
        }}
        transition={{ duration: 0.1 }}
      />
      {/* Glow effect */}
      <motion.div
        className="h-1 w-2 absolute top-0 shadow-lg"
        style={{
          left: `${scrollProgress}%`,
          background: 'linear-gradient(90deg, #00D4FF, #7C3AED)',
          boxShadow: '0 0 10px #00D4FF, 0 0 20px #7C3AED, 0 0 30px #00D4FF',
          transform: 'translateX(-50%)',
        }}
      />
    </motion.div>
  );
}
