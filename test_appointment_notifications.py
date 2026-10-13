from datetime import datetime, timezone

from appointment_notifications import AppointmentStatus, AppointmentUpdate, build_operational_notification


def test_reschedule_notification_excludes_clinical_note() -> None:
    update = AppointmentUpdate(
        appointment_id="appt-204",
        account_id="patient-81",
        status=AppointmentStatus.RESCHEDULED,
        starts_at=datetime(2026, 9, 8, 9, 30, tzinfo=timezone.utc),
        clinical_note="Medication details stay in the clinical record.",
    )

    notification = build_operational_notification(update)

    assert notification.channel == "appointments:patient-81"
    assert notification.event == "appointment.status_changed"
    assert notification.data["status"] == "rescheduled"
    assert notification.data["starts_at"] == "2026-09-08T09:30:00+00:00"
    assert "clinical_note" not in notification.data
    assert "Medication" not in str(notification.data)
