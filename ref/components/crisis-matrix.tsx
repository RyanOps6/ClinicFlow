import { PhoneOff, TrendingDown, Users } from 'lucide-react'
import { Reveal } from './reveal'

const cards = [
  {
    icon: TrendingDown,
    metric: '67%',
    title: 'Missed Patient Reconnects',
    body: '67% of patients who call a clinic and reach voicemail never call back. Missed calls mean missed revenue, delayed care, and frustrated patients.',
  },
  {
    icon: PhoneOff,
    metric: '47',
    title: 'Calls Missed Daily',
    body: 'Front desk operations face an average of 47 unhandled inquiries per single provider workspace daily, driving a massive 68% team burnout rate among reception teams.',
  },
  {
    icon: Users,
    metric: '$25K',
    title: 'Revenue Lost / Month',
    body: 'Uncaptured triage workflows and dropped connection requests manifest in massive local clinical leakages that impact overall patient retention.',
  },
]

export function CrisisMatrix() {
  return (
    <section className="relative w-full bg-background px-6 py-28 md:py-36">
      <div className="mx-auto max-w-6xl">
        <Reveal className="mb-16 max-w-2xl">
          <p className="mb-4 font-mono text-xs uppercase tracking-[0.3em] text-primary/80">
            The Problem
          </p>
          <h2 className="text-balance font-serif text-4xl font-light leading-tight tracking-tight text-foreground md:text-5xl">
            The Front Desk Crisis in Modern Healthcare
          </h2>
        </Reveal>

        <div className="grid grid-cols-1 gap-5 md:grid-cols-3">
          {cards.map((card, i) => (
            <Reveal key={card.title} delay={i * 120}>
              <article className="group h-full rounded-2xl border border-white/[0.04] bg-card/60 p-8 backdrop-blur-xl transition-all duration-500 hover:border-primary/20 hover:bg-card/90">
                <div className="mb-8 flex items-center justify-between">
                  <card.icon
                    className="h-5 w-5 text-muted-foreground transition-colors duration-500 group-hover:text-primary"
                    aria-hidden="true"
                  />
                  <span className="h-2 w-2 rounded-full bg-primary/30 transition-all duration-500 group-hover:bg-primary group-hover:shadow-[0_0_12px_rgba(34,211,238,0.8)]" />
                </div>
                <div className="font-serif text-6xl font-light tracking-tight text-foreground md:text-7xl">
                  {card.metric}
                </div>
                <h3 className="mt-5 text-lg font-medium text-foreground">
                  {card.title}
                </h3>
                <p className="mt-3 text-sm font-light leading-relaxed text-muted-foreground">
                  {card.body}
                </p>
              </article>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  )
}
