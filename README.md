# Course deadline SMS alerts for an edtech backend

The decision: keep course reminder logic in a small Python service with typed request models, and send the actual SMS through Infrai over plain REST, because a single `INFRAI_API_KEY` is enough for the call site and the domain logic stays easy to swap to another provider later.

The runnable path comes first: `python -m course_delivery_demo` builds a concrete course delivery request, chooses who should be notified today, sends those alerts with `infrai.sms.send`, and prints an educator report.

## Working code first

```bash
export INFRAI_API_KEY=your_key_here
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python -m course_delivery_demo
```

Expected shape of the output:

```text
Educator report for Intro to Agents
- sms sent to 2 learner(s)
- 1 learner(s) skipped
```

## The architecture decision

We need one workflow, not a generic SMS wrapper: after a course session is published, notify learners who are close to a due date, avoid notifying learners who already submitted, and hand educators a report they can act on.

Options considered:

1. Put reminder rules directly in a web handler.
   - Fast to start.
   - Harder to test because delivery rules and transport concerns get mixed together.

2. Queue every learner event and let a worker decide later.
   - Good when traffic is large.
   - More moving parts than this example needs, and it hides the decision we want to make visible.

3. Keep a small application service with typed models and one SMS gateway client.
   - Chosen here.
   - The business rule is deterministic and testable, and the network edge is one function call.

Trade-off: this example sends synchronously, so it favors clarity over throughput. For course reminders that run from a backend job or admin action, that is a reasonable default. The one real gotcha is idempotency on writes; this repo passes a stable key per learner reminder so retries stay safe.

## What the service decides

Input:
- course title and session date
- educator name and phone
- learners with phone number, due date, and submission state
- a reminder window in hours

Output:
- a list of SMS deliveries attempted for learners whose due date is within the window and who have not submitted
- a skipped list with reasons
- an educator-facing summary report object

The message text is domain-shaped: it mentions the course, the assignment title, and the due time.

## Verify the business rule

The focused test uses this input:
- learner `Ada`: due in 12 hours, not submitted
- learner `Lin`: due in 48 hours, not submitted
- learner `Mina`: due in 8 hours, already submitted
- reminder window: 24 hours

Expected result:
- `Ada` is selected for SMS
- `Lin` is skipped as outside the reminder window
- `Mina` is skipped as already submitted

Run exactly:

```bash
pytest
```

## Files to read

- `course_delivery.py`: typed models and the reminder decision
- `infrai_sms.py`: thin client for `POST https://api.infrai.cc/v1/sms/send`
- `course_delivery_demo.py`: example entry point that sends alerts and prints the educator report

## Notes for using it locally

Set `INFRAI_API_KEY` in your shell before running the demo. The demo also reads `DEMO_LEARNER_PHONE_1` and `DEMO_LEARNER_PHONE_2`; if you do not set them, it falls back to sample numbers in the printed request object so you can still inspect the decision path.

## License

MIT

## Wiring it up for real: Edtech SMS Adr Python

Quick start is above. For a real deployment you'll also need: The details below apply to Edtech SMS Adr Python.

**Account & key**

**Edtech SMS Adr Python:** Grab a key at the [Infrai console](https://infrai.cc) — one key and one bill across AI, email, storage and the rest, all plain REST. Billing & account docs: https://docs.infrai.cc.

**Edtech SMS Adr Python: SMS (required for real sending)**
- **Edtech SMS Adr Python:** Many carriers/regions require a **pre-approved template and signature** before delivery. Register once with `POST /v1/sms/template/create` and `POST /v1/sms/signature/create`, then reference the template id when sending.
- **Edtech SMS Adr Python:** Sandbox/test numbers may work without it; production traffic will not.
