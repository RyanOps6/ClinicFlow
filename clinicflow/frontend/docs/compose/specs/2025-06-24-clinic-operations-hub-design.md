# Clinic Operations Hub Dashboard - Design Spec

## [S1] Overview
Transform the existing ClinicFlow frontend into a premium, modern Clinic Operations Hub web dashboard for hospital staff and administrators. This is a UI-only overhaul — all backend APIs already exist and will be consumed as-is.

## [S2] Design System
- **Theme:** Clean, modern, professional healthcare layout (Premium Light Mode)
- **Palette:**
  - Borders: `border-slate-200`
  - Headers: `text-slate-900` (deep navy)
  - Primary accent: Medical teal/cyan (`text-teal-600`, `bg-teal-50`)
  - Status colors: Teal (booking), Amber (reschedule), Coral (cancel), Gray (unknown)
- **Typography:** Sans-serif, generous whitespace, elegant grid cards
- **Framework:** React + TypeScript + Tailwind CSS + Lucide React icons

## [S3] Global Navigation Bar
- Horizontal top bar
- Left: "ClinicFlow Dashboard" branding with medical icon
- Center: Live backend API status badge ("Operational" / "Degraded") — polls `/health`
- Right: User profile icon with staff avatar placeholder

## [S4] Tabbed Layout
Three main tabs controlled by React state (not route-based):
1. **Live Conversation** (default)
2. **Call Sessions Log**
3. **Appointments Ledger**

## [S5] Tab 1: Live Conversation & Test Workspace
Split-pane layout:
- **Left (40%):** "Staff Test Playground" — chat interface with message bubbles, text input, "Send" and "Clear/Reset" buttons
- **Right (60%):** "Live Session Monitor" — card grid updating in real-time:
  - Intent Status Badge (color-coded: Teal=Booking, Amber=Reschedule, Coral=Cancel, Gray=Unknown)
  - Patient Profile Matrix (table with Full Name, Phone, Reason — "Awaiting input..." if empty)

## [S6] Tab 2: Call Sessions Log
- Top metric row: Total Sessions Today, Active Calls, Automation Completion Rate
- Data table: Session ID, Patient Name, Interaction Type (Intent), Channel, Session Status, "View Details" button

## [S7] Tab 3: Appointments Ledger
- Clean list/card view of appointments
- Columns/fields: Date, Time, Doctor, Patient Name, Status (upcoming vs canceled)
- Status badges with appropriate colors

## [S8] Technical Approach
- Install Tailwind CSS, Lucide React, clsx, tailwind-merge
- Replace all existing custom CSS with Tailwind utility classes
- Single `App.tsx` with tab state; keep existing pages as tab content components
- Use existing `api/client.ts` and `types/index.ts` without changes
- Preserve all existing API routes and functionality
