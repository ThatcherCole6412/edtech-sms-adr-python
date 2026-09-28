from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

from course_delivery import (
    CourseDeliveryRequest,
    CourseReminderService,
    LearnerDeadline,
    SmsDeliveryRecord,
)
from infrai_sms import infrai


def build_demo_request() -> CourseDeliveryRequest:
    now = datetime.now(timezone.utc)
    return CourseDeliveryRequest(
        course_id="course-101",
        course_title="Intro to Agents",
        session_title="Week 3 release",
        session_published_at=now,
        educator_name="Dr. Rivera",
        educator_phone_number="+15550000000",
        reminder_window_hours=24,
        learners=[
            LearnerDeadline(
                learner_id="learner-ada",
                learner_name="Ada",
                phone_number=os.environ.get("DEMO_LEARNER_PHONE_1", "+15550100001"),
                assignment_title="Tool-use reflection",
                due_at=now + timedelta(hours=12),
                submitted_at=None,
            ),
            LearnerDeadline(
                learner_id="learner-lin",
                learner_name="Lin",
                phone_number=os.environ.get("DEMO_LEARNER_PHONE_2", "+15550100002"),
                assignment_title="Tool-use reflection",
                due_at=now + timedelta(hours=20),
                submitted_at=None,
            ),
            LearnerDeadline(
                learner_id="learner-mina",
                learner_name="Mina",
                phone_number=os.environ.get("DEMO_LEARNER_PHONE_3", "+15550100003"),
                assignment_title="Tool-use reflection",
                due_at=now + timedelta(hours=8),
                submitted_at=now - timedelta(hours=1),
            ),
        ],
    )


def main() -> None:
    request = build_demo_request()
    service = CourseReminderService()
    plan = service.build_notification_plan(request, now=request.session_published_at)

    delivered = []
    skipped = []

    for item in plan:
        if item.decision == "skip":
            skipped.append(item)
            continue

        result = infrai.sms.send(
            {
                "to": item.phone_number,
                "body": item.message_text,
            },
            idempotency_key=item.idempotency_key or item.learner_id,
        )
        delivered.append(
            SmsDeliveryRecord(
                learner_id=item.learner_id,
                learner_name=item.learner_name,
                phone_number=item.phone_number,
                assignment_title=item.assignment_title,
                due_at=item.due_at,
                message_text=item.message_text or "",
                provider_message_id=result.data.get("message_id", "unknown"),
            )
        )

    report = service.build_report(
        request=request,
        delivered=delivered,
        skipped=skipped,
        now=request.session_published_at,
    )

    print(f"Educator report for {report.course_title}")
    print(f"- sms sent to {report.sent_count} learner(s)")
    print(f"- {report.skipped_count} learner(s) skipped")


if __name__ == "__main__":
    main()
