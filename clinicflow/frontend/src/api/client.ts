import type {
  AppointmentResponse,
  DashboardOverview,
  SendMessageResponse,
  SessionSnapshot,
  StartSessionResponse,
} from '../types';

export const BASE = import.meta.env.PROD
  ? 'https://clinicflow-backend-h4w4.onrender.com'
  : '';

let authToken: string | null = localStorage.getItem('auth_token');

export function getAuthToken(): string | null {
  return authToken;
}

export function setAuthToken(token: string | null): void {
  authToken = token;
  if (token) {
    localStorage.setItem('auth_token', token);
  } else {
    localStorage.removeItem('auth_token');
  }
}

export async function login(username: string, password: string): Promise<{ token: string; username: string }> {
  const res = await fetch(`${BASE}/api/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  });
  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || `Login error: ${res.status}`);
  }
  const data = await res.json();
  setAuthToken(data.token);
  return data;
}

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (authToken) {
    headers['Authorization'] = `Bearer ${authToken}`;
  }
  
  const res = await fetch(`${BASE}/api${url}`, {
    headers,
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
