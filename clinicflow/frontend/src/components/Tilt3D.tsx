import React, { useRef } from 'react';

interface Tilt3DProps {
  children: React.ReactNode;
  className?: string;
  maxTilt?: number; // Maximum tilt angle in degrees
}

export default function Tilt3D({ children, className = '', maxTilt = 10 }: Tilt3DProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    const el = containerRef.current;
    if (!el) return;

    const rect = el.getBoundingClientRect();
    const x = e.clientX - rect.left; // cursor x position relative to element
    const y = e.clientY - rect.top;  // cursor y position relative to element

    const halfWidth = rect.width / 2;
    const halfHeight = rect.height / 2;

    // Normalized coordinates (-1 to 1)
    const normX = (x - halfWidth) / halfWidth;
    const normY = (y - halfHeight) / halfHeight;

    // Compute rotation angles
    const rotateY = normX * maxTilt;
    const rotateX = -normY * maxTilt;

    // Apply 3D matrix transform directly to inline styles for optimal performance (bypassing React render cycles)
    el.style.transform = `perspective(1000px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) translateZ(12px)`;
    el.style.transition = 'transform 0.1s ease-out, box-shadow 0.1s ease-out';
  };

  const handleMouseLeave = () => {
    const el = containerRef.current;
    if (!el) return;

    // Smoothly snap back to origin
    el.style.transform = 'perspective(1000px) rotateX(0deg) rotateY(0deg) translateZ(0px)';
    el.style.transition = 'transform 0.5s cubic-bezier(0.25, 1, 0.5, 1), box-shadow 0.5s cubic-bezier(0.25, 1, 0.5, 1)';
  };

  return (
    <div
      ref={containerRef}
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
      className={className}
      style={{ transformStyle: 'preserve-3d' }}
    >
      {children}
    </div>
  );
}
