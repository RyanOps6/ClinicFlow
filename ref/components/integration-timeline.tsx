import { Reveal } from './reveal'

const steps = [
  {
    step: '01',
    tag: 'Core Authorization',
    title: 'Secure EHR Sync Integration',
    body: 'Seamless native configurations bridge system interactions across 15+ modern medical platforms including Epic, eClinicalWorks, and athenahealth. Achieve a 40% reduction in administrative overhead.',
  },
  {
    step: '02',
    tag: 'Machine Adaptation',
    title: 'Nomenclature Calibration Engine',
    body: 'Real-time NLP voice synthesis processing running at a validated 98.5% accuracy rate, natively tuned for complex medical terminology, ICD-10 coding, and clinical dialects.',
  },
  {
    step: '03',
    tag: 'Complete Autonomy',
    title: '24/7 Voice Dispatch Activation',
    body: 'Deploy secure clinical routing pathways running under a verified sub-30 second latency profile to instantly capture drops and boost patient adherence by 22%.',
  },
]

export function IntegrationTimeline() {
  return (
    <section className="relative w-full bg-background px-6 py-28 md:py-36">
      <div className="mx-auto max-w-4xl">
        <Reveal className="mb-20 text-center">
          <p className="mb-4 font-mono text-xs uppercase tracking-[0.3em] text-primary/80">
            The Integration Path
          </p>
          <h2 className="text-balance font-serif text-4xl font-light leading-tight tracking-tight text-foreground md:text-5xl">
            From First Call to Full Autonomy
          </h2>
        </Reveal>

        <div className="relative">
          {/* Vertical guide line */}
          <div
            className="absolute left-[19px] top-2 bottom-2 w-px bg-gradient-to-b from-primary/40 via-white/[0.08] to-transparent md:left-[23px]"
            aria-hidden="true"
          />

          <ol className="space-y-14">
            {steps.map((s, i) => (
              <Reveal as="li" key={s.step} delay={i * 100} className="relative pl-16 md:pl-20">
                {/* Neon node checkpoint */}
                <span
                  className="cf-pulse absolute left-0 top-1 flex h-10 w-10 items-center justify-center rounded-full border border-primary/40 bg-card md:h-12 md:w-12"
                  aria-hidden="true"
                >
                  <span className="h-2.5 w-2.5 rounded-full bg-primary shadow-[0_0_14px_rgba(34,211,238,0.9)]" />
                </span>

                <div className="rounded-2xl border border-white/[0.04] bg-card/50 p-7 backdrop-blur-xl transition-colors duration-500 hover:border-primary/20">
                  <div className="flex items-center gap-3">
                    <span className="font-mono text-xs text-primary">
                      Step {s.step}
                    </span>
                    <span className="text-xs font-light uppercase tracking-[0.2em] text-muted-foreground">
                      {s.tag}
                    </span>
                  </div>
                  <h3 className="mt-3 font-serif text-2xl font-light text-foreground md:text-3xl">
                    {s.title}
                  </h3>
                  <p className="mt-3 text-sm font-light leading-relaxed text-muted-foreground">
                    {s.body}
                  </p>
                </div>
              </Reveal>
            ))}
          </ol>
        </div>
      </div>
    </section>
  )
}
