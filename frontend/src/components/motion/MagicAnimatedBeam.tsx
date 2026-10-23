import { useEffect, useId, useState, type RefObject } from 'react';
import { motion, useReducedMotion } from 'motion/react';

type MagicAnimatedBeamProps = {
  className?: string;
  containerRef: RefObject<HTMLElement | null>;
  fromRef: RefObject<HTMLElement | null>;
  toRef: RefObject<HTMLElement | null>;
  curvature?: number;
  reverse?: boolean;
  pathColor?: string;
  pathWidth?: number;
  pathOpacity?: number;
  gradientStartColor?: string;
  gradientStopColor?: string;
  delay?: number;
  duration?: number;
  repeat?: number;
  repeatDelay?: number;
};

/**
 * Magic UI AnimatedBeam pattern, adapted from the official source so the
 * network map can use refs without adopting the library's Tailwind helpers.
 * Source: https://github.com/magicuidesign/magicui/blob/main/apps/www/registry/magicui/animated-beam.tsx
 */
export function MagicAnimatedBeam({
  className,
  containerRef,
  fromRef,
  toRef,
  curvature = 0,
  reverse = false,
  pathColor = '#29483e',
  pathWidth = 1.25,
  pathOpacity = 0.25,
  gradientStartColor = '#8cf2c8',
  gradientStopColor = '#f2b35d',
  delay = 0,
  duration = 1.2,
  repeat = 1,
  repeatDelay = 0,
}: MagicAnimatedBeamProps) {
  const id = useId();
  const reducedMotion = useReducedMotion();
  const [pathD, setPathD] = useState('');
  const [svgDimensions, setSvgDimensions] = useState({ width: 0, height: 0 });

  useEffect(() => {
    const updatePath = () => {
      if (!containerRef.current || !fromRef.current || !toRef.current) return;
      const containerRect = containerRef.current.getBoundingClientRect();
      const fromRect = fromRef.current.getBoundingClientRect();
      const toRect = toRef.current.getBoundingClientRect();
      const startX = fromRect.left - containerRect.left + fromRect.width / 2;
      const startY = fromRect.top - containerRect.top + fromRect.height / 2;
      const endX = toRect.left - containerRect.left + toRect.width / 2;
      const endY = toRect.top - containerRect.top + toRect.height / 2;
      const controlY = startY - curvature;
      setSvgDimensions({ width: containerRect.width, height: containerRect.height });
      setPathD(`M ${startX},${startY} Q ${(startX + endX) / 2},${controlY} ${endX},${endY}`);
    };

    const resizeObserver = new ResizeObserver(updatePath);
    if (containerRef.current) resizeObserver.observe(containerRef.current);
    if (fromRef.current) resizeObserver.observe(fromRef.current);
    if (toRef.current) resizeObserver.observe(toRef.current);
    updatePath();
    return () => resizeObserver.disconnect();
  }, [containerRef, fromRef, toRef, curvature]);

  const gradientCoordinates = reverse
    ? { x1: ['90%', '-10%'], x2: ['100%', '0%'] }
    : { x1: ['10%', '110%'], x2: ['0%', '100%'] };

  if (!pathD || svgDimensions.width === 0) return null;

  return (
    <svg
      aria-hidden="true"
      className={`world-magic-beam ${className ?? ''}`}
      fill="none"
      width={svgDimensions.width}
      height={svgDimensions.height}
      viewBox={`0 0 ${svgDimensions.width} ${svgDimensions.height}`}
    >
      <path d={pathD} stroke={pathColor} strokeWidth={pathWidth} strokeOpacity={pathOpacity} strokeLinecap="round" />
      <path d={pathD} stroke={`url(#${id})`} strokeWidth={pathWidth} strokeOpacity="1" strokeLinecap="round" />
      <defs>
        <motion.linearGradient
          id={id}
          gradientUnits="userSpaceOnUse"
          initial={{ x1: '0%', x2: '0%', y1: '0%', y2: '0%' }}
          animate={reducedMotion ? { x1: '50%', x2: '50%', y1: '0%', y2: '0%' } : { x1: gradientCoordinates.x1, x2: gradientCoordinates.x2, y1: '0%', y2: '0%' }}
          transition={{ delay, duration: reducedMotion ? 0 : duration, ease: [0.16, 1, 0.3, 1], repeat: reducedMotion ? 0 : repeat, repeatDelay }}
        >
          <stop stopColor={gradientStartColor} stopOpacity="0" />
          <stop stopColor={gradientStartColor} />
          <stop offset="32.5%" stopColor={gradientStopColor} />
          <stop offset="100%" stopColor={gradientStopColor} stopOpacity="0" />
        </motion.linearGradient>
      </defs>
    </svg>
  );
}
