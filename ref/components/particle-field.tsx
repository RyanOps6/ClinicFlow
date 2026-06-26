'use client'

import { useEffect, useRef } from 'react'
import * as THREE from 'three'

/**
 * A transparent, full-width WebGL field of ~450 fine ambient light-dust
 * particles. Particles drift slowly and warp toward real-time mouse
 * coordinates for a quiet, premium parallax feel.
 */
export function ParticleField() {
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const container = containerRef.current
    if (!container) return

    // Respect reduced motion preferences.
    const prefersReduced = window.matchMedia(
      '(prefers-reduced-motion: reduce)',
    ).matches

    const scene = new THREE.Scene()
    const camera = new THREE.PerspectiveCamera(
      70,
      container.clientWidth / container.clientHeight,
      0.1,
      1000,
    )
    camera.position.z = 60

    const renderer = new THREE.WebGLRenderer({
      alpha: true,
      antialias: true,
    })
    renderer.setSize(container.clientWidth, container.clientHeight)
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    renderer.setClearColor(0x000000, 0)
    container.appendChild(renderer.domElement)

    // Generate ~450 particles within a wide volume.
    const COUNT = 460
    const positions = new Float32Array(COUNT * 3)
    const basePositions = new Float32Array(COUNT * 3)
    const speeds = new Float32Array(COUNT)

    for (let i = 0; i < COUNT; i++) {
      const x = (Math.random() - 0.5) * 160
      const y = (Math.random() - 0.5) * 100
      const z = (Math.random() - 0.5) * 60
      positions[i * 3] = x
      positions[i * 3 + 1] = y
      positions[i * 3 + 2] = z
      basePositions[i * 3] = x
      basePositions[i * 3 + 1] = y
      basePositions[i * 3 + 2] = z
      speeds[i] = 0.2 + Math.random() * 0.6
    }

    const geometry = new THREE.BufferGeometry()
    geometry.setAttribute(
      'position',
      new THREE.BufferAttribute(positions, 3),
    )

    // Soft round sprite texture so particles read as light dust, not squares.
    const sprite = makeDustTexture()
    const material = new THREE.PointsMaterial({
      size: 1.5,
      map: sprite,
      transparent: true,
      opacity: 0.7,
      depthWrite: false,
      blending: THREE.AdditiveBlending,
      color: new THREE.Color(0x9fdfff),
    })

    const points = new THREE.Points(geometry, material)
    scene.add(points)

    // Mouse tracking in normalized device coords.
    const mouse = new THREE.Vector2(0, 0)
    const target = new THREE.Vector2(0, 0)

    const onPointerMove = (e: PointerEvent) => {
      target.x = (e.clientX / window.innerWidth) * 2 - 1
      target.y = -((e.clientY / window.innerHeight) * 2 - 1)
    }
    window.addEventListener('pointermove', onPointerMove)

    const clock = new THREE.Clock()
    let frameId = 0

    const animate = () => {
      frameId = requestAnimationFrame(animate)
      const t = clock.getElapsedTime()

      // Ease mouse toward target.
      mouse.x += (target.x - mouse.x) * 0.04
      mouse.y += (target.y - mouse.y) * 0.04

      const pos = geometry.attributes.position.array as Float32Array
      for (let i = 0; i < COUNT; i++) {
        const ix = i * 3
        const bx = basePositions[ix]
        const by = basePositions[ix + 1]
        const bz = basePositions[ix + 2]
        const s = speeds[i]

        // Slow ambient drift.
        const drift = prefersReduced ? 0 : Math.sin(t * s + i) * 1.6
        // Mouse warp — pull the field gently toward the cursor.
        const warpX = mouse.x * (12 + bz * 0.18)
        const warpY = mouse.y * (12 + bz * 0.18)

        pos[ix] = bx + warpX + drift
        pos[ix + 1] = by + warpY + Math.cos(t * s + i) * 1.4
        pos[ix + 2] = bz
      }
      geometry.attributes.position.needsUpdate = true

      // Subtle full-field rotation for depth.
      points.rotation.z = Math.sin(t * 0.05) * 0.06

      renderer.render(scene, camera)
    }
    animate()

    const onResize = () => {
      if (!container) return
      camera.aspect = container.clientWidth / container.clientHeight
      camera.updateProjectionMatrix()
      renderer.setSize(container.clientWidth, container.clientHeight)
    }
    window.addEventListener('resize', onResize)

    return () => {
      cancelAnimationFrame(frameId)
      window.removeEventListener('pointermove', onPointerMove)
      window.removeEventListener('resize', onResize)
      geometry.dispose()
      material.dispose()
      sprite.dispose()
      renderer.dispose()
      if (renderer.domElement.parentNode === container) {
        container.removeChild(renderer.domElement)
      }
    }
  }, [])

  return (
    <div
      ref={containerRef}
      aria-hidden="true"
      className="pointer-events-none absolute inset-0 z-[15] h-full w-full"
    />
  )
}

/** Builds a soft radial-gradient texture for round, glowing dust motes. */
function makeDustTexture() {
  const size = 64
  const canvas = document.createElement('canvas')
  canvas.width = size
  canvas.height = size
  const ctx = canvas.getContext('2d')!
  const gradient = ctx.createRadialGradient(
    size / 2,
    size / 2,
    0,
    size / 2,
    size / 2,
    size / 2,
  )
  gradient.addColorStop(0, 'rgba(255,255,255,0.95)')
  gradient.addColorStop(0.4, 'rgba(160,220,255,0.5)')
  gradient.addColorStop(1, 'rgba(160,220,255,0)')
  ctx.fillStyle = gradient
  ctx.fillRect(0, 0, size, size)
  const texture = new THREE.CanvasTexture(canvas)
  texture.needsUpdate = true
  return texture
}
