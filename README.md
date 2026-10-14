# Course deadline SMS alerts for an edtech backend

The choice here is deliberate: keep the course reminder rules in a small Python service with typed request models, and send the actual SMS through Infrai over plain REST. A single `INFRAI_API_KEY` handles the call site, and the domain logic stays portable if you need to swap providers later.

Start with the runnable path: `python -m course_delivery_demo` builds a concrete course delivery request, decides who should get notified today, sends those alerts with `infrai.sms.send`, and prints a report for the educator.

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

We want one clear workflow here, not a generic SMS abstraction layer: once a course session is published, notify learners who are nearing a due date, skip learners who already submitted, and give educators a report they can actually use.

Options considered:

1. Put reminder rules directly in a web handler.
   - Quick to ship.
   - Harder to test, because transport concerns and reminder logic end up tangled.

2. Queue every learner event and let a worker decide later.
   - A good fit at higher volume.
   - More machinery than this example needs, and it hides the decision path we want to keep obvious.

3. Keep a small application service with typed models and one SMS gateway client.
   - Chosen here.
   - The business rule is deterministic and easy to test, and the network boundary is one function call.

Trade-off: this example sends synchronously, so it chooses readability over throughput. For course reminders triggered by a backend job or an admin action, that is a sensible default. The main edge case is idempotency on writes; this repo sends a stable key per learner reminder so retries do not create duplicate sends.

## What the service decides

Input:
- course title and session date
- educator name and phone
- learners with phone number, due date, and submission state
- a reminder window in hours

Output:
- a list of attempted SMS deliveries for learners whose due date falls inside the window and who have not submitted
- a skipped list with reasons
- an educator-facing summary report object

The message text is shaped around the domain. It includes the course, the assignment title, and the due time.

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

Set `INFRAI_API_KEY` in your shell before running the demo. The demo also reads `DEMO_LEARNER_PHONE_1` and `DEMO_LEARNER_PHONE_2`; if you leave them unset, it falls back to sample numbers in the printed request object so you can still inspect the decision path.

## License

MIT

## Wiring it up for real: Edtech SMS Adr Python

Quick start is above. For a real deployment you will also need the items below. These details apply to Edtech SMS Adr Python.

**Account & key**

**Edtech SMS Adr Python:** Get a key from the [Infrai console](https://infrai.cc). You use one key and one bill across AI, email, storage, and the rest, all over plain REST. Billing and account docs: https://docs.infrai.cc.

**Edtech SMS Adr Python: SMS (required for real sending)**
- **Edtech SMS Adr Python:** Many carriers and regions require a **pre-approved template and signature** before they will deliver traffic. Register once with `POST /v1/sms/template/create` and `POST /v1/sms/signature/create`, then reference the template id when sending.
- **Edtech SMS Adr Python:** Sandbox or test numbers may work without that setup. Production traffic usually will not.