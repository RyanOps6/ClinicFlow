import React from 'react';
import { Link } from 'react-router-dom';
import { TrendingDown, PhoneOff, Users, ChevronDown, Check } from 'lucide-react';
import Tilt3D from './Tilt3D';

const cards = [
  {
    icon: TrendingDown,
    metric: '67%',
    title: 'Missed Patient Reconnects',
    body: '67% of patients who call a clinic and reach voicemail never call back. Missed calls mean missed revenue, delayed care, and frustrated patients.',
    colorClass: 'from-sky-500 to-teal-500',
    iconColor: 'text-sky-500'
  },
  {
    icon: PhoneOff,
    metric: '47',
    title: 'Calls Missed Daily',
    body: 'Front desk operations face an average of 47 unhandled inquiries per single provider workspace daily, driving a massive 68% team burnout rate among reception teams.',
    colorClass: 'from-indigo-500 to-sky-500',
    iconColor: 'text-indigo-500'
  },
  {
    icon: Users,
    metric: '$25K',
    title: 'Revenue Lost / Month',
    body: 'Uncaptured triage workflows and dropped connection requests manifest in massive local clinical leakages that impact overall patient retention.',
    colorClass: 'from-purple-500 to-indigo-500',
    iconColor: 'text-purple-500'
  },
];

const steps = [
  {
    step: '01',
    tag: 'Core Sync',
    title: 'Secure EHR Sync Integration',
    body: 'Seamless native configurations bridge system interactions across 15+ modern medical platforms including Epic, eClinicalWorks, and athenahealth. Achieve a 40% reduction in administrative overhead.',
  },
  {
    step: '02',
    tag: 'Adaptation Engine',
    title: 'Nomenclature Calibration Engine',
    body: 'Real-time NLP voice synthesis processing running at a validated 98.5% accuracy rate, natively tuned for complex medical terminology, ICD-10 coding, and clinical dialects.',
  },
  {
    step: '03',
    tag: 'Autonomy Activation',
    title: '24/7 Voice Dispatch Activation',
    body: 'Deploy secure clinical routing pathways running under a verified sub-30 second latency profile to instantly capture drops and boost patient adherence by 22%.',
  },
];

const team = [
  {
    name: 'Dr. John Henry',
    role: 'Founder & CEO | Interventional Cardiologist',
    bio: 'Founded by practicing medical professionals to address real clinical environments. Our structural layout models are engineered directly from systemic healthcare insights to systematically target user friction points.',
    initials: 'JH',
    badge: 'Clinical Founder',
    badgeColor: 'bg-sky-100 text-sky-800 border-sky-200'
  },
  {
    name: 'Dr. David Miller',
    role: 'CHIEF AI RESEARCHER & COMPLIANCE STRATEGIST',
    bio: 'Our AI is developed by researchers from leading institutions with deep expertise in medical nomenclature processing. System boundaries incorporate comprehensive end-to-end encryption frameworks with verified BAA compliance layers.',
    initials: 'DM',
    badge: 'Scientific Intelligence',
    badgeColor: 'bg-teal-100 text-teal-800 border-teal-200'
  },
];

const security = [
  'SOC 2 Type II Certified',
  '100% HIPAA Encryption Compliant',
  'Automated BAA Instance Generation',
];

