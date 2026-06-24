export interface StartSessionRequest {
  session_type: string;
  channel: string;
}

export interface StartSessionResponse {
  session_id: number;
  assistant_message: string;
  workflow_state: string;
  collected_data: Record<string, unknown>;
}

export interface SendMessageRequest {
  message: string;
}

export interface SendMessageResponse {
  session_id: number;
  assistant_message: string;
  workflow_state: string;
  collected_data: Record<string, unknown>;
  intent: string;
  urgency_level: string;
  appointment_id?: number;
  completed: boolean;
}

export interface SessionSnapshot {
  id: number;
  session_type: string;
  channel: string;
  status: string;
  intent: string;
  workflow_state?: string;
  collected_data: Record<string, unknown>;
  transcript: MessageEntry[];
  offered_slots: string[];
  selected_slot?: string;
  summary_text?: string;
  urgency_level: string;
  started_at?: string;
  ended_at?: string;
  created_at?: string;
}

export interface MessageEntry {
  role: string;
  content: string;
}

export interface AppointmentResponse {
  id: number;
  patient_id: number;
  patient_name?: string;
  appointment_type: string;
  doctor_name?: string;
  scheduled_date: string;
  scheduled_time: string;
  status: string;
  reason_for_visit: string;
  notes?: string;
  created_at?: string;
}

export interface DashboardOverview {
  total_appointments: number;
  active_sessions: number;
  escalations: number;
  recent_sessions: DashboardSession[];
  recent_events: DashboardEvent[];
  recent_appointments: DashboardAppointment[];
}

export interface DashboardSession {
  id: number;
  session_type: string;
  status: string;
  intent: string;
  urgency_level: string;
  patient_name?: string;
  started_at?: string;
}

export interface DashboardEvent {
  id: number;
  session_id: number;
  event_type: string;
  created_at?: string;
}

export interface DashboardAppointment {
  id: number;
  patient_name?: string;
  scheduled_date: string;
  scheduled_time: string;
  status: string;
}
