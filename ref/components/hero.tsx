'use client'

import { ChevronDown } from 'lucide-react'
import { ParticleField } from './particle-field'

export function Hero() {
  return (
    <section className="relative h-screen min-h-[680px] w-full overflow-hidden">
      {/* Background video layer (z-0) */}
      <video
        className="pointer-events-none absolute left-0 top-0 z-0 h-full w-full object-cover"
        autoPlay
        muted
        loop
        playsInline
        poster="/hero-poster.png"
        aria-hidden="true"
      >
        <source src="/bg-039.mp4" type="video/mp4" />
      </video>

      {/* Tone overlay (z-10) */}
      <div className="absolute inset-0 z-10 bg-gradient-to-b from-black/20 via-[#07090e]/40 to-[#07090e]" />

      {/* Interactive WebGL particle field (z-15) */}
      <ParticleField />

      {/* Content (z-20) */}
      <div className="relative z-20 flex h-full flex-col items-center justify-center px-6 text-center">
        {/* Pill badge */}
        <div className="mb-8 inline-flex items-center gap-2 rounded-full border border-white/[0.08] bg-white/[0.03] px-5 py-2 backdrop-blur-xl">
          <span className="h-1.5 w-1.5 rounded-full bg-primary shadow-[0_0_12px_rgba(34,211,238,0.9)]" />
          <span className="text-xs font-light uppercase tracking-[0.32em] text-foreground/80">
            Mindloop Clinical Suite
          </span>
        </div>

        {/* Headline */}
        <h1 className="max-w-4xl text-balance font-serif text-5xl font-light leading-[1.05] tracking-tight text-foreground sm:text-6xl md:text-7xl lg:text-8xl">
          Focus in a{' '}
          <span className="italic text-primary">Distracted</span> World
        </h1>

        {/* Subtext */}
        <p className="mt-7 max-w-xl text-pretty text-base font-light leading-relaxed text-muted-foreground md:text-lg">
          Where empathy meets algorithm. ClinicFlow orchestrates receptionist
          workflows with serene latency metrics and quiet efficiency.
        </p>

        {/* CTA buttons */}
        <div className="mt-10 flex flex-col items-center gap-4 sm:flex-row">
          <a
            href="/playground"
            className="group inline-flex items-center justify-center rounded-full border border-primary/40 bg-primary/15 px-7 py-3.5 text-sm font-medium text-primary backdrop-blur-xl transition-all duration-300 hover:bg-primary/25 hover:shadow-[0_0_30px_rgba(34,211,238,0.35)]"
          >
            Start Playground Session
          </a>
          <a
            href="/sessions"
            className="inline-flex items-center justify-center rounded-full border border-white/[0.08] bg-white/[0.03] px-7 py-3.5 text-sm font-light text-foreground/90 backdrop-blur-xl transition-all duration-300 hover:border-white/20 hover:bg-white/[0.07]"
          >
            View Active Ledger
          </a>
        </div>
      </div>

      {/* Scroll indicator */}
      <div className="absolute bottom-8 left-1/2 z-20 -translate-x-1/2">
        <div className="flex h-11 w-7 items-start justify-center rounded-full border border-white/15 bg-white/[0.03] p-1.5 backdrop-blur-xl">
          <ChevronDown className="cf-bounce h-4 w-4 text-primary" />
        </div>
      </div>
    </section>
  )
}
