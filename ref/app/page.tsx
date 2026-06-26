import { Hero } from '@/components/hero'
import { CrisisMatrix } from '@/components/crisis-matrix'
import { IntegrationTimeline } from '@/components/integration-timeline'
import { LeadershipLedger } from '@/components/leadership-ledger'
import { SiteFooter } from '@/components/site-footer'

export default function Page() {
  return (
    <main className="relative w-full overflow-x-hidden bg-background">
      <Hero />
      <CrisisMatrix />
      <IntegrationTimeline />
      <LeadershipLedger />
      <SiteFooter />
    </main>
  )
}
