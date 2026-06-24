# Clinic Operations Hub Dashboard - Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use compose:subagent (recommended) or compose:execute to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform the existing ClinicFlow frontend into a premium, modern Clinic Operations Hub web dashboard using React, Tailwind CSS, and Lucide React icons.

**Architecture:** Keep the existing component structure but replace all CSS with Tailwind utility classes. Add a tabbed navigation system in `App.tsx` to switch between the three main views. Backend API consumption remains unchanged.

**Tech Stack:** React 18, TypeScript, Vite, Tailwind CSS v4, Lucide React, clsx, tailwind-merge

## Global Constraints
- Preserve all existing API calls in `api/client.ts`
- Preserve all existing types in `types/index.ts`
- Use Lucide React icons exclusively (no custom SVGs)
- Maintain the same backend API contract
- Keep the existing route structure for deep-linking to sessions

---

### Task 1: Install Tailwind CSS and Dependencies

**Files:**
- Modify: `frontend/package.json`
- Modify: `frontend/vite.config.ts`
- Create: `frontend/src/index.css` (replacing existing)
- Create: `frontend/postcss.config.js`

**Interfaces:**
- Produces: Tailwind CSS configured and ready; existing CSS classes replaced with utility-first approach

- [ ] **Step 1: Install packages**

```bash
cd D:\iclinic\clinicflow\frontend && npm install -D tailwindcss@^3.4.0 postcss autoprefixer clsx tailwind-merge && npm install lucide-react
```

- [ ] **Step 2: Initialize Tailwind**

```bash
cd D:\iclinic\clinicflow\frontend && npx tailwindcss init -p
```

- [ ] **Step 3: Configure tailwind.config.js**

Create `tailwind.config.js` with content paths and theme extensions for the medical palette.

- [ ] **Step 4: Update index.css**

Replace with `@tailwind` directives and custom就去 base styles only.

- [ ] **Step 5: Update vite.config.ts**

Ensure build works with the new CSS setup.

---

### Task 2: Build Global Navigation Bar Component

**Files:**
- Create: `frontend/src/components/GlobalNav.tsx`

**Interfaces:**
- Consumes: Health API from a new `api/health.ts` or inline fetch
- Produces: `GlobalNav` component with status badge and profile

- [ ] **Step 1: Create GlobalNav.tsx**

Build a horizontal nav with:
- Left: Activity icon + "ClinicFlow Dashboard"
- Center: Poll `/health` endpoint every 30s, show "Backend API: Operational" badge
- Right: User avatar circle with "Staff" label

- [ ] **Step 2: Verify nav renders correctly**

Run `npm run build` and check for errors (if backend is not running, mock the status).

---

### Task 3: Build Tab Bar and App Shell

**Files:**
- Modify: `frontend/src/App.tsx`

**Interfaces:**
- Consumes: Three main view components
- Produces: Tab state and switcher

- [ ] **Step 1: Add tab state to App.tsx**

Replace `BrowserRouter`-based layout with a tab state machine:
- `activeTab: 'conversation' | 'sessions' | 'appointments'`
- Keep `BrowserRouter` for deep-linking to session details, but main nav is tab-based

- [ ] **Step 2: Build TabBar component inline or in separate file**

Three tabs with icons: Chat, History/Log, Calendar. Show active state with teal underline.

---

### Task 4: Build Tab 1 - Live Conversation & Test Workspace

**Files:**
- Create: `frontend/src/components/ChatInterface.tsx` (new chat UI)
- Create: `frontend/src/components/LiveSessionMonitor.tsx` (session monitor card)
- Modify: `frontend/src/pages/SessionPage.tsx` (rework or create new page component)

**Interfaces:**
- Consumes: `startSession`, `sendMessage`, `getSession` from `api/client.ts`
- Produces: Split-pane layout as specified

- [ ] **Step 1: Create ChatInterface component**

Premium chat UI with:
- Message bubbles (Patient on left, AI on right)
- Modern input bar at bottom
- "Send" button (teal primary)
- "Clear / Reset Session" button
- Session type selector (Booking, Reschedule, Cancel)

- [ ] **Step 2: Create LiveSessionMonitor component**

Card grid with:
- Intent Status Badge (dynamic color)
- Patient Profile Matrix (table with name, phone, reason placeholders)

- [ ] **Step 3: Wire SessionPage tab view**

Combine both in a 40/60 split layout.

---

### Task 5: Build Tab 2 - Call Sessions Log

**Files:**
- Create: `frontend/src/components/SessionsLog.tsx`

**Interfaces:**
- Consumes: `getDashboardOverview` from `api/client.ts`
- Produces: Metric row + data table

- [ ] **Step 1: Create metric row**

Three stat cards: Total Sessions Today, Active Calls, Automation Completion Rate.

- [ ] **Step 2: Create data table**

Columns: Session ID, Patient Name, Interaction Type, Channel, Status, View Details button.
Reuse existing `DashboardSession` data from the overview API.

---

### Task 6: Build Tab 3 - Appointments Ledger

**Files:**
- Create: `frontend/src/components/AppointmentsLedger.tsx`

**Interfaces:**
- Consumes: `getAppointments` from `api/client.ts`
- Produces: Clean list/card view

- [ ] **Step 1: Create appointments list**

Cards showing: Date, Time, Doctor, Patient Name, Status badge.
Group by upcoming vs canceled.

---

### Task 7: Cleanup and Remove Old CSS

**Files:**
- Delete: `frontend/src/index.css` old contents (replaced in Task 1)
- Review: All component files for any remaining custom CSS class references and replace with Tailwind

- [ ] **Step 1: Verify no broken class names**

Run `npm run build` and fix any errors.

---

### Task 8: Verification and Polish

- [ ] **Step 1: Run build**

```bash
cd D:\iclinic\clinicflow\frontend && npm run build
```

- [ ] **Step 2: Visually check all three tabs**

Switch between tabs, verify chat works, verify sessions log fetches, verify appointments display.

- [ ] **Step 3: Check responsive behavior**

Ensure layout works on desktop (primary target) and does not break on smaller screens.
