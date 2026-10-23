import type { ReactNode } from 'react';
import { motion, type Variants } from 'motion/react';
import { useReducedMotion } from 'motion/react';

export type AnimatedGroupProps = {
  children: ReactNode;
  className?: string;
  preset?: 'fade' | 'slide' | 'blur-slide' | 'scale';
};

const presets: Record<NonNullable<AnimatedGroupProps['preset']>, Variants> = {
  fade: { hidden: { opacity: 0 }, visible: { opacity: 1 } },
  slide: { hidden: { opacity: 0, y: 14 }, visible: { opacity: 1, y: 0 } },
  'blur-slide': { hidden: { opacity: 0, y: 14, filter: 'blur(4px)' }, visible: { opacity: 1, y: 0, filter: 'blur(0px)' } },
  scale: { hidden: { opacity: 0, scale: 0.96 }, visible: { opacity: 1, scale: 1 } },
};

/** Adapted from Motion Primitives' AnimatedGroup pattern. */
export function AnimatedGroup({ children, className, preset = 'slide' }: AnimatedGroupProps) {
  const reducedMotion = useReducedMotion();
  const item = reducedMotion ? presets.fade : presets[preset];
  return (
    <motion.div
      className={className}
      initial="hidden"
      animate="visible"
      variants={{ visible: { transition: { staggerChildren: reducedMotion ? 0 : 0.06 } } }}
    >
      {Array.isArray(children) ? children.map((child, index) => <motion.div key={index} variants={item}>{child}</motion.div>) : <motion.div variants={item}>{children}</motion.div>}
    </motion.div>
  );
}
