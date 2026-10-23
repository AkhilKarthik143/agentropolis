import { AnimatePresence, motion, type Transition, type Variant } from 'motion/react';

type TransitionPanelProps = {
  children: React.ReactNode[];
  activeIndex: number;
  className?: string;
  transition?: Transition;
  variants?: { enter: Variant; center: Variant; exit: Variant };
};

/** Motion Primitives' TransitionPanel pattern, kept local so the app owns its styling. */
export function TransitionPanel({ children, activeIndex, className, transition = { duration: 0.26, ease: 'easeOut' }, variants, }: TransitionPanelProps) {
  return (
    <div className={className}>
      <AnimatePresence initial={false} mode="popLayout">
        <motion.div
          key={activeIndex}
          variants={variants}
          transition={transition}
          initial="enter"
          animate="center"
          exit="exit"
        >
          {children[activeIndex]}
        </motion.div>
      </AnimatePresence>
    </div>
  );
}
