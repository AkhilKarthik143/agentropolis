/**
 * Agentropolis — Procedural Grid Distortion
 *
 * Subtle, slow-moving grid that warps gently over time. Cursor-driven parallax
 * gives a sense of spatial depth. Market health modulates the grid's color
 * and distortion intensity.
 *
 * Canvas 2D — cheap, reactive, atmospheric.
 */

import { useEffect, useRef, useState } from 'react';
import { useReducedMotion } from 'motion/react';

interface GridPoint {
  x: number;
  y: number;
  ox: number; // original x
  oy: number; // original y
}

export function ProceduralGrid({
  className = '',
  marketHealth = 0.7, // 0-1, affects color and distortion
  cursorX = 0,
  cursorY = 0,
}: {
  className?: string;
  marketHealth?: number;
  cursorX?: number;
  cursorY?: number;
}) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animationRef = useRef<number | null>(null);
  const reducedMotion = useReducedMotion();
  const [width, setWidth] = useState(0);
  const [height, setHeight] = useState(0);
  const pointsRef = useRef<GridPoint[]>([]);

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

      // Build grid points
      const spacing = 40;
      const cols = Math.ceil(rect.width / spacing) + 2;
      const rows = Math.ceil(rect.height / spacing) + 2;
      const points: GridPoint[] = [];
      for (let row = 0; row < rows; row++) {
        for (let col = 0; col < cols; col++) {
          const x = col * spacing - spacing;
          const y = row * spacing - spacing;
          points.push({ x, y, ox: x, oy: y });
        }
      }
      pointsRef.current = points;
    };
    resize();
    window.addEventListener('resize', resize);

    let time = 0;

    function animate() {
      if (reducedMotion) {
        drawStatic(ctx, pointsRef.current, width, height);
        animationRef.current = requestAnimationFrame(animate);
        return;
      }

      time += 0.002;
      ctx.clearRect(0, 0, width, height);

      const spacing = 40;
      const waveAmp = 8 * (1 - marketHealth * 0.5); // less healthy = more distortion
      const cursorInfluence = 60;

      // Compute distorted points
      const points = pointsRef.current.map((p) => {
        const dx = p.x - cursorX;
        const dy = p.y - cursorY;
        const distToCursor = Math.sqrt(dx * dx + dy * dy);
        const cursorPush = distToCursor < cursorInfluence ? (1 - distToCursor / cursorInfluence) * 20 : 0;

        const cursorXoff = (dx / Math.max(distToCursor, 1)) * cursorPush;
        const cursorYoff = (dy / Math.max(distToCursor, 1)) * cursorPush;

        return {
          x: p.ox + Math.cos(time * 0.5 + p.oy * 0.1) * waveAmp * 0.5 + cursorXoff,
          y: p.oy + Math.sin(time * 0.5 + p.ox * 0.1) * waveAmp * 0.5 + cursorYoff,
        };
      });

      // Color shifts with market health: teal (healthy) → amber (stressed)
      const r = Math.round(140 * (1 - marketHealth) + 255 * marketHealth);
      const g = Math.round(242 * marketHealth + 180 * (1 - marketHealth));
      const b = Math.round(200 * marketHealth + 80 * (1 - marketHealth));

      ctx.strokeStyle = `rgba(${r}, ${g}, ${b}, 0.08)`;
      ctx.lineWidth = 1;
      ctx.lineCap = 'round';

      // Draw horizontal lines
      const rows = Math.ceil(height / spacing) + 2;
      const cols = Math.ceil(width / spacing) + 2;
      for (let row = 0; row < rows; row++) {
        ctx.beginPath();
        for (let col = 0; col < cols; col++) {
          const idx = row * cols + col;
          const p = points[idx];
          if (col === 0) ctx.moveTo(p.x, p.y);
          else ctx.lineTo(p.x, p.y);
        }
        ctx.stroke();
      }

      // Draw vertical lines
      for (let col = 0; col < cols; col++) {
        ctx.beginPath();
        for (let row = 0; row < rows; row++) {
          const idx = row * cols + col;
          const p = points[idx];
          if (row === 0) ctx.moveTo(p.x, p.y);
          else ctx.lineTo(p.x, p.y);
        }
        ctx.stroke();
      }

      // Draw intersection nodes - faint
      ctx.fillStyle = `rgba(${r}, ${g}, ${b}, 0.15)`;
      points.forEach((p) => {
        ctx.beginPath();
        ctx.arc(p.x, p.y, 1.2, 0, Math.PI * 2);
        ctx.fill();
      });

      animationRef.current = requestAnimationFrame(animate);
    }

    function drawStatic(ctx: CanvasRenderingContext2D, points: GridPoint[], w: number, h: number) {
      const spacing = 40;
      const cols = Math.ceil(w / spacing) + 2;
      const rows = Math.ceil(h / spacing) + 2;
      ctx.strokeStyle = 'rgba(140, 242, 200, 0.06)';
      ctx.lineWidth = 1;
      for (let row = 0; row < rows; row++) {
        ctx.beginPath();
        for (let col = 0; col < cols; col++) {
          const p = points[row * cols + col];
          if (col === 0) ctx.moveTo(p.ox, p.oy);
          else ctx.lineTo(p.ox, p.oy);
        }
        ctx.stroke();
      }
      for (let col = 0; col < cols; col++) {
        ctx.beginPath();
        for (let row = 0; row < rows; row++) {
          const p = points[row * cols + col];
          if (row === 0) ctx.moveTo(p.ox, p.oy);
          else ctx.lineTo(p.ox, p.oy);
        }
        ctx.stroke();
      }
    }

    animate();

    return () => {
      window.removeEventListener('resize', resize);
      if (animationRef.current) cancelAnimationFrame(animationRef.current);
    };
  }, [marketHealth, cursorX, cursorY, reducedMotion, width, height]);

  return (
    <canvas
      className={`absolute inset-0 -z-10 pointer-events-none ${className}`}
      ref={canvasRef}
      aria-hidden="true"
    />
  );
}