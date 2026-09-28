from datetime import datetime, timedelta, timezone

from course_delivery import CourseDeliveryRequest, CourseReminderService, LearnerDeadline


def test_build_notification_plan_selects_only_due_unsubmitted_learners() -> None:
    now = datetime(2026, 1, 15, 9, 0, tzinfo=timezone.utc)
    request = CourseDeliveryRequest(
        course_id="course-101",
        course_title="Intro to Agents",
        session_title="Week 3 release",
        session_published_at=now,
        educator_name="Dr. Rivera",
        educator_phone_number="+15550000000",
        reminder_window_hours=24,
        learners=[
            LearnerDeadline(
                learner_id="ada",
                learner_name="Ada",
                phone_number="+15550100001",
                assignment_title="Tool-use reflection",
                due_at=now + timedelta(hours=12),
                submitted_at=None,
            ),
            LearnerDeadline(
                learner_id="lin",
                learner_name="Lin",
                phone_number="+15550100002",
                assignment_title="Tool-use reflection",
                due_at=now + timedelta(hours=48),
                submitted_at=None,
            ),
            LearnerDeadline(
                learner_id="mina",
                learner_name="Mina",
                phone_number="+15550100003",
                assignment_title="Tool-use reflection",
                due_at=now + timedelta(hours=8),
                submitted_at=now - timedelta(hours=1),
            ),
        ],
    )

    service = CourseReminderService()
    plan = service.build_notification_plan(request, now=now)

    send_items = [item for item in plan if item.decision == "send"]
    skipped = {item.learner_name: item.reason for item in plan if item.decision == "skip"}

    assert [item.learner_name for item in send_items] == ["Ada"]
    assert skipped["Lin"] == "outside reminder window"
    assert skipped["Mina"] == "already submitted"
    assert "Intro to Agents" in send_items[0].message_text
    assert send_items[0].idempotency_key == (
        f"course-reminder:course-101:Week 3 release:ada:{(now + timedelta(hours=12)).isoformat()}"
    )
