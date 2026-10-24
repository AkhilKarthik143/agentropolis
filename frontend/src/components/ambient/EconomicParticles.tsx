/**
 * Agentropolis — Economic Particle System
 *
 * Canvas 2D particle flows representing financial transactions moving between
 * business nodes. Particles spawn on real payment events, travel along curved
 * paths, and fade out on arrival.
 *
 * Each particle carries: amount (size), direction, type (payment/offer/alert),
 * and lifecycle state.
 */

import { useEffect, useRef, useState } from 'react';
import { useReducedMotion } from 'motion/react';

interface FlowParticle {
  id: string;
  x: number;
  y: number;
  targetX: number;
  targetY: number;
  progress: number; // 0-1
  speed: number;
  size: number;
  opacity: number;
  color: string;
  type: 'payment' | 'offer' | 'alert' | 'recovery';
  completed: boolean;
}

interface ParticleSpawn {
  fromX: number;
  fromY: number;
  toX: number;
  toY: number;
  type?: 'payment' | 'offer' | 'alert' | 'recovery';
  amountCents?: number;
}

export function EconomicParticles({ className = '' }: { className?: string }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animationRef = useRef<number | null>(null);
  const reducedMotion = useReducedMotion();
  const [width, setWidth] = useState(0);
  const [height, setHeight] = useState(0);
  const particlesRef = useRef<FlowParticle[]>([]);
  const spawnQueueRef = useRef<ParticleSpawn[]>([]);

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

    // Expose spawn function globally so the motion coordinator can trigger particles
    (window as any).__agentropolisSpawnParticle = (spawn: ParticleSpawn) => {
      spawnQueueRef.current.push(spawn);
    };

    let lastTime = 0;

    function animate(timestamp: number) {
      if (reducedMotion) {
        animationRef.current = requestAnimationFrame(animate);
        return;
      }

      const dt = timestamp - lastTime;
      lastTime = timestamp;

      ctx.clearRect(0, 0, width, height);

      // Process spawn queue
      while (spawnQueueRef.current.length > 0) {
        const spawn = spawnQueueRef.current.shift()!;
        const dx = spawn.toX - spawn.fromX;
        const dy = spawn.toY - spawn.fromY;
        const dist = Math.sqrt(dx * dx + dy * dy);
        const duration = Math.max(600, dist * 1.2); // ms
        const size = spawn.amountCents ? Math.min(4, 1 + Math.log10(spawn.amountCents / 100)) : 2;

        const color = spawn.type === 'alert' ? '#ff4757' : spawn.type === 'offer' ? '#ffbe76' : spawn.type === 'recovery' ? '#8cf2c8' : '#ff6a00';

        particlesRef.current.push({
          id: Math.random().toString(36).slice(2),
          x: spawn.fromX,
          y: spawn.fromY,
          targetX: spawn.toX,
          targetY: spawn.toY,
          progress: 0,
          speed: 1 / duration,
          size,
          opacity: 0,
          color,
          type: spawn.type ?? 'payment',
          completed: false,
        });
      }

      // Update and draw particles
      for (let i = particlesRef.current.length - 1; i >= 0; i--) {
        const p = particlesRef.current[i];
        if (p.completed) {
          particlesRef.current.splice(i, 1);
          continue;
        }

        p.progress += p.speed * (16 / dt > 0 ? dt / 16 : 1); // normalize to ~60fps
        if (p.progress > 1) p.progress = 1;

        // Ease: slow start, fast middle, slow end
        const eased = 1 - Math.pow(1 - p.progress, 3);
        p.x = p.x + (p.targetX - p.x) * 0.15 + (p.targetX - spawnFromX(p)) * 0;
        // Use quadratic bezier for flow
        const cx = (p.x + p.targetX) / 2 + (Math.random() - 0.5) * 40;
        const cy = (p.y + p.targetY) / 2 + (Math.random() - 0.5) * 40;
        const bx = (1 - eased) ** 2 * p.x + 2 * (1 - eased) * eased * cx + eased ** 2 * p.targetX;
        const by = (1 - eased) ** 2 * p.y + 2 * (1 - eased) * eased * cy + eased ** 2 * p.targetY;

        p.x = bx;
        p.y = by;
        p.opacity = eased;

        // Draw particle
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
        ctx.fillStyle = p.color;
        ctx.globalAlpha = p.opacity;
        ctx.fill();
        ctx.globalAlpha = 1;

        // Glow trail
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.size * 1.5, 0, Math.PI * 2);
        ctx.fillStyle = p.color;
        ctx.globalAlpha = p.opacity * 0.4;
        ctx.fill();
        ctx.globalAlpha = 1;

        if (p.progress >= 1) p.completed = true;
      }

      animationRef.current = requestAnimationFrame(animate);
    }

    function spawnFromX(p: FlowParticle): number {
      return p.x; // approximation
    }

    animationRef.current = requestAnimationFrame(animate);

    return () => {
      window.removeEventListener('resize', resize);
      if (animationRef.current) cancelAnimationFrame(animationRef.current);
      delete (window as any).__agentropolisSpawnParticle;
    };
  }, [reducedMotion, width, height]);

  return (
    <canvas
      className={`absolute inset-0 -z-10 pointer-events-none ${className}`}
      ref={canvasRef}
      aria-hidden="true"
    />
  );
}

/** Trigger a particle flow from code */
export function spawnEconomicParticle(spawn: ParticleSpawn) {
  const fn = (window as any).__agentropolisSpawnParticle;
  if (fn) fn(spawn);
}