from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import and_
from sqlalchemy.orm import Session as DBSession

from app.models.appointment import Appointment
from app.models.provider_schedule import ProviderSchedule

DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def _generate_time_slots(start_time: str, end_time: str, duration_minutes: int) -> list[str]:
    """Generate time slot strings from start to end with given duration."""
    sh, sm = map(int, start_time.split(":"))
    eh, em = map(int, end_time.split(":"))
    start_mins = sh * 60 + sm
    end_mins = eh * 60 + em
    slots = []
    while start_mins + duration_minutes <= end_mins:
        h = start_mins // 60
        m = start_mins % 60
        slots.append(f"{h:02d}:{m:02d}")
        start_mins += duration_minutes
    return slots


def get_provider_schedules(db: DBSession) -> list[dict]:
    """Get all provider schedules."""
    schedules = db.query(ProviderSchedule).order_by(
        ProviderSchedule.provider_name,
        ProviderSchedule.day_of_week,
    ).all()
    return [
        {
            "id": s.id,
            "provider_name": s.provider_name,
            "day_of_week": s.day_of_week,
            "day_name": DAY_NAMES[s.day_of_week],
            "start_time": s.start_time,
            "end_time": s.end_time,
            "slot_duration_minutes": s.slot_duration_minutes,
        }
        for s in schedules
    ]


def get_available_slots(
    db: DBSession,
    days: int = 7,
    provider_name: Optional[str] = None,
    exclude_appointment_id: Optional[int] = None,
) -> list[str]:
    """Generate available slots from provider schedules minus booked appointments.

    Args:
        db: database session
        days: how many days ahead to look
        provider_name: if set, only show slots for this provider
        exclude_appointment_id: if set, this appointment's slot is NOT treated as booked
            (used during reschedule so the current slot stays available)
    """
    now = datetime.now()
    today_date = now.date()
    cutoff = today_date + timedelta(days=days)

    schedules = db.query(ProviderSchedule).all()
    if provider_name:
        schedules = [s for s in schedules if s.provider_name.lower() == provider_name.lower()]

    if not schedules:
        return _fallback_static_slots(days)

    booked = db.query(
        Appointment.scheduled_date,
        Appointment.scheduled_time,
        Appointment.doctor_name,
    ).filter(
        and_(
            Appointment.status.in_(["booked", "rescheduled"]),
            Appointment.scheduled_date >= today_date.strftime("%Y-%m-%d"),
            Appointment.scheduled_date <= cutoff.strftime("%Y-%m-%d"),
        )
    ).all()

    booked_set = {(b.scheduled_date, b.scheduled_time, b.doctor_name) for b in booked}
    if exclude_appointment_id:
        excl = db.query(Appointment).filter(Appointment.id == exclude_appointment_id).first()
        if excl:
            booked_set.discard((excl.scheduled_date, excl.scheduled_time, excl.doctor_name))

    result = []
    for day_offset in range(days):
        target_date = today_date + timedelta(days=day_offset)
        date_str = target_date.strftime("%Y-%m-%d")
        dow = target_date.weekday()

        day_schedules = [s for s in schedules if s.day_of_week == dow]
        for sched in day_schedules:
            all_times = _generate_time_slots(
                sched.start_time, sched.end_time, sched.slot_duration_minutes
            )
            for t in all_times:
                if (date_str, t, sched.provider_name) not in booked_set:
                    label = f"{DAY_NAMES[dow]} {date_str} at {t} — {sched.provider_name}"
                    result.append(label)

    return result


def is_slot_available(
    db: DBSession,
    date_str: str,
    time_str: str,
    provider_name: Optional[str] = None,
    exclude_appointment_id: Optional[int] = None,
) -> bool:
    """Check if a specific slot is available."""
    slots = get_available_slots(db, days=14, provider_name=provider_name, exclude_appointment_id=exclude_appointment_id)
    target = f"{date_str} at {time_str}"
    return any(target in s for s in slots)


def find_nearest_available(
    db: DBSession,
    requested_date: str,
    requested_time: str,
    provider_name: Optional[str] = None,
    exclude_appointment_id: Optional[int] = None,
    count: int = 5,
) -> list[str]:
    """Find nearest available slots to a requested date/time."""
    slots = get_available_slots(db, days=14, provider_name=provider_name, exclude_appointment_id=exclude_appointment_id)
    if not slots:
        return []

    try:
        req_h = int(requested_time.split(":")[0])
    except (ValueError, IndexError):
        return slots[:count]

    same_date = [s for s in slots if requested_date in s]
    if same_date:
        def _slot_hour(s):
            try:
                return int(s.split(" at ")[-1].split(":")[0])
            except (ValueError, IndexError):
                return 99
        same_date.sort(key=lambda s: abs(_slot_hour(s) - req_h))
        return same_date[:count]

    return slots[:count]


def _fallback_static_slots(days: int) -> list[str]:
    """Fallback when no provider schedules exist — generates generic slots."""
    from app.utils.slot_utils import generate_slots, format_slots_for_display
    return format_slots_for_display(generate_slots(days))


def seed_default_providers(db: DBSession):
    """Create default provider schedules if none exist."""
    existing = db.query(ProviderSchedule).count()
    if existing > 0:
        return

    providers = [
        ("Dr. Smith", [(0, "09:00", "17:00"), (1, "09:00", "17:00"), (2, "09:00", "17:00"),
                       (3, "09:00", "17:00"), (4, "09:00", "15:00")]),
        ("Dr. Jones", [(0, "10:00", "18:00"), (1, "10:00", "18:00"), (2, "10:00", "18:00"),
                       (3, "10:00", "18:00"), (4, "10:00", "16:00")]),
    ]
    for name, days in providers:
        for dow, start, end in days:
            db.add(ProviderSchedule(
                provider_name=name,
                day_of_week=dow,
                start_time=start,
                end_time=end,
                slot_duration_minutes=60,
            ))
    db.commit()