export default function Home() {
  // scroll reveal handler
  React.useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add('cf-in');
          }
        });
      },
      { threshold: 0.1, rootMargin: '0px 0px -40px 0px' }
    );
    const elements = document.querySelectorAll('.cf-reveal');
    elements.forEach((el) => observer.observe(el));
    return () => observer.disconnect();
  }, []);

  return (
    <div className="w-full flex flex-col relative font-sans">
      
      {/* SECTION 1: Clean Gradient Hero Section */}
      <section className="relative min-h-[calc(100vh-65px)] w-full overflow-hidden flex flex-col items-center justify-center px-6 bg-gradient-to-b from-sky-100 via-sky-50 to-white">
        
        {/* Subtle grid background pattern */}
        <div className="absolute inset-0 opacity-20 bg-[radial-gradient(#38bdf8_1px,transparent_1px)] [background-size:16px_16px] pointer-events-none" />

        {/* Hero Content Wrapper */}
        <div className="relative z-10 max-w-4xl mx-auto text-center flex flex-col items-center gap-6 py-12">
          
          {/* Pill Badge */}
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-white/80 border border-sky-200 text-[10px] font-bold uppercase tracking-widest text-sky-700 shadow-sm select-none animate-fadeIn">
            <span className="w-1.5 h-1.5 rounded-full bg-sky-500 animate-pulse shadow-[0_0_8px_#38bdf8]" />
            Mindloop Clinical Suite
          </div>

          {/* Central Serif Heading */}
          <h1 className="font-serif text-5xl md:text-7xl text-slate-900 tracking-tight text-center drop-shadow-sm select-none leading-tight font-light serif-title">
            Focus in a <span className="italic text-sky-600">Distracted</span> World
          </h1>

          {/* Serene Description */}
          <p className="text-slate-600 text-sm sm:text-base md:text-lg max-w-xl font-light leading-relaxed serif-title tracking-wider select-none">
            Where empathy meets algorithm. ClinicFlow orchestrates receptionist workflows with serene latency metrics and quiet efficiency.
          </p>

          {/* CTA Navigation Buttons */}
          <div className="mt-8 flex flex-wrap gap-4 justify-center pointer-events-auto">
            <Link
              to="/playground"
              className="px-8 py-3.5 rounded-full text-xs font-bold uppercase tracking-widest text-white bg-gradient-to-r from-sky-500 to-teal-500 hover:from-sky-600 hover:to-teal-600 hover:scale-[1.03] transition-all duration-300 shadow-lg shadow-sky-500/20"
            >
              Start Playground Session
            </Link>
            <Link
              to="/appointments"
              className="px-8 py-3.5 rounded-full text-xs font-bold uppercase tracking-widest text-sky-600 border border-sky-200 bg-white/70 hover:bg-white/90 hover:scale-[1.03] transition-all duration-300 shadow-lg shadow-black/5"
            >
              View Active Ledger
            </Link>
          </div>
        </div>

        {/* Scroll indicator */}
        <div className="absolute bottom-8 left-1/2 z-10 -translate-x-1/2">
          <div className="flex h-11 w-7 items-start justify-center rounded-full border border-sky-200 bg-white/60 p-1.5">
            <ChevronDown className="cf-bounce h-4 w-4 text-sky-500" />
          </div>
        </div>
      </section>

      {/* Content wrapper for operational folds */}
      <div className="w-full h-auto flex flex-col bg-white">

        {/* SECTION 2: THE OPERATIONAL MATRIX (Daylight Grid) */}
        <section 
          className="relative z-20 bg-white text-slate-800 py-28 md:py-36 px-6 md:px-12 border-t border-slate-100"
          style={{ backgroundImage: 'radial-gradient(rgba(56, 189, 248, 0.08) 1px, transparent 0)', backgroundSize: '24px 24px' }}
        >
          <div className="max-w-6xl mx-auto space-y-16">
            
            <div className="cf-reveal text-center space-y-4 max-w-2xl mx-auto">
              <span className="text-[10px] font-mono font-bold text-sky-600 uppercase tracking-[0.3em]">The Problem</span>
              <h2 className="font-serif text-3xl md:text-5xl tracking-tight text-slate-900 font-light leading-tight">
                The Front Desk Crisis in Modern Healthcare
              </h2>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
              {cards.map((card, i) => (
                <Tilt3D key={card.title} maxTilt={6}>
                  <article className="cf-reveal glass-frosted-light rounded-2xl p-8 flex flex-col justify-between min-h-[260px] h-full">
                    <div>
                      <div className="mb-8 flex items-center justify-between">
                        <card.icon className={`h-5 w-5 ${card.iconColor}`} />
                        <span className="h-2 w-2 rounded-full bg-sky-300 transition-all duration-300 group-hover:bg-sky-500" />
                      </div>
                      <div className={`font-sans text-5xl md:text-6xl font-bold tracking-tight bg-gradient-to-r ${card.colorClass} bg-clip-text text-transparent`}>
                        {card.metric}
                      </div>
                      <h3 className="mt-5 text-lg font-bold text-slate-900 font-sans">
                        {card.title}
                      </h3>
                    </div>
                    <div className="mt-4">
                      <p className="text-sm font-normal leading-relaxed text-slate-600 font-sans">
                        {card.body}
                      </p>
                    </div>
                  </article>
                </Tilt3D>
              ))}
            </div>

          </div>
        </section>

        {/* SECTION 3: TIMELINE INTEGRATION PATHWAYS (Vibrant Threading) */}
        <section className="relative z-20 bg-slate-50/50 text-slate-800 py-28 md:py-36 px-6 md:px-12 border-t border-slate-100">
          <div className="max-w-4xl mx-auto space-y-20 relative">
            
            <div className="cf-reveal text-center space-y-4">
              <span className="text-[10px] font-mono font-bold text-sky-600 uppercase tracking-[0.3em]">The Integration Path</span>
              <h2 className="font-serif text-3xl md:text-5xl tracking-tight text-slate-900 font-light">
                From First Call to Full Autonomy
              </h2>
            </div>

            {/* Timeline Container */}
            <div className="relative pt-4">
              
              {/* Absolute connecting neon layout wire */}
              <div className="absolute left-[19px] md:left-[23px] top-2 bottom-2 w-[3px] bg-gradient-to-b from-teal-400 via-sky-400 to-transparent shadow-[0_0_8px_rgba(20,184,166,0.5)] pointer-events-none" />

              <ol className="space-y-12">
                {steps.map((s, i) => (
                  <li key={s.step} className="cf-reveal relative pl-16 md:pl-20">
                    {/* Neon node checkpoint that blooms as it enters viewport */}
                    <span className="absolute left-0 top-1.5 flex h-10 w-10 items-center justify-center rounded-full border border-sky-200 bg-white shadow-md md:h-12 md:w-12 z-10 transition-all duration-700 [.cf-in_&]:border-sky-400 [.cf-in_&]:shadow-[0_0_15px_rgba(56,189,248,0.7)]">
                      <span className="h-3 w-3 rounded-full bg-teal-400 neon-pulse-teal" />
                    </span>

                    <div className="glass-frosted-light rounded-2xl p-7">
                      <div className="flex items-center gap-3">
                        <span className="font-mono text-xs font-bold text-sky-600">
                          Step {s.step}
                        </span>
                        <span className="text-[10px] font-bold uppercase tracking-[0.2em] text-slate-400">
                          {s.tag}
                        </span>
                      </div>
                      <h3 className="mt-3 font-serif text-2xl font-light text-slate-900 md:text-3xl">
                        {s.title}
                      </h3>
                      <p className="mt-3 text-sm font-normal leading-relaxed text-slate-600 font-sans">
                        {s.body}
                      </p>
                    </div>
                  </li>
                ))}
              </ol>
            </div>

          </div>
        </section>

        {/* SECTION 4: LEADERSHIP BIOGRAPHIES (Premium Corporate Look) */}
        <section className="relative z-20 bg-white text-slate-800 py-28 md:py-36 px-6 md:px-12 border-t border-slate-100">
          <div className="max-w-5xl mx-auto space-y-16">
            
            <div className="cf-reveal text-center space-y-4 max-w-2xl mx-auto">
              <h2 className="font-serif text-3xl md:text-5xl tracking-tight text-slate-900 font-light text-center leading-tight">
                Built by Clinicians. Powered by Research.
              </h2>
              <p className="mx-auto mt-6 max-w-2xl text-pretty font-serif text-lg md:text-xl font-light italic leading-relaxed text-sky-700/80">
                &ldquo;AI should not replace the doctor, front desk, or MA; it should replace the paperwork.&rdquo;
              </p>
            </div>

            <div className="grid grid-cols-1 gap-8 md:grid-cols-2">
              {team.map((member, i) => (
                <article key={member.name} className="cf-reveal glass-frosted-light rounded-2xl p-8 flex flex-col justify-between h-full shadow-lg border border-slate-100">
                  <div className="space-y-6">
                    <div className="flex items-center gap-4">
                      <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-full border border-sky-100 bg-sky-50 font-serif text-lg font-light text-sky-600 shadow-inner">
                        {member.initials}
                      </div>
                      <div>
                        <h3 className="text-lg font-bold text-slate-900 font-sans">
                          {member.name}
                        </h3>
                        <p className="mt-0.5 text-xs font-bold uppercase tracking-wider text-sky-600/85 font-sans">
                          {member.role}
                        </p>
                      </div>
                    </div>
                    <p className="text-sm font-normal leading-relaxed text-slate-600 font-sans">
                      {member.bio}
                    </p>
                  </div>
                  <div className="pt-6 border-t border-slate-100 mt-8 flex justify-between items-center">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold border ${member.badgeColor}`}>
                      {member.badge}
                    </span>
                    <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider font-mono">Active Advisor</span>
                  </div>
                </article>
              ))}
            </div>

          </div>
        </section>

      </div>

      {/* SECTION 5: SYSTEM CLEANUP & NAVIGATION FOOTER */}
      <footer className="relative z-20 bg-slate-50 text-slate-500 py-16 px-6 md:px-12 border-t border-slate-200 font-sans">
        <div className="mx-auto grid max-w-6xl grid-cols-1 gap-12 md:grid-cols-4">
          
          {/* Column 1 — Brand */}
          <div className="space-y-4">
            <div className="flex items-center gap-2.5">
              <span className="h-2.5 w-2.5 rounded-full bg-sky-500 shadow-[0_0_10px_rgba(56,189,248,0.9)]" />
              <span className="font-serif text-lg font-light tracking-tight text-slate-900">
                ClinicFlow Executive
              </span>
            </div>
            <p className="text-xs text-slate-500 leading-relaxed font-normal">
              Industrializing patient workflows via predictive automation interfaces. Engineered for institutional reliability.
            </p>
            <p className="text-xs text-slate-400 font-serif italic">
              "Where empathy meets algorithm."
            </p>
          </div>

          {/* Column 2 — Navigation Map */}
          <div>
            <h4 className="font-mono text-xs uppercase tracking-[0.25em] text-slate-800 font-bold">
              Navigation Map
            </h4>
            <ul className="mt-5 space-y-3">
              {navLinks.map((link) => (
                <li key={link.href}>
                  <Link
                    to={link.href}
                    className="inline-flex items-center gap-2 text-sm font-normal text-slate-500 transition-colors hover:text-sky-600"
                  >
                    <span className="font-mono text-xs text-sky-500/70">
                      {link.href}
                    </span>
                    <span>{link.label}</span>
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          {/* Column 3 — Security Matrix */}
          <div>
            <h4 className="font-mono text-xs uppercase tracking-[0.25em] text-slate-800 font-bold">
              Security Matrix
            </h4>
            <ul className="mt-5 space-y-3">
              {security.map((item) => (
                <li key={item} className="flex items-start gap-2 text-xs font-normal text-slate-500">
                  <Check className="mt-0.5 h-4 w-4 shrink-0 text-teal-500" />
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </div>

          {/* Column 4 — Contact Operations */}
          <div className="space-y-4">
            <h4 className="font-mono text-xs uppercase tracking-[0.25em] text-slate-800 font-bold">
              Contact Operations
            </h4>
            <p className="text-xs text-slate-500 font-normal">
              &copy; 2026 ClinicFlow System Inc.
            </p>
            <a
              href="mailto:contact@clinicflow.ai"
              className="inline-block text-sm font-semibold text-sky-600 transition-colors hover:text-sky-700 underline"
            >
              contact@clinicflow.ai
            </a>
          </div>

        </div>
        
        {/* Bottom Credits */}
        <div className="max-w-6xl mx-auto mt-12 pt-8 border-t border-slate-200 flex flex-col sm:flex-row items-center justify-between text-[11px] text-slate-400 gap-4 sm:gap-0">
          <span>© 2026 ClinicFlow Executive, Inc. All rights reserved. Inspired by iMedClinic.ai.</span>
          <div className="flex gap-4">
            <a href="#privacy" className="hover:text-slate-600 transition-colors">Privacy Policy</a>
            <a href="#terms" className="hover:text-slate-600 transition-colors">Terms of Service</a>
          </div>
        </div>
      </footer>

    </div>
  );
}

const navLinks = [
  { label: 'Playground', href: '/playground' },
  { label: 'Sessions', href: '/sessions' },
  { label: 'Appointments', href: '/appointments' },
];
