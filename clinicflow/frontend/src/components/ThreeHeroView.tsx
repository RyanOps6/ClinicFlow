import React, { useState, useEffect, useRef } from 'react';
import Spline from '@splinetool/react-spline';
import * as THREE from 'three';

// --- GLSL Noise and Shader Definitions for local Three.js Shader Orb ---
const vertexShader = `
  uniform float uTime;
  uniform vec2 uMouse;
  varying vec3 vNormal;
  varying vec3 vViewPosition;
  varying vec3 vPosition;
  varying float vNoise;

  // Description : Array and textureless GLSL 2D/3D/4D simplex noise functions.
  //      Author : Ian McEwan, Ashima Arts.
  //  Maintainer : stegu
  //     Lastmod : 20110822 (ijm)
  //     License : Copyright (C) 2011 Ashima Arts. All rights reserved.
  //               Distributed under the MIT License. See LICENSE file.
  //               https://github.com/ashima/webgl-noise

  vec3 mod289(vec3 x) { return x - floor(x * (1.0 / 289.0)) * 289.0; }
  vec4 mod289(vec4 x) { return x - floor(x * (1.0 / 289.0)) * 289.0; }
  vec4 permute(vec4 x) { return mod289(((x*34.0)+1.0)*x); }
  vec4 taylorInvSqrt(vec4 r) { return 1.79284291400159 - 0.85373472095314 * r; }

  float snoise(vec3 v) {
    const vec2 C = vec2(1.0/6.0, 1.0/3.0);
    const vec4 D = vec4(0.0, 0.5, 1.0, 2.0);

    vec3 i  = floor(v + dot(v, C.yyy));
    vec3 x0 = v - i + dot(i, C.xxx);

    vec3 g = step(x0.yzx, x0.xyz);
    vec3 l = 1.0 - g;
    vec3 i1 = min(g.xyz, l.zxy);
    vec3 i2 = max(g.xyz, l.zxy);

    vec3 x1 = x0 - i1 + C.xxx;
    vec3 x2 = x0 - i2 + C.yyy;
    vec3 x3 = x0 - D.yyy;

    i = mod289(i);
    vec4 p = permute(permute(permute(
               i.z + vec4(0.0, i1.z, i2.z, 1.0))
             + i.y + vec4(0.0, i1.y, i2.y, 1.0))
             + i.x + vec4(0.0, i1.x, i2.x, 1.0));

    float n_ = 0.142857142857;
    vec3 ns = n_ * D.wyz - D.xzx;

    vec4 j = p - 49.0 * floor(p * ns.z);

    vec4 x_ = floor(j * ns.z);
    vec4 y_ = floor(j - 7.0 * x_);

    vec4 x = x_ *ns.x + ns.yyyy;
    vec4 y = y_ *ns.x + ns.yyyy;
    vec4 h = 1.0 - abs(x) - abs(y);

    vec4 b0 = vec4(x.xy, y.xy);
    vec4 b1 = vec4(x.zw, y.zw);

    vec4 s0 = floor(b0)*2.0 + 1.0;
    vec4 s1 = floor(b1)*2.0 + 1.0;
    vec4 sh = -step(h, vec4(0.0));

    vec4 a0 = b0.xzyw + s0.xzyw*sh.xxyy;
    vec4 a1 = b1.xzyw + s1.xzyw*sh.zzww;

    vec3 p0 = vec3(a0.xy, h.x);
    vec3 p1 = vec3(a0.zw, h.y);
    vec3 p2 = vec3(a1.xy, h.z);
    vec3 p3 = vec3(a1.zw, h.w);

    vec4 norm = taylorInvSqrt(vec4(dot(p0,p0), dot(p1,p1), dot(p2,p2), dot(p3,p3)));
    p0 *= norm.x;
    p1 *= norm.y;
    p2 *= norm.z;
    p3 *= norm.w;

    vec4 m = max(0.6 - vec4(dot(x0,x0), dot(x1,x1), dot(x2,x2), dot(x3,x3)), 0.0);
    m = m * m;
    return 42.0 * dot(m*m, vec4(dot(p0,x0), dot(p1,x1), dot(p2,x2), dot(p3,x3)));
  }

  void main() {
    vNormal = normalize(normalMatrix * normal);
    
    // Wave coordinates
    vec3 coords = position * 1.5 + vec3(0.0, 0.0, uTime * 0.3);
    float noise = snoise(coords);
    vNoise = noise;
    
    // Interactive scale factor based on mouse vector offset
    float amp = 0.12 + (length(uMouse) * 0.06);
    vec3 displaced = position + normal * (noise * amp);
    
    vec4 mvPosition = modelViewMatrix * vec4(displaced, 1.0);
    vViewPosition = -mvPosition.xyz;
    vPosition = displaced;
    
    gl_Position = projectionMatrix * mvPosition;
  }
`;

