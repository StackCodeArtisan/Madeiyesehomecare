"""app.py - Flask backend for MedaiyeseHomeCareServices"""
import logging
import os
import re
import secrets
import smtplib
import ssl
import time
from collections import defaultdict, deque
from datetime import datetime
from email.message import EmailMessage
from typing import Dict, Tuple

from flask import Flask, jsonify, render_template, request, session

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', 'change-me')
app.logger.setLevel(logging.INFO)

RATE_LIMIT_MAX = 5
RATE_LIMIT_WINDOW = 600  # seconds (10 minutes)
request_log: Dict[str, deque] = defaultdict(deque)
EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _clear_expired(ip: str, now_ts: float) -> None:
    window = request_log[ip]
    while window and now_ts - window[0] > RATE_LIMIT_WINDOW:
        window.popleft()


def is_rate_limited(ip: str) -> bool:
    now_ts = time.time()
    _clear_expired(ip, now_ts)
    if len(request_log[ip]) >= RATE_LIMIT_MAX:
        return True
    request_log[ip].append(now_ts)
    return False


def sanitize(value: str) -> str:
    if not value:
        return ''
    # Strip HTML tags (rough) and whitespace
    return re.sub(r'<[^>]+>', '', value).strip()


def issue_csrf_token() -> str:
    token = secrets.token_hex(16)
    session['csrf_token'] = token
    session['form_time'] = int(time.time())
    return token


def send_email(subject: str, reply_to: str, body: str) -> Tuple[bool, str]:
    """Send email using SMTP settings from environment variables."""
    server = os.environ.get('MAIL_SERVER')
    port = int(os.environ.get('MAIL_PORT', '587'))
    username = os.environ.get('MAIL_USERNAME')
    password = os.environ.get('MAIL_PASSWORD')
    use_tls = os.environ.get('MAIL_USE_TLS', 'true').lower() == 'true'
    use_ssl = os.environ.get('MAIL_USE_SSL', 'false').lower() == 'true'
    destination = os.environ.get('DESTINATION_EMAIL')

    if not all([server, port, username, password, destination]):
        return False, 'Email configuration missing. Please set environment variables.'

    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = username
    msg['To'] = destination
    if reply_to:
        msg['Reply-To'] = reply_to

    msg.set_content(body)

    try:
        if use_ssl:
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(server, port, context=context) as smtp:
                smtp.login(username, password)
                smtp.send_message(msg)
        else:
            with smtplib.SMTP(server, port) as smtp:
                if use_tls:
                    context = ssl.create_default_context()
                    smtp.starttls(context=context)
                smtp.login(username, password)
                smtp.send_message(msg)
    except Exception as exc:  # pragma: no cover - logged for observability
        app.logger.exception('Failed to send email: %s', exc)
        return False, 'Unable to send email at this time.'

    return True, 'Request sent successfully.'


def send_care_request_email(payload: Dict[str, str]) -> Tuple[bool, str]:
    body = (
        f"New care request submitted on {datetime.utcnow().isoformat()} UTC\n\n"
        f"Full Name: {payload['full_name']}\n"
        f"Phone: {payload['phone']}\n"
        f"Email: {payload['email']}\n"
        f"Address: {payload['address']}\n"
        f"Preferred Start Date: {payload['start_date']}\n"
        f"Type of Care: {payload['care_type']}\n"
        f"Additional Notes: {payload['notes'] or 'N/A'}\n"
    )
    subject = f"New Care Request from {payload['full_name']}"
    return send_email(subject, payload.get('email'), body)


# Optional Flask-Mail example (commented for reference)
# Optional Flask-Mail example (commented for reference)
# from flask_mail import Mail, Message
# mail = Mail(app)
# app.config.update(
#     MAIL_SERVER=os.environ.get('MAIL_SERVER'),
#     MAIL_PORT=int(os.environ.get('MAIL_PORT', 587)),
#     MAIL_USE_TLS=os.environ.get('MAIL_USE_TLS', 'true').lower() == 'true',
#     MAIL_USE_SSL=os.environ.get('MAIL_USE_SSL', 'false').lower() == 'true',
#     MAIL_USERNAME=os.environ.get('MAIL_USERNAME'),
#     MAIL_PASSWORD=os.environ.get('MAIL_PASSWORD'),
# )
# def send_mail_via_flask_mail(payload):
#     message = Message(
#         subject=f"New Care Request from {payload['full_name']}",
#         sender=app.config['MAIL_USERNAME'],
#         recipients=[os.environ.get('DESTINATION_EMAIL')],
#         reply_to=payload['email'],
#         body='...'
#     )
#     mail.send(message)


@app.before_request
def apply_simple_rate_limit():
    if request.endpoint == 'request_care' and request.method == 'POST':
        client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        if client_ip and is_rate_limited(client_ip):
            return jsonify({'success': False, 'message': 'Too many requests. Please try later.', 'csrf_token': issue_csrf_token()}), 429


@app.route('/')
def index():
    csrf_token = issue_csrf_token()
    return render_template('index.html', csrf_token=csrf_token)


