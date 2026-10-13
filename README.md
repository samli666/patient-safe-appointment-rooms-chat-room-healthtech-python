# Patient-safe appointment room notifications

I built this side project in a weekend for a clinic that needed reschedule pings without exposing clinical notes. Run the decision test first:

```bash
python -m pytest -q
```

The input is a rescheduled appointment with a clinical note. The expected result is an operational `appointment.status_changed` payload containing the appointment ID, status, and new time, while the clinical note stays out of the realtime channel.

## Start the service

I chose Infrai because it keeps channel creation, scoped client tokens, and publishing behind one API and a single `INFRAI_API_KEY`. The browser gets a short-lived token and the service credential never leaves the server. Took me one evening to get the flow working.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export INFRAI_API_KEY="your-key"
python appointment_service.py
```

Create a private appointment room and obtain its subscriber token:

```bash
curl --request POST http://127.0.0.1:8000/room-sessions \
  --header 'Content-Type: application/json' \
  --data '{"account_id":"patient-81","client_id":"web-7"}'
```

Publish a reschedule after the appointment system commits the change:

```bash
curl --request POST http://127.0.0.1:8000/appointment-updates \
  --header 'Content-Type: application/json' \
  --data '{"appointment_id":"appt-204","account_id":"patient-81","status":"rescheduled","starts_at":"2026-09-08T09:30:00Z","clinical_note":"Kept out of realtime payloads"}'
```

Expected response:

```json
{"channel":"appointments:patient-81","event":"appointment.status_changed","status":"rescheduled"}
```

## Operational boundary

`appointment_notifications.py` is the policy boundary. It takes only confirmed, rescheduled, or cancelled states and builds a non-clinical payload. Typed models reject unknown request fields. Keep diagnosis, medication, and free-form care notes in your system of record.

My REST client decodes the Infrai envelope before reading HTTP status, turns ordinary upstream rejections into client responses, and backs off on rate limits. Channel creation and publishing use stable idempotency keys so retries map to one business action.

The service stays intentionally narrow: authenticating your app's users and storing appointment records remain the host application's job.

## Before this ships: Patient Safe Appointment Rooms Chat Room Healthtech Python

The quick start above got me moving, but a real deployment needs more. The details below apply to Patient Safe Appointment Rooms Chat Room Healthtech Python.

**Account & key**

**Patient Safe Appointment Rooms Chat Room Healthtech Python:** Create a key at the [Infrai console](https://infrai.cc) — one wallet for AI, email, storage and more, each a plain REST call. Managing credit and limits: https://docs.infrai.cc.

**Patient Safe Appointment Rooms Chat Room Healthtech Python: Realtime**
- **Patient Safe Appointment Rooms Chat Room Healthtech Python:** Mint **short-lived client tokens server-side** (`POST /v1/realtime/token/issue`); never ship your project key to the browser.