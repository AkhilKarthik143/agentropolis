import { useEffect } from 'react';
import { motion, useReducedMotion, useSpring, useTransform, type SpringOptions } from 'motion/react';

type AnimatedNumberProps = {
  value: number;
  className?: string;
  prefix?: string;
  decimals?: number;
  springOptions?: SpringOptions;
};

/** Motion Primitives-style number interpolation for confirmed financial state. */
export function AnimatedNumber({ value, className, prefix = '', decimals = 0, springOptions }: AnimatedNumberProps) {
  const reducedMotion = useReducedMotion();
  const spring = useSpring(value, springOptions ?? { stiffness: 260, damping: 28, mass: 0.8 });
  const formatter = new Intl.NumberFormat('en-US', { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
  const display = useTransform(spring, (current) => `${prefix}${formatter.format(current)}`);

  useEffect(() => {
    spring.set(value);
  }, [spring, value]);

  return reducedMotion ? <span className={className}>{prefix}{formatter.format(value)}</span> : <motion.span className={className}>{display}</motion.span>;
}