const fragmentShader = `
  uniform float uTime;
  uniform vec2 uMouse;
  uniform vec3 uColorTeal;
  uniform vec3 uColorSky;
  uniform vec3 uColorPurple;
  varying vec3 vNormal;
  varying vec3 vViewPosition;
  varying vec3 vPosition;
  varying float vNoise;

  void main() {
    vec3 normal = normalize(vNormal);
    vec3 viewDir = normalize(vViewPosition);
    
    // Fresnel transparency factor
    float fresnel = pow(1.0 - max(dot(normal, viewDir), 0.0), 3.0);
    
    // Light source vector reacts dynamically to mouse coordinates
    vec3 lightDir = normalize(vec3(uMouse.x * 2.5, uMouse.y * 2.5, 2.0));
    vec3 halfDir = normalize(lightDir + viewDir);
    float spec = pow(max(dot(normal, halfDir), 0.0), 40.0);
    
    // Mix clinical teals, cyans, and deep violet/purples
    float baseGrad = dot(normal, vec3(0.0, 1.0, 0.0)) * 0.5 + 0.5;
    vec3 baseColor = mix(uColorTeal, uColorSky, baseGrad);
    
    // Dynamic noise ripple influence
    vec3 finalGlassColor = mix(baseColor, uColorPurple, fresnel + (vNoise * 0.2));
    
    // Add bright iridescent edge glow
    vec3 rimGlow = vec3(0.4, 0.95, 0.85) * fresnel;
    
    // Specular highlight reflection
    vec3 specularHighlight = vec3(1.0) * spec * 0.95;
    
    vec3 color = finalGlassColor * (0.45 + fresnel * 0.55) + rimGlow + specularHighlight;
    
    // Opacity layer mapping: core is semi-translucent glass, rim is highly opaque and reflective
    float opacity = mix(0.4, 0.95, fresnel);
    
    gl_FragColor = vec4(color, opacity);
  }
`;

function ThreeShaderOrb() {
  const containerRef = useRef<HTMLDivElement>(null);
  const mouseRef = useRef({ x: 0, y: 0, targetX: 0, targetY: 0 });

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    // Dimensions
    const width = container.clientWidth || 400;
    const height = container.clientHeight || 400;

    // Renderer
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(width, height);
    container.appendChild(renderer.domElement);

    // Scene
    const scene = new THREE.Scene();

    // Camera
    const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 100);
    camera.position.z = 4.2;

    // Geometry
    const geometry = new THREE.SphereGeometry(1.4, 64, 64);

    // Material Uniforms
    const uniforms = {
      uTime: { value: 0 },
      uMouse: { value: new THREE.Vector2(0, 0) },
      uColorTeal: { value: new THREE.Color(0.05, 0.58, 0.53) }, // #0d9488
      uColorSky: { value: new THREE.Color(0.01, 0.52, 0.78) },  // #0284c7
      uColorPurple: { value: new THREE.Color(0.49, 0.23, 0.93) }, // #7c3aed
    };

    const material = new THREE.ShaderMaterial({
      vertexShader,
      fragmentShader,
      uniforms,
      transparent: true,
      depthWrite: true,
      depthTest: true,
    });

    // Mesh
    const mesh = new THREE.Mesh(geometry, material);
    scene.add(mesh);

    // Dynamic mouse listeners
    const handleMouseMove = (e: MouseEvent) => {
      const rect = container.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      
      const nx = (x / rect.width) * 2 - 1;
      const ny = -(y / rect.height) * 2 + 1;

      mouseRef.current.targetX = nx;
      mouseRef.current.targetY = ny;
    };

    window.addEventListener('mousemove', handleMouseMove);

    // Resize handling
    const resizeObserver = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const w = entry.contentRect.width;
        const h = entry.contentRect.height;
        renderer.setSize(w, h);
        camera.aspect = w / h;
        camera.updateProjectionMatrix();
      }
    });
    resizeObserver.observe(container);

    // Animation Loop
    const clock = new THREE.Clock();
    let animationId: number;

    const tick = () => {
      const elapsedTime = clock.getElapsedTime();
      
      // Interpolate/Lerp mouse coordinates for heavy dragging inertia
      const mouse = mouseRef.current;
      mouse.x += (mouse.targetX - mouse.x) * 0.05;
      mouse.y += (mouse.targetY - mouse.y) * 0.05;

      // Update uniforms
      uniforms.uTime.value = elapsedTime;
      uniforms.uMouse.value.set(mouse.x, mouse.y);

      // Rotate sphere mesh based on cursor coordinates
      mesh.rotation.y = mouse.x * 0.4;
      mesh.rotation.x = -mouse.y * 0.4;
      
      // Gentle constant rotation spin
      mesh.rotation.z = elapsedTime * 0.05;

      renderer.render(scene, camera);
      animationId = requestAnimationFrame(tick);
    };

    tick();

    // Clean up
    return () => {
      cancelAnimationFrame(animationId);
      window.removeEventListener('mousemove', handleMouseMove);
      resizeObserver.disconnect();
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
      className="w-full h-full min-h-[320px] max-h-[450px] relative flex items-center justify-center pointer-events-auto"
      style={{ cursor: 'grab' }}
    />
  );
}

