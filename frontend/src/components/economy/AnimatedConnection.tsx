/**
 * Agentropolis — Animated Connection
 *
 * Flowing light paths between business nodes. Supports:
 * - Path-drawing animation on formation
 * - Animated message packets traveling along the connection
 * - Color-coded relationship statuses
 * - Animated thickness based on economic activity
 * - Dissolving animation when contracts expire
 *
 * SVG-based, ref-driven so endpoints can be any DOM element.
 */

import { useEffect, useRef, useState, useId, type RefObject } from 'react';
import { motion, useReducedMotion } from 'motion/react';

type ConnectionStatus = 'negotiating' | 'active' | 'disrupted' | 'defaulted' | 'forming' | 'dissolving';

interface AnimatedConnectionProps {
  containerRef: RefObject<HTMLElement | null>;
  fromRef: RefObject<HTMLElement | null>;
  toRef: RefObject<HTMLElement | null>;
  status?: ConnectionStatus;
  activity?: number; // 0-1, affects thickness and packet frequency
  curvature?: number;
  packetInterval?: number; // ms between packets, 0 = disabled
  className?: string;
}

const statusColors: Record<ConnectionStatus, string> = {
  negotiating: '#ffbe76',
  active: '#8cf2c8',
  disrupted: '#ff4757',
  defaulted: '#ff4757',
  forming: '#c49bea',
  dissolving: '#666666',
};

const statusWidths: Record<ConnectionStatus, number> = {
  negotiating: 1.5,
  active: 2,
  disrupted: 1,
  defaulted: 1,
  forming: 1,
  dissolving: 0.5,
};

interface Packet {
  id: string;
  progress: number;
  color: string;
}

