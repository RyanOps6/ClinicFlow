import { Check } from 'lucide-react'

const navLinks = [
  { label: 'Playground', href: '/playground' },
  { label: 'Sessions', href: '/sessions' },
  { label: 'Appointments', href: '/appointments' },
]

const security = [
  'SOC 2 Type II Certified',
  '100% HIPAA Encryption Compliant',
  'Automated BAA Instance Generation',
]

export function SiteFooter() {
  return (
    <footer className="w-full border-t border-white/[0.04] bg-black px-6 py-16">
      <div className="mx-auto grid max-w-6xl grid-cols-1 gap-12 md:grid-cols-4">
        {/* Column 1 — Brand */}
        <div>
          <div className="flex items-center gap-2">
            <span className="h-2 w-2 rounded-full bg-primary shadow-[0_0_10px_rgba(34,211,238,0.9)]" />
            <span className="font-serif text-lg font-light tracking-tight text-foreground">
              ClinicFlow Executive
            </span>
          </div>
          <p className="mt-4 max-w-xs text-sm font-light leading-relaxed text-muted-foreground">
            Industrializing patient workflows via predictive automation
            interfaces. Engineered for institutional reliability.
          </p>
        </div>

        {/* Column 2 — Navigation map */}
        <div>
          <h4 className="font-mono text-xs uppercase tracking-[0.25em] text-foreground/60">
            Navigation Map
          </h4>
          <ul className="mt-5 space-y-3">
            {navLinks.map((link) => (
              <li key={link.href}>
                <a
                  href={link.href}
                  className="inline-flex items-center gap-2 text-sm font-light text-muted-foreground transition-colors hover:text-primary"
                >
                  <span className="font-mono text-xs text-primary/60">
                    {link.href}
                  </span>
                </a>
              </li>
            ))}
          </ul>
        </div>

        {/* Column 3 — Security matrix */}
        <div>
          <h4 className="font-mono text-xs uppercase tracking-[0.25em] text-foreground/60">
            Security Matrix
          </h4>
          <ul className="mt-5 space-y-3">
            {security.map((item) => (
              <li
                key={item}
                className="flex items-start gap-2 text-sm font-light text-muted-foreground"
              >
                <Check
                  className="mt-0.5 h-4 w-4 shrink-0 text-primary"
                  aria-hidden="true"
                />
                <span>{item}</span>
              </li>
            ))}
          </ul>
        </div>

        {/* Column 4 — Contact operations */}
        <div>
          <h4 className="font-mono text-xs uppercase tracking-[0.25em] text-foreground/60">
            Contact Operations
          </h4>
          <p className="mt-5 text-sm font-light text-muted-foreground">
            &copy; 2026 ClinicFlow System Inc.
          </p>
          <a
            href="mailto:Info@imedclinic.ai"
            className="mt-3 inline-block text-sm font-light text-primary transition-colors hover:text-primary/80"
          >
            Info@imedclinic.ai
          </a>
        </div>
      </div>
    </footer>
  )
}
