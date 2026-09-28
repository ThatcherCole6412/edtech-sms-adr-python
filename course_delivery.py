from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class LearnerDeadline(BaseModel):
    learner_id: str
    learner_name: str
    phone_number: str
    assignment_title: str
    due_at: datetime
    submitted_at: Optional[datetime] = None


class CourseDeliveryRequest(BaseModel):
    course_id: str
    course_title: str
    session_title: str
    session_published_at: datetime
    educator_name: str
    educator_phone_number: str
    reminder_window_hours: int = Field(gt=0, le=168)
    learners: List[LearnerDeadline]


class LearnerNotificationPlan(BaseModel):
    learner_id: str
    learner_name: str
    phone_number: str
    assignment_title: str
    due_at: datetime
    decision: Literal["send", "skip"]
    reason: str
    message_text: Optional[str] = None
    idempotency_key: Optional[str] = None


class SmsDeliveryRecord(BaseModel):
    learner_id: str
    learner_name: str
    phone_number: str
    assignment_title: str
    due_at: datetime
    message_text: str
    provider_message_id: str


class EducatorReport(BaseModel):
    course_title: str
    session_title: str
    educator_name: str
    generated_at: datetime
    sent_count: int
    skipped_count: int
    delivered: List[SmsDeliveryRecord]
    skipped: List[LearnerNotificationPlan]


class CourseReminderService:
    def build_notification_plan(
        self,
        request: CourseDeliveryRequest,
        now: Optional[datetime] = None,
    ) -> List[LearnerNotificationPlan]:
        decision_time = now or datetime.now(timezone.utc)
        window_end = decision_time + timedelta(hours=request.reminder_window_hours)
        plans: List[LearnerNotificationPlan] = []

        for learner in request.learners:
            if learner.submitted_at is not None:
                plans.append(
                    LearnerNotificationPlan(
                        learner_id=learner.learner_id,
                        learner_name=learner.learner_name,
                        phone_number=learner.phone_number,
                        assignment_title=learner.assignment_title,
                        due_at=learner.due_at,
                        decision="skip",
                        reason="already submitted",
                    )
                )
                continue

            if learner.due_at > window_end:
                plans.append(
                    LearnerNotificationPlan(
                        learner_id=learner.learner_id,
                        learner_name=learner.learner_name,
                        phone_number=learner.phone_number,
                        assignment_title=learner.assignment_title,
                        due_at=learner.due_at,
                        decision="skip",
                        reason="outside reminder window",
                    )
                )
                continue

            if learner.due_at < decision_time:
                plans.append(
                    LearnerNotificationPlan(
                        learner_id=learner.learner_id,
                        learner_name=learner.learner_name,
                        phone_number=learner.phone_number,
                        assignment_title=learner.assignment_title,
                        due_at=learner.due_at,
                        decision="skip",
                        reason="deadline already passed",
                    )
                )
                continue

            message_text = (
                f"{learner.learner_name}, {learner.assignment_title} for {request.course_title} "
                f"is due at {learner.due_at.strftime('%Y-%m-%d %H:%M UTC')}. "
                f"Reply to {request.educator_name} if you need help."
            )
            idempotency_key = (
                f"course-reminder:{request.course_id}:{request.session_title}:"
                f"{learner.learner_id}:{learner.due_at.isoformat()}"
            )
            plans.append(
                LearnerNotificationPlan(
                    learner_id=learner.learner_id,
                    learner_name=learner.learner_name,
                    phone_number=learner.phone_number,
                    assignment_title=learner.assignment_title,
                    due_at=learner.due_at,
                    decision="send",
                    reason="due soon and not submitted",
                    message_text=message_text,
                    idempotency_key=idempotency_key,
                )
            )

        return plans

    def build_report(
        self,
        request: CourseDeliveryRequest,
        delivered: List[SmsDeliveryRecord],
        skipped: List[LearnerNotificationPlan],
        now: Optional[datetime] = None,
    ) -> EducatorReport:
        return EducatorReport(
            course_title=request.course_title,
            session_title=request.session_title,
            educator_name=request.educator_name,
            generated_at=now or datetime.now(timezone.utc),
            sent_count=len(delivered),
            skipped_count=len(skipped),
            delivered=delivered,
            skipped=skipped,
        )
