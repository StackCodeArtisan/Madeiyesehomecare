# Medaiyese Home Care Services

Production-minded single-page Flask site inspired by the Kindred Home Care layout. Visitors can learn about services, explore a dedicated contact page, and submit a secure "Request Care" form that emails your intake team.

## Features
- Bootstrap 5 layout with hero, services, responsive contact form, Kindred-style contact page, and dedicated appointment booking page
- Vanilla JS fetch submission with inline validation and messaging
- Flask backend with CSRF token, honeypot, timestamp check, and basic rate limiting (5 requests / 10 min per IP)
- Email delivery via SMTP by default, with commented Flask-Mail alternative
- Optional `/thank-you` template if you prefer redirect over AJAX response

## Setup
1. **Clone / copy the project** into your environment.
2. **Create and populate `.env`** (copy `.env.example` and set real values):
   ```bash
   cp .env.example .env
   ```
   Update SMTP credentials plus `DESTINATION_EMAIL` and `FLASK_SECRET_KEY`.
3. **Install Python deps** (Python 3.10+ recommended):
   ```bash
   python -m venv .venv
   .\.venv\Scripts\activate  # Windows
   pip install -r requirements.txt
   ```

## Running locally
```bash
set FLASK_APP=app.py
flask run --reload
```
Visit `http://127.0.0.1:5000/`.

## Testing the contact form
Use the UI or send a JSON payload:
```bash
curl -X POST http://127.0.0.1:5000/request-care ^
  -H "Content-Type: application/json" ^
  -d "{\"full_name\": \"Jane Caregiver\", \"phone\": \"2045551212\", \"email\": \"jane@example.com\", \"address\": \"1 River St\", \"start_date\": \"2025-12-01\", \"care_type\": \"Companion Care\", \"notes\": \"Evenings\", \"csrf_token\": \"REPLACE\"}"
```
Grab a CSRF token from the page source or browser dev tools first. Successful responses return JSON `{ "success": true, "message": "Request sent successfully." }`.

### Appointment Booking API
```bash
curl -X POST http://127.0.0.1:5000/submit-appointment ^ 
  -H "Content-Type: application/json" ^
  -d "{\"full_name\":\"Jane Client\",\"email\":\"jane@example.com\",\"phone\":\"2045554444\",\"preferred_date\":\"2025-12-05\",\"preferred_time\":\"10:00\",\"reason\":\"Discuss respite care\",\"csrf_token\":\"REPLACE\"}"
```
Returns `{ "success": true, "message": "Request sent successfully." }` when email dispatch succeeds.

## Email delivery options
- **Default (`smtplib`)**: populate the SMTP variables. The backend sends plain-text summaries and sets a `Reply-To` header.
- **Flask-Mail (optional)**: uncomment the provided block in `app.py`, install `Flask-Mail`, and update the `requirements.txt` entry if you want to vendor-lock it.

## Security & production notes
- Current CSRF token + session timestamp guard + honeypot protect basic spam. Replace the in-memory rate limiter with Redis or a dedicated gateway for high traffic.
- Always run behind HTTPS (e.g., reverse proxy via nginx / load balancer) so credentials and CSRF tokens remain confidential.
- Configure a production SMTP provider (SendGrid, Mailgun, SES) and set environment variables in your hosting platform.
- Log files and monitoring should capture `app.logger` output for audit trails.

## Verifying email in development
You can run a local SMTP debug server instead of sending real mail:
```bash
python -m smtpd -c DebuggingServer -n localhost:1025
```
Set `MAIL_SERVER=localhost`, `MAIL_PORT=1025`, `MAIL_USE_TLS=false`, `MAIL_USE_SSL=false` to inspect payloads in the console.

---
Need help deploying (Render, Railway, Fly.io, etc.)? Configure the environment variables there, enable HTTPS, and use `gunicorn app:app` behind the platform’s web server.
# Madeiyesehomecare
# MedCare
# Madeiyesehomecare
