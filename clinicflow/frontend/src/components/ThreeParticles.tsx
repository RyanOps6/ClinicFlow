import React, { useEffect, useRef } from 'react';
import * as THREE from 'three';

export default function ThreeParticles() {
  const containerRef = useRef<HTMLDivElement>(null);
  const mouseRef = useRef({ x: 0, y: 0, targetX: 0, targetY: 0 });

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    // Dimensions
    let width = container.clientWidth || window.innerWidth;
    let height = container.clientHeight || window.innerHeight;

    // Renderer - Alpha transparent profile
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(width, height);
    renderer.setClearColor(0x000000, 0); // Completely transparent background
    container.appendChild(renderer.domElement);

    // Scene
    const scene = new THREE.Scene();

    // Camera
    const camera = new THREE.PerspectiveCamera(60, width / height, 0.1, 100);
    camera.position.z = 5;

    // Particle Count (500-600)
    const particleCount = 550;
    const geometry = new THREE.BufferGeometry();
    const positions = new Float32Array(particleCount * 3);
    const colors = new Float32Array(particleCount * 3);
    const velocities: { x: number; y: number; z: number }[] = [];

    // Colors: electric-blue (#22d3ee) and soft gold (#fbbf24)
    // Electric blue RGB: 0.13, 0.82, 0.93
    // Soft gold RGB: 0.98, 0.75, 0.14
    for (let i = 0; i < particleCount; i++) {
      positions[i * 3] = (Math.random() - 0.5) * 12;     // X coordinate
      positions[i * 3 + 1] = (Math.random() - 0.5) * 8;  // Y coordinate
      positions[i * 3 + 2] = (Math.random() - 0.5) * 6;  // Z coordinate

      const isBlue = Math.random() > 0.35;
      if (isBlue) {
        colors[i * 3] = 0.13;
        colors[i * 3 + 1] = 0.82;
        colors[i * 3 + 2] = 0.93;
      } else {
        colors[i * 3] = 0.98;
        colors[i * 3 + 1] = 0.75;
        colors[i * 3 + 2] = 0.14;
      }

      // Initial organic floating drift velocities
      velocities.push({
        x: (Math.random() - 0.5) * 0.002,
        y: (Math.random() - 0.5) * 0.002,
        z: (Math.random() - 0.5) * 0.0015,
      });
    }

    geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));

    // Create a white radial gradient texture so vertex colors are applied cleanly
    const makeWhiteGlowTexture = () => {
      const size = 64;
      const canvas = document.createElement('canvas');
      canvas.width = size;
      canvas.height = size;
      const ctx = canvas.getContext('2d')!;
      const gradient = ctx.createRadialGradient(
        size / 2, size / 2, 0,
        size / 2, size / 2, size / 2
      );
      gradient.addColorStop(0, 'rgba(255,255,255,1)');
      gradient.addColorStop(0.4, 'rgba(255,255,255,0.5)');
      gradient.addColorStop(1, 'rgba(255,255,255,0)');
      ctx.fillStyle = gradient;
      ctx.fillRect(0, 0, size, size);
      const texture = new THREE.CanvasTexture(canvas);
      texture.needsUpdate = true;
      return texture;
    };

    const material = new THREE.PointsMaterial({
      size: 0.15, // Radiant size
      map: makeWhiteGlowTexture(),
      transparent: true,
      opacity: 0.85,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
      vertexColors: true,
    });

    const points = new THREE.Points(geometry, material);
    scene.add(points);

    // Mouse metrics to track speed and coordinate sweeps
    let lastMouseTime = Date.now();
    let lastMouseX = 0;
    let lastMouseY = 0;
    let mouseSpeed = 0;

    const handleMouseMove = (e: MouseEvent) => {
      const nx = (e.clientX / window.innerWidth) * 2 - 1;
      const ny = -(e.clientY / window.innerHeight) * 2 + 1;
      mouseRef.current.targetX = nx;
      mouseRef.current.targetY = ny;

      const now = Date.now();
      const dt = now - lastMouseTime;
      if (dt > 0) {
        const dx = e.clientX - lastMouseX;
        const dy = e.clientY - lastMouseY;
        const dist = Math.sqrt(dx * dx + dy * dy);
        // Smoothly filter the speed value
        mouseSpeed = mouseSpeed * 0.8 + (dist / dt) * 0.2;
      }
      lastMouseX = e.clientX;
      lastMouseY = e.clientY;
      lastMouseTime = now;
    };

    window.addEventListener('mousemove', handleMouseMove);

    // Resize handling
    const handleResize = () => {
      if (!container) return;
      width = container.clientWidth || window.innerWidth;
      height = container.clientHeight || window.innerHeight;
      renderer.setSize(width, height);
      camera.aspect = width / height;
      camera.updateProjectionMatrix();
    };

    window.addEventListener('resize', handleResize);

    // Animation Loop
    let animationId: number;
    const posArr = geometry.attributes.position.array as Float32Array;

    const tick = () => {
      // Slow decay of mouse speed when mouse stops moving
      mouseSpeed *= 0.96;
      const speedMultiplier = 1.0 + Math.min(mouseSpeed * 1.5, 8.0);

      // 1. Particle position updating with speed multiplier
      for (let i = 0; i < particleCount; i++) {
        posArr[i * 3] += velocities[i].x * speedMultiplier;
        posArr[i * 3 + 1] += velocities[i].y * speedMultiplier;
        posArr[i * 3 + 2] += velocities[i].z * speedMultiplier;

        // Viewport boundaries wrap-around
        if (posArr[i * 3] > 6) posArr[i * 3] = -6;
        if (posArr[i * 3] < -6) posArr[i * 3] = 6;
        if (posArr[i * 3 + 1] > 4) posArr[i * 3 + 1] = -4;
        if (posArr[i * 3 + 1] < -4) posArr[i * 3 + 1] = 4;
        if (posArr[i * 3 + 2] > 3) posArr[i * 3 + 2] = -3;
        if (posArr[i * 3 + 2] < -3) posArr[i * 3 + 2] = 3;
      }
      geometry.attributes.position.needsUpdate = true;

      // 2. Interpolate mouse positions for smooth parallax warping
      const mouse = mouseRef.current;
      mouse.x += (mouse.targetX - mouse.x) * 0.05;
      mouse.y += (mouse.targetY - mouse.y) * 0.05;

      // Parallactic warp shifting
      points.position.x = mouse.x * 0.55;
      points.position.y = mouse.y * 0.55;

      // Continuous subtle rotation
      points.rotation.y += 0.0004;
      points.rotation.z += 0.00015;

      renderer.render(scene, camera);
      animationId = requestAnimationFrame(tick);
    };

    tick();

    // Cleanup
    return () => {
      cancelAnimationFrame(animationId);
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('resize', handleResize);
      if (container && renderer.domElement) {
        container.removeChild(renderer.domElement);
      }
      geometry.dispose();
      material.dispose();
      renderer.dispose();
    };
  }, []);

  return (
    <div 
      ref={containerRef} 
      className="absolute inset-0 w-full h-full pointer-events-none z-15"
    />
  );
}
