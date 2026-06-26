import { Analytics } from '@vercel/analytics/next'
import type { Metadata, Viewport } from 'next'
import { Geist, Geist_Mono, Cormorant_Garamond } from 'next/font/google'
import './globals.css'

const geistSans = Geist({ variable: '--font-geist-sans', subsets: ['latin'] })
const geistMono = Geist_Mono({
  variable: '--font-geist-mono',
  subsets: ['latin'],
})
const cormorant = Cormorant_Garamond({
  variable: '--font-cormorant',
  subsets: ['latin'],
  weight: ['300', '400', '500', '600', '700'],
  style: ['normal', 'italic'],
})

export const metadata: Metadata = {
  title: 'ClinicFlow Executive — Healthcare Voice AI for the Front Desk',
  description:
    'ClinicFlow Executive orchestrates receptionist workflows with serene latency metrics and quiet efficiency. Built by clinicians, powered by research. Voice AI that replaces the paperwork, not the people.',
  generator: 'v0.app',
  keywords: [
    'healthcare voice AI',
    'clinic front desk automation',
    'medical receptionist AI',
    'EHR integration',
    'HIPAA compliant AI',
    'patient triage',
  ],
}

export const viewport: Viewport = {
  colorScheme: 'dark',
  themeColor: '#07090e',
  width: 'device-width',
  initialScale: 1,
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} ${cormorant.variable} bg-background`}
    >
      <body className="font-sans antialiased">
        {children}
        {process.env.NODE_ENV === 'production' && <Analytics />}
      </body>
    </html>
  )
}