export function AnimatedConnection({
  containerRef,
  fromRef,
  toRef,
  status = 'active',
  activity = 0.5,
  curvature = 60,
  packetInterval = 800,
  className = '',
}: AnimatedConnectionProps) {
  const svgRef = useRef<SVGSVGElement | null>(null);
  const pathRef = useRef<SVGPathElement | null>(null);
  const reducedMotion = useReducedMotion();
  const [pathD, setPathD] = useState('');
  const gradientId = useId();
  const [packets, setPackets] = useState<Packet[]>([]);
  const packetTimerRef = useRef<number | null>(null);
  const lastPacketTime = useRef(0);
  const packetAnimateRef = useRef<number | null>(null);

  useEffect(() => {
    const container = containerRef.current;
    const from = fromRef.current;
    const to = toRef.current;
    if (!container || !from || !to) return;

    const updatePath = () => {
      const containerRect = container.getBoundingClientRect();
      const fromRect = from.getBoundingClientRect();
      const toRect = to.getBoundingClientRect();

      const startX = fromRect.left - containerRect.left + fromRect.width / 2;
      const startY = fromRect.top - containerRect.top + fromRect.height / 2;
      const endX = toRect.left - containerRect.left + toRect.width / 2;
      const endY = toRect.top - containerRect.top + toRect.height / 2;

      const dx = endX - startX;
      const dy = endY - startY;
      const dist = Math.sqrt(dx * dx + dy * dy);

      const midX = (startX + endX) / 2;
      const midY = (startY + endY) / 2;
      const perpX = -dy / Math.max(dist, 1);
      const perpY = dx / Math.max(dist, 1);
      const cpX = midX + perpX * curvature;
      const cpY = midY + perpY * curvature;

      setPathD(`M ${startX},${startY} Q ${cpX},${cpY} ${endX},${endY}`);
    };

    const resizeObserver = new ResizeObserver(updatePath);
    resizeObserver.observe(container);
    resizeObserver.observe(from);
    resizeObserver.observe(to);
    updatePath();

    return () => resizeObserver.disconnect();
  }, [containerRef, fromRef, toRef, curvature]);

  // Animate path drawing
  useEffect(() => {
    if (!pathRef.current) return;
    const totalLength = pathRef.current.getTotalLength ? pathRef.current.getTotalLength() : 0;

    pathRef.current.style.strokeDasharray = `${totalLength} ${totalLength}`;
    pathRef.current.style.strokeDashoffset = String(totalLength);

    if (status === 'forming' || status === 'active') {
      requestAnimationFrame(() => {
        if (pathRef.current) {
          pathRef.current.style.transition = reducedMotion ? 'none' : 'stroke-dashoffset 0.8s ease-out';
          pathRef.current.style.strokeDashoffset = '0';
        }
      });
    } else if (status === 'dissolving') {
      requestAnimationFrame(() => {
        if (pathRef.current) {
          pathRef.current.style.transition = reducedMotion ? 'none' : 'stroke-dashoffset 0.6s ease-out';
          pathRef.current.style.strokeDashoffset = String(totalLength);
        }
      });
    }
  }, [status, reducedMotion, pathD]);

  // Spawn packets
  useEffect(() => {
    if (reducedMotion || packetInterval <= 0 || status === 'dissolving' || status === 'defaulted') {
      if (packetTimerRef.current) {
        clearInterval(packetTimerRef.current);
        packetTimerRef.current = null;
      }
      return;
    }

    const color = statusColors[status];
    const baseInterval = packetInterval / (0.5 + activity);

    packetTimerRef.current = window.setInterval(() => {
      const now = Date.now();
      if (now - lastPacketTime.current < 150) return;
      lastPacketTime.current = now;

      setPackets((prev) => [...prev.filter((p) => p.progress < 1), { id: Math.random().toString(36).slice(2), progress: 0, color }]);
    }, baseInterval);

    return () => {
      if (packetTimerRef.current) clearInterval(packetTimerRef.current);
    };
  }, [status, activity, packetInterval, reducedMotion]);

  // Animate packets along path using SVG getPointAtLength
  useEffect(() => {
    if (reducedMotion || packets.length === 0 || !pathRef.current) return;

    packetAnimateRef.current = window.setInterval(() => {
      setPackets((prev) => {
        const next = prev.map((p) => ({ ...p, progress: Math.min(p.progress + 0.06, 1) }));
        return next.filter((p) => p.progress < 1);
      });
    }, 16);

    return () => {
      if (packetAnimateRef.current) window.clearInterval(packetAnimateRef.current);
    };
  }, [packets, reducedMotion]);

  if (!pathD) return null;

  const color = statusColors[status];
  const width = statusWidths[status] * (0.6 + activity * 0.6);
  const opacity = status === 'dissolving' ? 0.3 : status === 'defaulted' ? 0.4 : 0.6;
  const dashArray = status === 'negotiating' ? '6 6' : status === 'disrupted' ? '3 5' : '0 0';


  return (
    <svg
      ref={svgRef}
      className={`absolute inset-0 -z-1 pointer-events-none ${className}`}
      style={{
        width: '100%',
        height: '100%',
        overflow: 'visible',
        pointerEvents: 'none',
      }}
      aria-hidden="true"
    >
      <defs>
        <linearGradient id={gradientId} x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%" stopColor={color} stopOpacity="0" />
          <stop offset="30%" stopColor={color} stopOpacity={opacity} />
          <stop offset="70%" stopColor={color} stopOpacity={opacity} />
          <stop offset="100%" stopColor={color} stopOpacity="0" />
        </linearGradient>
      </defs>

      {/* Main connection path */}
      <path
        ref={pathRef}
        d={pathD}
        fill="none"
        stroke={`url(#${gradientId})`}
        strokeWidth={width}
        strokeOpacity={1}
        strokeDasharray={dashArray}
        style={{
          transition: reducedMotion ? 'none' : 'all 0.4s ease',
          filter: status === 'active' || status === 'negotiating' ? `drop-shadow(0 0 4px ${color})` : 'none',
        }}
      />

      {/* Packet markers animated along the path */}
      {packets.map((packet) => {
        const pathEl = pathRef.current;
        if (!pathEl || !pathEl.getPointAtLength) return null;
        const length = pathEl.getTotalLength();
        const point = pathEl.getPointAtLength(length * packet.progress);

        return (
          <motion.circle
            key={packet.id}
            cx={point.x}
            cy={point.y}
            r={2.5}
            fill={packet.color}
            animate={{
              r: [1.5, 4, 1.5],
              opacity: [0, 1, 0],
              transition: { duration: 0.5, repeat: Infinity, ease: 'easeInOut' },
            }}
          />
        );
      })}
    </svg>
  );
}