@app.route('/request-care', methods=['POST'])
def request_care():
    if not request.is_json:
        return jsonify({'success': False, 'message': 'Invalid submission format.', 'csrf_token': issue_csrf_token()}), 400

    payload = request.get_json() or {}
    if payload.get('service_interest'):  # honeypot
        app.logger.warning('Honeypot triggered; dropping submission.')
        return jsonify({'success': False, 'message': 'Invalid submission.', 'csrf_token': issue_csrf_token()}), 400

    csrf_token = payload.get('csrf_token')
    if not csrf_token or csrf_token != session.get('csrf_token'):
        return jsonify({'success': False, 'message': 'Security token mismatch.', 'csrf_token': issue_csrf_token()}), 400

    form_time = session.get('form_time')
    if not form_time or time.time() - form_time < 3:
        return jsonify({'success': False, 'message': 'Submission too quick; suspected bot.', 'csrf_token': issue_csrf_token()}), 400

    required_fields = {
        'full_name': 'Full name is required.',
        'phone': 'Phone number is required.',
        'email': 'Valid email is required.',
        'address': 'Address is required.',
        'start_date': 'Preferred start date is required.',
        'care_type': 'Care type selection is required.'
    }
    errors = {}

    for field, message in required_fields.items():
        value = payload.get(field, '').strip()
        if not value:
            errors[field] = message
    email_value = payload.get('email', '').strip()
    if email_value and not EMAIL_REGEX.match(email_value):
        errors['email'] = 'Please enter a valid email address.'

    if errors:
        return jsonify({'success': False, 'errors': errors, 'message': 'Please review highlighted fields.', 'csrf_token': issue_csrf_token()}), 400

    safe_payload = {key: sanitize(payload.get(key, '')) for key in ['full_name', 'phone', 'email', 'address', 'start_date', 'care_type', 'notes']}

    ok, mail_message = send_care_request_email(safe_payload)
    status_code = 200 if ok else 500
    if ok:
        app.logger.info('Care request submitted by %s', safe_payload['full_name'])
    return jsonify({'success': ok, 'message': mail_message, 'csrf_token': issue_csrf_token()}), status_code


@app.route('/thank-you')
def thank_you():
    return render_template('thank_you.html')


@app.route('/contact')
def contact():
    csrf_token = issue_csrf_token()
    return render_template('contact.html', csrf_token=csrf_token)


@app.route('/appointment')
def appointment():
    csrf_token = issue_csrf_token()
    return render_template('appointment.html', csrf_token=csrf_token)


@app.route('/team')
def team():
    return render_template('team.html')


def send_appointment_email(payload: Dict[str, str]) -> Tuple[bool, str]:
    body = (
        f"New in-person appointment request submitted on {datetime.utcnow().isoformat()} UTC\n\n"
        f"Full Name: {payload['full_name']}\n"
        f"Email: {payload['email']}\n"
        f"Phone: {payload['phone']}\n"
        f"Preferred Date: {payload['preferred_date']}\n"
        f"Preferred Time: {payload['preferred_time']}\n"
        f"Reason: {payload['reason'] or 'N/A'}\n"
    )
    subject = f"Appointment Request from {payload['full_name']}"
    return send_email(subject, payload.get('email'), body)


@app.route('/submit-appointment', methods=['POST'])
def submit_appointment():
    if not request.is_json:
        return jsonify({'success': False, 'message': 'Invalid submission format.', 'csrf_token': issue_csrf_token()}), 400

    payload = request.get_json() or {}
    if payload.get('appointment_guard'):
        app.logger.warning('Appointment honeypot triggered.')
        return jsonify({'success': False, 'message': 'Invalid submission.', 'csrf_token': issue_csrf_token()}), 400

    csrf_token = payload.get('csrf_token')
    if not csrf_token or csrf_token != session.get('csrf_token'):
        return jsonify({'success': False, 'message': 'Security token mismatch.', 'csrf_token': issue_csrf_token()}), 400

    form_time = session.get('form_time')
    if not form_time or time.time() - form_time < 3:
        return jsonify({'success': False, 'message': 'Submission too quick; suspected bot.', 'csrf_token': issue_csrf_token()}), 400

    required_fields = {
        'full_name': 'Full name is required.',
        'email': 'A valid email is required.',
        'phone': 'Phone number is required.',
        'preferred_date': 'Preferred date is required.',
        'preferred_time': 'Preferred time is required.'
    }
    errors = {}

    for field, message in required_fields.items():
        value = payload.get(field, '').strip()
        if not value:
            errors[field] = message

    email_value = payload.get('email', '').strip()
    if email_value and not EMAIL_REGEX.match(email_value):
        errors['email'] = 'Please enter a valid email address.'

    if errors:
        return jsonify({'success': False, 'errors': errors, 'message': 'Please review highlighted fields.', 'csrf_token': issue_csrf_token()}), 400

    safe_payload = {key: sanitize(payload.get(key, '')) for key in ['full_name', 'email', 'phone', 'preferred_date', 'preferred_time', 'reason']}

    ok, message = send_appointment_email(safe_payload)
    status_code = 200 if ok else 500
    if ok:
        app.logger.info('Appointment request submitted by %s', safe_payload['full_name'])
    return jsonify({'success': ok, 'message': message, 'csrf_token': issue_csrf_token()}), status_code

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))  # Render provides PORT
    app.run(host='0.0.0.0', port=port, debug=os.environ.get('FLASK_ENV') == 'development')
