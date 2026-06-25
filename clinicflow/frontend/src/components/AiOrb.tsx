import { useEffect, useRef } from 'react';

interface AiOrbProps {
  isSpeaking: boolean;
  isProcessing: boolean;
}

export default function AiOrb({ isSpeaking, isProcessing }: AiOrbProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animationId: number;
    let t = 0;

    // Set high-DPI resolution
    const size = 36; // 36px in CSS
    const dpr = window.devicePixelRatio || 1;
    canvas.width = size * dpr;
    canvas.height = size * dpr;
    canvas.style.width = `${size}px`;
    canvas.style.height = `${size}px`;

    const render = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      
      // Save context and scale for high-DPI
      ctx.save();
      ctx.scale(dpr, dpr);

      // Increment time based on state
      if (isSpeaking) {
        t += 0.045;
      } else if (isProcessing) {
        t += 0.09;
      } else {
        t += 0.015;
      }

      const center = size / 2;
      
      // Determine core size and pulse
      let R = size * 0.28; // base core radius
      if (isSpeaking) {
        R = size * 0.32 + Math.sin(t * 6) * 1.2; // bigger and vibrating
      } else if (isProcessing) {
        R = size * 0.28 + Math.sin(t * 10) * 1.6; // pulsing faster
      } else {
        R = size * 0.25 + Math.sin(t * 2) * 0.4; // very gentle breath
      }

      // Draw background ambient glow (clinical teals and sky blues)
      ctx.beginPath();
      const glowGrad = ctx.createRadialGradient(center, center, 2, center, center, size / 2);
      if (isSpeaking) {
        glowGrad.addColorStop(0, 'rgba(20, 184, 166, 0.45)');
        glowGrad.addColorStop(0.6, 'rgba(6, 182, 212, 0.18)');
        glowGrad.addColorStop(1, 'rgba(6, 182, 212, 0)');
      } else if (isProcessing) {
        glowGrad.addColorStop(0, 'rgba(139, 92, 246, 0.35)');
        glowGrad.addColorStop(0.6, 'rgba(20, 184, 166, 0.12)');
        glowGrad.addColorStop(1, 'rgba(20, 184, 166, 0)');
      } else {
        glowGrad.addColorStop(0, 'rgba(56, 189, 248, 0.25)');
        glowGrad.addColorStop(0.6, 'rgba(20, 184, 166, 0.08)');
        glowGrad.addColorStop(1, 'rgba(20, 184, 166, 0)');
      }
      ctx.fillStyle = glowGrad;
      ctx.arc(center, center, size / 2, 0, 2 * Math.PI);
      ctx.fill();

      // Draw speaking ripples (sound waves propagating outwards)
      if (isSpeaking) {
        const rippleSpeed = t * 1.4;
        for (let k = 0; k < 2; k++) {
          const progress = (rippleSpeed + k * 0.5) % 1.0;
          const rippleRadius = R + progress * (size * 0.46 - R);
          const rippleAlpha = (1.0 - progress) * 0.4;
          
          ctx.beginPath();
          for (let j = 0; j <= 48; j++) {
            const phi = (j / 48) * 2 * Math.PI;
            // sound wave frequency print ripples
            const wave = Math.sin(phi * 8 - t * 15) * 1.4 * (1.0 - progress);
            const r = rippleRadius + wave;
            const rx = center + Math.cos(phi) * r;
            const ry = center + Math.sin(phi) * r;
            if (j === 0) ctx.moveTo(rx, ry);
            else ctx.lineTo(rx, ry);
          }
          ctx.closePath();
          ctx.strokeStyle = `rgba(20, 184, 166, ${rippleAlpha})`;
          ctx.lineWidth = 0.8;
          ctx.stroke();
        }
      }

      // Pre-compute 3D particles and lines
      interface Point3D {
        px: number;
        py: number;
        z3: number;
      }
      
      const rings: Point3D[][] = [];
      const numRings = 3;
      const numPoints = 28;

      for (let r = 0; r < numRings; r++) {
        let roll = 0;
        let pitchOffset = 0;
        let yawOffset = 0;
        
        if (r === 0) {
          roll = 0;
          pitchOffset = t * 0.6;
          yawOffset = t * 0.4;
        } else if (r === 1) {
          roll = Math.PI / 3;
          pitchOffset = -t * 0.5;
          yawOffset = -t * 0.6;
        } else {
          roll = (2 * Math.PI) / 3;
          pitchOffset = t * 0.3;
          yawOffset = -t * 0.8;
        }

        const ringPoints: Point3D[] = [];
        for (let j = 0; j < numPoints; j++) {
          const phi = (j / numPoints) * 2 * Math.PI;

          // Wave distortion for speaking
          let wave = 0;
          if (isSpeaking) {
            wave = (Math.sin(phi * 5 + t * 12) + Math.sin(phi * 9 - t * 9) * 0.3) * 0.16;
          }
          const dist = 1.05 + wave;
          const x0 = Math.cos(phi) * dist;
          const y0 = Math.sin(phi) * dist;
          const z0 = 0;

          // Rotations:
          // Z-axis (roll)
          const x1 = x0 * Math.cos(roll) - y0 * Math.sin(roll);
          const y1 = x0 * Math.sin(roll) + y0 * Math.cos(roll);
          const z1 = z0;

          // X-axis (pitch)
          const x2 = x1;
          const y2 = y1 * Math.cos(pitchOffset) - z1 * Math.sin(pitchOffset);
          const z2 = y1 * Math.sin(pitchOffset) + z1 * Math.cos(pitchOffset);

          // Y-axis (yaw)
          const x3 = x2 * Math.cos(yawOffset) + z2 * Math.sin(yawOffset);
          const y3 = y2;
          const z3 = -x2 * Math.sin(yawOffset) + z2 * Math.cos(yawOffset);

          // 2D projection
          const ringRad = size * 0.38;
          const scale = ringRad * (1 + z3 * 0.18);
          const px = center + x3 * scale;
          const py = center + y3 * scale;

          ringPoints.push({ px, py, z3 });
        }
        rings.push(ringPoints);
      }

      // Draw faint hologram wireframe lines
      ctx.lineWidth = 0.5;
      for (let r = 0; r < numRings; r++) {
        ctx.beginPath();
        const rPoints = rings[r];
        ctx.moveTo(rPoints[0].px, rPoints[0].py);
        for (let j = 1; j < numPoints; j++) {
          ctx.lineTo(rPoints[j].px, rPoints[j].py);
        }
        ctx.lineTo(rPoints[0].px, rPoints[0].py);
        
        if (isSpeaking) {
          ctx.strokeStyle = 'rgba(45, 212, 191, 0.25)';
        } else if (isProcessing) {
          ctx.strokeStyle = 'rgba(139, 92, 246, 0.2)';
        } else {
          ctx.strokeStyle = 'rgba(56, 189, 248, 0.18)';
        }
        ctx.stroke();
      }

      // Gather all particles to draw with Z depth sorting
      interface SortedParticle {
        x: number;
        y: number;
        z: number;
        color: string;
        size: number;
      }
      const particles: SortedParticle[] = [];

      for (let r = 0; r < numRings; r++) {
        const rPoints = rings[r];
        for (let j = 0; j < numPoints; j++) {
          const pt = rPoints[j];
          let color = '';
          let pSize = 0.7;
          
          if (isSpeaking) {
            const alpha = Math.max(0.18, 0.7 + pt.z3 * 0.3);
            color = `rgba(45, 212, 191, ${alpha})`;
            pSize = Math.max(0.5, (1.0 + pt.z3 * 0.5) * 1.25);
          } else if (isProcessing) {
            const alpha = Math.max(0.15, 0.6 + pt.z3 * 0.3);
            color = `rgba(139, 92, 246, ${alpha})`;
            pSize = Math.max(0.4, (0.85 + pt.z3 * 0.4) * 1.1);
          } else {
            const alpha = Math.max(0.1, 0.45 + pt.z3 * 0.35);
            color = `rgba(56, 189, 248, ${alpha})`;
            pSize = Math.max(0.35, 0.7 + pt.z3 * 0.3);
          }

          particles.push({
            x: pt.px,
            y: pt.py,
            z: pt.z3,
            color,
            size: pSize
          });
        }
      }

      // Sort by Z coordinate ascending (back to front)
      particles.sort((a, b) => a.z - b.z);

      // Draw back particles (z < 0)
      for (const p of particles) {
        if (p.z >= 0) break;
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.size, 0, 2 * Math.PI);
        ctx.fillStyle = p.color;
        ctx.fill();
      }

      // Draw the core sphere (middle layer)
      ctx.beginPath();
      ctx.arc(center, center, R, 0, 2 * Math.PI);
      
      const coreGrad = ctx.createRadialGradient(
        center - R * 0.25, 
        center - R * 0.25, 
        R * 0.08, 
        center, 
        center, 
        R
      );
      
      if (isSpeaking) {
        coreGrad.addColorStop(0, 'rgba(255, 255, 255, 0.98)');
        coreGrad.addColorStop(0.2, 'rgba(45, 212, 191, 0.95)'); // Teal-400
        coreGrad.addColorStop(0.7, 'rgba(13, 148, 136, 0.85)'); // Teal-600
        coreGrad.addColorStop(1, 'rgba(4, 47, 46, 0.95)');
      } else if (isProcessing) {
        coreGrad.addColorStop(0, 'rgba(255, 255, 255, 0.98)');
        coreGrad.addColorStop(0.2, 'rgba(139, 92, 246, 0.95)'); // Violet-500
        coreGrad.addColorStop(0.7, 'rgba(45, 212, 191, 0.8)'); // Teal-400 (shifting!)
        coreGrad.addColorStop(1, 'rgba(15, 23, 42, 0.98)');
      } else {
        coreGrad.addColorStop(0, 'rgba(255, 255, 255, 0.95)');
        coreGrad.addColorStop(0.2, 'rgba(56, 189, 248, 0.88)'); // Sky-400
        coreGrad.addColorStop(0.7, 'rgba(13, 148, 136, 0.75)'); // Teal-600
        coreGrad.addColorStop(1, 'rgba(15, 23, 42, 0.98)');
      }
      
      ctx.fillStyle = coreGrad;
      ctx.fill();

      // Core Highlight/Shine layer for 3D glass texture
      ctx.beginPath();
      ctx.ellipse(center - R * 0.25, center - R * 0.25, R * 0.4, R * 0.2, -Math.PI / 4, 0, 2 * Math.PI);
      const highlightGrad = ctx.createLinearGradient(
        center - R * 0.4, 
        center - R * 0.4, 
        center - R * 0.1, 
        center - R * 0.1
      );
      highlightGrad.addColorStop(0, 'rgba(255, 255, 255, 0.6)');
      highlightGrad.addColorStop(1, 'rgba(255, 255, 255, 0)');
      ctx.fillStyle = highlightGrad;
      ctx.fill();

      // Draw front particles (z >= 0)
      for (const p of particles) {
        if (p.z < 0) continue;
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.size, 0, 2 * Math.PI);
        ctx.fillStyle = p.color;
        ctx.fill();
      }

      ctx.restore();
      animationId = requestAnimationFrame(render);
    };

    render();

    return () => {
      cancelAnimationFrame(animationId);
    };
  }, [isSpeaking, isProcessing]);

  return (
    <div className="relative flex items-center justify-center">
      <canvas 
        ref={canvasRef} 
        className="block select-none pointer-events-none drop-shadow-[0_0_10px_rgba(20,184,166,0.35)]"
      />
    </div>
  );
}
