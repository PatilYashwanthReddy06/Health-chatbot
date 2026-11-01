"""In-memory OTP storage and optional email delivery (SMTP via env)."""
from __future__ import annotations

import os
import secrets
import smtplib
import time
from email.mime.text import MIMEText
from threading import Lock
from typing import Optional, Tuple

OTP_TTL_SEC = 300
_lock = Lock()
_patient_otp: dict[str, Tuple[str, float]] = {}  # phone -> (code, expiry_unix)
_doctor_otp: dict[str, Tuple[str, float]] = {}  # email_lower -> (code, expiry_unix)


def _generate_code() -> str:
    return f"{secrets.randbelow(900000) + 100000:06d}"


def store_patient_otp(phone: str) -> str:
    code = _generate_code()
    with _lock:
        _patient_otp[phone] = (code, time.time() + OTP_TTL_SEC)
    return code


def verify_patient_otp(phone: str, code: str) -> bool:
    if not code or not phone:
        return False
    with _lock:
        entry = _patient_otp.get(phone)
        if not entry:
            return False
        stored, exp = entry
        if time.time() > exp:
            del _patient_otp[phone]
            return False
        if stored != code.strip():
            return False
        del _patient_otp[phone]
        return True


def store_doctor_otp(email: str) -> str:
    code = _generate_code()
    key = email.strip().lower()
    with _lock:
        _doctor_otp[key] = (code, time.time() + OTP_TTL_SEC)
    return code


def verify_doctor_otp(email: str, code: str) -> bool:
    if not code or not email:
        return False
    key = email.strip().lower()
    with _lock:
        entry = _doctor_otp.get(key)
        if not entry:
            return False
        stored, exp = entry
        if time.time() > exp:
            del _doctor_otp[key]
            return False
        if stored != code.strip():
            return False
        del _doctor_otp[key]
        return True


def send_email_otp(to_email: str, otp_code: str) -> bool:
    """Send OTP email if SMTP_* env vars are set; otherwise return False."""
    host = os.environ.get("SMTP_HOST", "").strip()
    if not host:
        return False
    port = int(os.environ.get("SMTP_PORT", "587"))
    user = os.environ.get("SMTP_USER", "").strip()
    password = os.environ.get("SMTP_PASSWORD", "").strip()
    from_addr = os.environ.get("SMTP_FROM", user)
    subject = "Your Doctor account verification code"
    body = (
        f"Your verification code is: {otp_code}\n\n"
        "It expires in 5 minutes. If you did not request this, ignore this email."
    )
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = to_email
    try:
        with smtplib.SMTP(host, port, timeout=15) as smtp:
            smtp.starttls()
            if user and password:
                smtp.login(user, password)
            smtp.sendmail(from_addr, [to_email], msg.as_string())
        return True
    except Exception:
        return False
