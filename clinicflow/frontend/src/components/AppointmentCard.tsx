import type { AppointmentResponse } from '../types';

interface Props {
  appointment: AppointmentResponse;
  onReschedule?: (id: number) => void;
  onCancel?: (id: number) => void;
}

export default function AppointmentCard({ appointment, onReschedule, onCancel }: Props) {
  return (
    <div className={`appointment-card status-${appointment.status}`}>
      <div className="card-header">
        <strong>{appointment.patient_name ?? 'Unknown'}</strong>
        <span className={`status-badge status-${appointment.status}`}>{appointment.status}</span>
      </div>
      <div className="card-body">
        <p><span>Date:</span> {appointment.scheduled_date} at {appointment.scheduled_time}</p>
        <p><span>Reason:</span> {appointment.reason_for_visit}</p>
        {appointment.doctor_name && <p><span>Doctor:</span> {appointment.doctor_name}</p>}
      </div>
      {appointment.status === 'booked' && (
        <div className="card-actions">
          {onReschedule && (
            <button className="btn btn-sm" onClick={() => onReschedule(appointment.id)}>
              Reschedule
            </button>
          )}
          {onCancel && (
            <button className="btn btn-sm btn-danger" onClick={() => onCancel(appointment.id)}>
              Cancel
            </button>
          )}
        </div>
      )}
    </div>
  );
}
