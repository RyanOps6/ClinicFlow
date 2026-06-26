import { Reveal } from './reveal'

const team = [
  {
    name: 'Dr. Vijaiganesh Nagarajan',
    role: 'Founder & CEO | Interventional Cardiologist',
    bio: 'Founded by practicing medical professionals to address real clinical environments. Our structural layout models are engineered directly from systemic healthcare insights to systematically target user friction points.',
    initials: 'VN',
  },
  {
    name: 'Clinical Architecture Group',
    role: 'NLP Researchers & Compliance Strategists',
    bio: 'Our AI is developed by researchers from leading institutions with deep expertise in medical nomenclature processing. System boundaries incorporate comprehensive end-to-end encryption frameworks with verified BAA compliance layers.',
    initials: 'CA',
  },
]

export function LeadershipLedger() {
  return (
    <section className="relative w-full bg-background px-6 py-28 md:py-36">
      <div className="mx-auto max-w-5xl">
        <Reveal className="mb-16 text-center">
          <h2 className="text-balance font-serif text-4xl font-light leading-tight tracking-tight text-foreground md:text-5xl">
            Built by Clinicians. Powered by Research.
          </h2>
          <p className="mx-auto mt-6 max-w-2xl text-pretty font-serif text-xl font-light italic leading-relaxed text-muted-foreground md:text-2xl">
            &ldquo;AI should not replace the doctor, front desk, or MA; it
            should replace the paperwork.&rdquo;
          </p>
        </Reveal>

        <div className="grid grid-cols-1 gap-5 md:grid-cols-2">
          {team.map((member, i) => (
            <Reveal key={member.name} delay={i * 120}>
              <article className="h-full rounded-2xl border border-white/[0.04] bg-card/60 p-8 backdrop-blur-xl transition-colors duration-500 hover:border-accent/30">
                <div className="flex items-center gap-4">
                  <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-full border border-white/[0.08] bg-secondary font-serif text-lg font-light text-primary">
                    {member.initials}
                  </div>
                  <div>
                    <h3 className="text-lg font-medium text-foreground">
                      {member.name}
                    </h3>
                    <p className="mt-0.5 text-xs font-light uppercase tracking-wider text-primary/80">
                      {member.role}
                    </p>
                  </div>
                </div>
                <p className="mt-6 text-sm font-light leading-relaxed text-muted-foreground">
                  {member.bio}
                </p>
              </article>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  )
}
