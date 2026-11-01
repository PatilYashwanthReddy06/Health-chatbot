from __future__ import annotations

import sys
import os

# Add project root to Python path
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from pathlib import Path
from typing import Optional, Dict, Any

from flask import Flask, jsonify, request, session, send_from_directory

from database.db import init_db, get_connection, hash_password
from backend.appointment_handler import list_doctor_appointments, set_appointment_status
from backend.otp_service import store_doctor_otp, verify_doctor_otp, send_email_otp

PROJECT_DIR = Path(__file__).resolve().parent.parent
DOCTOR_FRONTEND_DIR = PROJECT_DIR / "doctor_frontend"


def create_app() -> Flask:
    app = Flask(
        __name__,
        static_folder=str(DOCTOR_FRONTEND_DIR),
        static_url_path="/static",
    )
    app.secret_key = "dev-doctor-secret-key-change-me"  # for demo only
    # Separate cookie from patient app to avoid overwriting sessions
    app.config["SESSION_COOKIE_NAME"] = "doctor_session"

    init_db()

    def get_current_doctor() -> Optional[Dict[str, Any]]:
        doctor_id = session.get("doctor_id")
        if not doctor_id:
            return None
        with get_connection() as conn:
            cur = conn.cursor(dictionary=True)
            cur.execute(
                "SELECT id, name, email, specialization FROM doctors WHERE id = %s",
                (doctor_id,),
            )
            row = cur.fetchone()
            return dict(row) if row else None

    @app.route("/")
    def index():
        return send_from_directory(str(DOCTOR_FRONTEND_DIR), "doctor_login.html")

    @app.route("/dashboard")
    def dashboard():
        return send_from_directory(str(DOCTOR_FRONTEND_DIR), "doctor_dashboard.html")

    @app.route("/register")
    def register_page():
        return send_from_directory(str(DOCTOR_FRONTEND_DIR), "doctor_register.html")

    @app.route("/api/otp/doctor/send", methods=["POST"])
    def api_otp_doctor_send():
        data = request.get_json(silent=True) or {}
        email = (data.get("email") or "").strip().lower()
        if "@" not in email or "." not in email.split("@")[-1]:
            return jsonify({"error": "Enter a valid email address."}), 400
        with get_connection() as conn:
            cur = conn.cursor(dictionary=True)
            cur.execute("SELECT id FROM doctors WHERE email = %s", (email,))
            if cur.fetchone():
                return jsonify({"error": "This email is already registered."}), 400
        code = store_doctor_otp(email)
        sent = send_email_otp(email, code)
        if not sent:
            print(f"[Doctor OTP] email={email} code={code}")
        msg = (
            "Verification email sent."
            if sent
            else "Email could not be sent (check SMTP settings). See server console for OTP in development."
        )
        resp = {"message": msg, "email_sent": sent}
        if app.debug:
            resp["debug_otp"] = code
        return jsonify(resp)

    @app.route("/api/register", methods=["POST"])
    def api_register():
        data = request.get_json(silent=True) or {}
        name = (data.get("name") or "").strip()
        email = (data.get("email") or "").strip().lower()
        password = (data.get("password") or "").strip()
        specialization = (data.get("specialization") or "").strip()
        hospital_name = (data.get("hospital_name") or "").strip()
        hospital_address = (data.get("hospital_address") or "").strip()
        otp = (data.get("otp") or "").strip()
        if not all([name, email, password, specialization, hospital_name, hospital_address, otp]):
            return jsonify({"error": "All fields including OTP are required."}), 400
        if "@" not in email:
            return jsonify({"error": "Invalid email."}), 400
        if len(password) < 4:
            return jsonify({"error": "Password must be at least 4 characters."}), 400
        if not verify_doctor_otp(email, otp):
            return jsonify({"error": "Invalid or expired OTP. Request a new code."}), 400
        with get_connection() as conn:
            cur = conn.cursor(dictionary=True)
            cur.execute("SELECT id FROM doctors WHERE email = %s", (email,))
            if cur.fetchone():
                return jsonify({"error": "Email already registered."}), 400
            try:
                cur.execute(
                    "INSERT INTO doctors (name, email, password_hash, specialization, "
                    "hospital_name, hospital_address) VALUES (%s, %s, %s, %s, %s, %s)",
                    (
                        name,
                        email,
                        hash_password(password),
                        specialization,
                        hospital_name,
                        hospital_address,
                    ),
                )
                conn.commit()
            except Exception:
                return jsonify({"error": "Could not create account."}), 400
            cur.execute(
                "SELECT id, name, email, specialization FROM doctors WHERE email = %s",
                (email,),
            )
            doctor = dict(cur.fetchone())
        return jsonify({"doctor": doctor})

    @app.route("/api/login", methods=["POST"])
    def api_login():
        data = request.get_json(silent=True) or {}
        email = (data.get("email") or "").strip().lower()
        password = (data.get("password") or "").strip()

        if not email or not password:
            return jsonify({"error": "Email and password are required."}), 400

        with get_connection() as conn:
            cur = conn.cursor(dictionary=True)
            cur.execute(
                "SELECT id, name, email, specialization, password_hash FROM doctors WHERE email = %s",
                (email,),
            )
            row = cur.fetchone()

            if not row or row["password_hash"] != hash_password(password):
                return jsonify({"error": "Invalid credentials."}), 401

            session["doctor_id"] = row["id"]
            doctor = {
                "id": row["id"],
                "name": row["name"],
                "email": row["email"],
                "specialization": row["specialization"],
            }

        return jsonify({"doctor": doctor})

    @app.route("/api/logout", methods=["POST"])
    def api_logout():
        session.pop("doctor_id", None)
        return jsonify({"ok": True})

    @app.route("/api/me")
    def api_me():
        doctor = get_current_doctor()
        if not doctor:
            return jsonify({"error": "Not authenticated."}), 401
        return jsonify({"doctor": doctor})

    @app.route("/api/appointments", methods=["GET"])
    def api_appointments():
        doctor = get_current_doctor()
        if not doctor:
            return jsonify({"error": "Not authenticated."}), 401
        appts = list_doctor_appointments(doctor["id"])
        return jsonify({"appointments": appts})

    @app.route("/api/appointments/<int:appointment_id>/status", methods=["POST"])
    def api_set_appointment_status(appointment_id: int):
        doctor = get_current_doctor()
        if not doctor:
            return jsonify({"error": "Not authenticated."}), 401

        data = request.get_json(silent=True) or {}
        action = (data.get("action") or "").strip().lower()
        if action not in ("accept", "reject"):
            return jsonify({"error": "Invalid action. Use accept or reject."}), 400

        new_status = "accepted" if action == "accept" else "rejected"
        updated = set_appointment_status(
            appointment_id=appointment_id,
            doctor_id=doctor["id"],
            new_status=new_status,
        )
        if not updated:
            return jsonify({"error": "Appointment not found."}), 404
        if updated.get("_forbidden"):
            return jsonify({"error": "Forbidden."}), 403
        return jsonify({"appointment": updated})

    return app


if __name__ == "__main__":
    app = create_app()
    # Run on a different port than the patient app; bind all interfaces so mobile devices on LAN can connect.
    app.run(host="0.0.0.0", debug=True, port=5001)

