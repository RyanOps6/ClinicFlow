import type {
  AppointmentResponse,
  DashboardOverview,
  SendMessageResponse,
  SessionSnapshot,
  StartSessionResponse,
} from '../types';

const BASE = '/api';

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${url}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`);
  }
  return res.json();
}

export async function startRescheduleSession(): Promise<StartSessionResponse> {
  return request('/sessions/start', {
    method: 'POST',
    body: JSON.stringify({ session_type: 'reschedule', channel: 'simulated' }),
  });
}

export async function startCancelSession(): Promise<StartSessionResponse> {
  return request('/sessions/start', {
    method: 'POST',
    body: JSON.stringify({ session_type: 'cancel', channel: 'simulated' }),
  });
}

export async function startSession(sessionType = 'booking'): Promise<StartSessionResponse> {
  return request('/sessions/start', {
    method: 'POST',
    body: JSON.stringify({ session_type: sessionType, channel: 'simulated' }),
  });
}

export async function sendMessage(
  sessionId: number,
  message: string
): Promise<SendMessageResponse> {
  return request(`/sessions/${sessionId}/message`, {
    method: 'POST',
    body: JSON.stringify({ message }),
  });
}

export async function getSession(sessionId: number): Promise<SessionSnapshot> {
  return request(`/sessions/${sessionId}`);
}

export async function getAppointments(): Promise<AppointmentResponse[]> {
  return request('/appointments');
}

export async function rescheduleAppointment(
  appointmentId: number,
  newDate: string,
  newTime: string
): Promise<AppointmentResponse> {
  return request(`/appointments/${appointmentId}/reschedule`, {
    method: 'POST',
    body: JSON.stringify({ new_date: newDate, new_time: newTime }),
  });
}

export async function cancelAppointment(appointmentId: number): Promise<AppointmentResponse> {
  return request(`/appointments/${appointmentId}/cancel`, {
    method: 'POST',
  });
}

export async function getDashboardOverview(): Promise<DashboardOverview> {
  return request('/dashboard/overview');
}

export async function getSessionAuditLogs(sessionId: number): Promise<any[]> {
  return request(`/sessions/${sessionId}/audit-logs`);
}

export async function getSessions(page = 1, limit = 20): Promise<SessionSnapshot[]> {
  return request(`/sessions?page=${page}&limit=${limit}`);
}

export async function getSessionMessages(sessionId: number): Promise<any[]> {
  return request(`/sessions/${sessionId}/messages`);
}

export async function cancelAppointmentPatch(appointmentId: number): Promise<AppointmentResponse> {
  return request(`/appointments/${appointmentId}/cancel`, {
    method: 'PATCH',
  });
}
