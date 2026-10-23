import { motion, useReducedMotion, type MotionStyle } from 'motion/react';

type ReactBitsBlurTextProps = {
  text: string;
  className?: string;
  animateBy?: 'words' | 'letters';
  direction?: 'top' | 'bottom' | 'left' | 'right';
  delay?: number;
  distance?: number;
  blur?: number;
  duration?: number;
};

/**
 * React Bits BlurText pattern, adapted from the official TS source for the
 * existing Motion runtime and Terminal Mint tokens.
 * Source: https://github.com/DavidHDev/react-bits/tree/main/src/ts-default/TextAnimations/BlurText
 */
export function ReactBitsBlurText({
  text,
  className,
  animateBy = 'words',
  direction = 'bottom',
  delay = 0,
  distance = 18,
  blur = 4,
  duration = 0.62,
}: ReactBitsBlurTextProps) {
  const reducedMotion = useReducedMotion();
  const pieces = animateBy === 'letters' ? Array.from(text) : text.split(/(\s+)/);
  const axis = direction === 'left' || direction === 'right' ? 'x' : 'y';
  const sign = direction === 'top' || direction === 'left' ? -1 : 1;
  const initial = reducedMotion
    ? { opacity: 1 }
    : { opacity: 0, filter: `blur(${blur}px)`, [axis]: sign * distance };
  const style: MotionStyle = { display: 'inline-block', whiteSpace: 'pre' };

  return (
    <span className={className} aria-label={text}>
      {pieces.map((piece, index) => (
        <motion.span
          key={`${piece}-${index}`}
          aria-hidden="true"
          style={style}
          initial={initial}
          animate={reducedMotion ? { opacity: 1 } : { opacity: 1, filter: 'blur(0px)', x: 0, y: 0 }}
          transition={{
            duration: reducedMotion ? 0 : duration,
            delay: reducedMotion ? 0 : delay + index * 0.045,
            ease: [0.33, 1, 0.68, 1],
          }}
        >
          {piece}
        </motion.span>
      ))}
    </span>
  );
}