class SplineErrorBoundary extends React.Component<
  { children: React.ReactNode; fallback: React.ReactNode; onError: () => void },
  { hasError: boolean }
> {
  constructor(props: any) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error: any, errorInfo: any) {
    console.error("Spline layout or rendering crashed, recovering via Three.js fallback:", error, errorInfo);
    this.props.onError();
  }

  render() {
    if (this.state.hasError) {
      return this.props.fallback;
    }
    return this.props.children;
  }
}

export default function ThreeHeroView() {
  const [offlineFallback, setOfflineFallback] = useState(false);
  const [hasError, setHasError] = useState(false);
  const [splineLoading, setSplineLoading] = useState(true);

  useEffect(() => {
    // Force immediate Three.js local shader fallback if the user is offline
    if (typeof navigator !== 'undefined' && !navigator.onLine) {
      setOfflineFallback(true);
      setSplineLoading(false);
      return;
    }

    // Set a timeout. If Spline scene has not fully loaded in 3.5s, switch to shader for instant UX.
    const timer = setTimeout(() => {
      if (splineLoading && !hasError) {
        console.warn('Spline load timed out. Falling back to local Three.js ambient shader.');
        setOfflineFallback(true);
        setSplineLoading(false);
      }
    }, 3500);

    return () => clearTimeout(timer);
  }, [splineLoading, hasError]);

  const handleSplineError = () => {
    console.error('Spline failed to load or parse. Rendering Three.js glass sphere fallback.');
    setHasError(true);
    setSplineLoading(false);
  };

  if (offlineFallback || hasError) {
    return (
      <div className="w-full h-full flex flex-col items-center justify-center relative">
        <div className="absolute inset-0 bg-gradient-radial from-teal-500/10 via-transparent to-transparent blur-3xl pointer-events-none" />
        <ThreeShaderOrb />
        <div className="absolute bottom-4 left-1/2 transform -translate-x-1/2 text-center pointer-events-none">
          <p className="text-[10px] font-semibold uppercase tracking-widest text-teal-600/70">
            Ambient Glass Shader (Fallback Active)
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full h-full flex flex-col items-center justify-center relative">
      {splineLoading && (
        <div className="absolute inset-0 flex flex-col items-center justify-center z-20 bg-white/40 backdrop-blur-sm transition-all duration-300">
          <div className="w-10 h-10 border-2 border-teal-500/30 border-t-teal-600 rounded-full animate-spin" />
          <span className="text-[10px] uppercase font-bold text-slate-500 tracking-wider mt-3">Connecting to 3D Engine...</span>
        </div>
      )}
      
      <div className="w-full h-full min-h-[350px] relative pointer-events-auto">
        <SplineErrorBoundary 
          fallback={<ThreeShaderOrb />}
          onError={handleSplineError}
        >
          <Spline 
            scene="https://prod.spline.design/6Wq1Q7YRyKj1OTDq/scene.splinecode" 
            onLoad={() => setSplineLoading(false)}
            onError={handleSplineError}
          />
        </SplineErrorBoundary>
      </div>
      
      {!splineLoading && (
        <div className="absolute bottom-4 left-1/2 transform -translate-x-1/2 text-center pointer-events-none">
          <p className="text-[10px] font-semibold uppercase tracking-widest text-teal-600/70">
            Interactive 3D Mesh (Spline Active)
          </p>
        </div>
      )}
    </div>
  );
}
