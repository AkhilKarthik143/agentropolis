/**
 * Agentropolis — Economic Constellation
 *
 * Slow-moving particle constellation in the background. Nodes represent
 * businesses; faint lines represent potential relationships. Particles drift
 * gently and occasionally brighten when real economic events fire.
 *
 * Canvas 2D — low cost, high atmosphere.
 */

import { useEffect, useRef, useState } from 'react';
import { useReducedMotion } from 'motion/react';

interface ConstellationNode {
  x: number;
  y: number;
  vx: number;
  vy: number;
  radius: number;
  opacity: number;
  targetOpacity: number;
  pulseOffset: number;
}

interface ConstellationLink {
  a: number;
  b: number;
  strength: number;
}

export function EconomicConstellation({
  className = '',
  particleCount = 40,
  connectionDistance = 180,
}: {
  className?: string;
  particleCount?: number;
  connectionDistance?: number;
}) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animationRef = useRef<number | null>(null);
  const reducedMotion = useReducedMotion();
  const [width, setWidth] = useState(0);
  const [height, setHeight] = useState(0);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const context = canvas.getContext('2d');
    if (!context) return;
    const ctx: CanvasRenderingContext2D = context;

    const resize = () => {
      const rect = canvas.parentElement?.getBoundingClientRect() ?? { width: window.innerWidth, height: window.innerHeight };
      const dpr = window.devicePixelRatio ?? 1;
      canvas.width = rect.width * dpr;
      canvas.height = rect.height * dpr;
      canvas.style.width = `${rect.width}px`;
      canvas.style.height = `${rect.height}px`;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      setWidth(rect.width);
      setHeight(rect.height);
    };
    resize();
    window.addEventListener('resize', resize);

    // Create nodes
    const nodes: ConstellationNode[] = [];
    for (let i = 0; i < particleCount; i++) {
      nodes.push({
        x: Math.random() * width,
        y: Math.random() * height,
        vx: (Math.random() - 0.5) * 0.3,
        vy: (Math.random() - 0.5) * 0.3,
        radius: 1 + Math.random() * 2,
        opacity: 0,
        targetOpacity: 0.3 + Math.random() * 0.4,
        pulseOffset: Math.random() * Math.PI * 2,
      });
    }

    // Precompute static links (Delaunay-like: connect nearest neighbors)
    const links: ConstellationLink[] = [];
    for (let i = 0; i < nodes.length; i++) {
      const distances: { index: number; dist: number }[] = [];
      for (let j = 0; j < nodes.length; j++) {
        if (i === j) continue;
        const dx = nodes[i].x - nodes[j].x;
        const dy = nodes[i].y - nodes[j].y;
        const dist = Math.sqrt(dx * dx + dy * dy);
        distances.push({ index: j, dist });
      }
      distances.sort((a, b) => a.dist - b.dist);
      for (let k = 0; k < Math.min(3, distances.length); k++) {
        links.push({ a: i, b: distances[k].index, strength: 1 - distances[k].dist / connectionDistance });
      }
    }

    let eventGlow = 0; // decays after an economic event

    function animate() {
      if (reducedMotion) {
        // Still draw static nodes, but no motion
        ctx.clearRect(0, 0, width, height);
        drawStatic(ctx, nodes, links);
        animationRef.current = requestAnimationFrame(animate);
        return;
      }

      ctx.clearRect(0, 0, width, height);

      // Decay event glow
      if (eventGlow > 0) eventGlow -= 0.005;
      if (eventGlow < 0) eventGlow = 0;

      // Update nodes
      nodes.forEach((node) => {
        node.x += node.vx;
        node.y += node.vy;

        // Bounce at edges
        if (node.x < 0 || node.x > width) node.vx *= -1;
        if (node.y < 0 || node.y > height) node.vy *= -1;

        // Slow opacity pulse
        const time = Date.now() * 0.001 + node.pulseOffset;
        node.opacity = 0.2 + 0.3 * Math.sin(time) + eventGlow * 0.5;
        if (node.opacity < 0) node.opacity = 0;
        if (node.opacity > 0.9) node.opacity = 0.9;
      });

      // Draw connections
      ctx.beginPath();
      links.forEach((link) => {
        const na = nodes[link.a];
        const nb = nodes[link.b];
        const dx = na.x - nb.x;
        const dy = na.y - nb.y;
        const dist = Math.sqrt(dx * dx + dy * dy);
        if (dist < connectionDistance) {
          const opacity = link.strength * 0.15 * (1 + eventGlow);
          ctx.moveTo(na.x, na.y);
          ctx.lineTo(nb.x, nb.y);
          ctx.strokeStyle = `rgba(140, 242, 200, ${opacity})`;
          ctx.lineWidth = 0.5;
        }
      });
      ctx.stroke();

      // Draw nodes
      nodes.forEach((node) => {
        ctx.beginPath();
        ctx.arc(node.x, node.y, node.radius, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(255, 106, 0, ${node.opacity})`;
        ctx.fill();

        // Occasional bright flash
        if (Math.random() < 0.01) {
          ctx.beginPath();
          ctx.arc(node.x, node.y, node.radius * 3, 0, Math.PI * 2);
          ctx.fillStyle = `rgba(255, 255, 255, ${0.3 * node.opacity})`;
          ctx.fill();
        }
      });

      animationRef.current = requestAnimationFrame(animate);
    }

    function drawStatic(ctx: CanvasRenderingContext2D, nodes: ConstellationNode[], links: ConstellationLink[]) {
      ctx.beginPath();
      links.forEach((link) => {
        const na = nodes[link.a];
        const nb = nodes[link.b];
        ctx.moveTo(na.x, na.y);
        ctx.lineTo(nb.x, nb.y);
        ctx.strokeStyle = `rgba(140, 242, 200, ${link.strength * 0.08})`;
        ctx.lineWidth = 0.5;
      });
      ctx.stroke();

      nodes.forEach((node) => {
        ctx.beginPath();
        ctx.arc(node.x, node.y, node.radius, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(255, 106, 0, ${node.targetOpacity})`;
        ctx.fill();
      });
    }

    // Expose trigger for economic events
    (window as any).__agentropolisTriggerConstellation = () => {
      eventGlow = 1;
    };

    animate();

    return () => {
      window.removeEventListener('resize', resize);
      if (animationRef.current) cancelAnimationFrame(animationRef.current);
      delete (window as any).__agentropolisTriggerConstellation;
    };
  }, [particleCount, connectionDistance, reducedMotion, width, height]);

  return (
    <canvas
      className={`absolute inset-0 -z-10 pointer-events-none ${className}`}
      ref={canvasRef}
      aria-hidden="true"
    />
  );
}

/** Trigger a constellation flash from a real economic event */
export function triggerConstellationFlash() {
  const fn = (window as any).__agentropolisTriggerConstellation;
  if (fn) fn();
}