from __future__ import annotations
from flask import Flask, request, jsonify, session

import sys
import os
import hashlib, sqlite3, os
# Add project root to Python path
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from pathlib import Path
from typing import Optional, Dict, Any

from flask import Flask, jsonify, request, session, send_from_directory
import requests

from database.db import init_db, get_connection, hash_password
from backend.otp_service import store_patient_otp, verify_patient_otp
from backend.disease_logic import list_diseases, get_disease_details, list_doctors
from backend.appointment_handler import (
    create_appointment,
    list_user_appointments,
)

BASE_DIR = Path(__file__).resolve().parent.parent

# External AI API endpoint (OpenAI Chat Completions)
from openai import OpenAI

OPENAI_API_KEY = "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"

client = OpenAI(
    api_key=OPENAI_API_KEY,
    base_url="https://api.groq.com/openai/v1"
)
def create_app() -> Flask:
    app = Flask(
        __name__,
        static_folder=str(BASE_DIR / "frontend"),
        static_url_path="/static",
    )
    app.secret_key = "dev-secret-key-change-me"  # for demo only
    # Use a separate cookie name from the doctor app so logins don't conflict
    app.config["SESSION_COOKIE_NAME"] = "patient_session"

    # Ensure DB exists
    init_db()

    # ---- Helpers ----

    def get_current_user() -> Optional[Dict[str, Any]]:
        user_id = session.get("user_id")
        if not user_id:
            return None
        with get_connection() as conn:
            cur = conn.cursor(dictionary=True)
            cur.execute(
                    "SELECT id, name, email, phone FROM users WHERE id = %s",
                (user_id,),
            )
            row = cur.fetchone()
            return dict(row) if row else None

    # ---- Routes ----

    @app.route("/")
    def index():
        # serve the chatbot UI
        return send_from_directory(str(BASE_DIR / "frontend"), "index.html")

    @app.route("/api/otp/patient/send", methods=["POST"])
    def api_otp_patient_send():
        data = request.get_json(silent=True) or {}
        phone = (data.get("phone") or "").strip()
        if not phone.isdigit() or len(phone) < 10:
            return jsonify({"error": "Enter a valid 10-digit mobile number."}), 400
        with get_connection() as conn:
            cur = conn.cursor(dictionary=True)
            cur.execute("SELECT id FROM users WHERE phone = %s", (phone,))
            if cur.fetchone():
                return jsonify({"error": "This mobile number is already registered."}), 400
        code = store_patient_otp(phone)
        # Demo: log OTP (replace with SMS gateway in production)
        print(f"[Patient OTP] phone={phone} code={code}")
        resp = {"message": "OTP sent. Enter the code below to complete registration."}
        if app.debug:
            resp["debug_otp"] = code
        return jsonify(resp)

    @app.route("/api/register", methods=["POST"])
    def api_register():
        data = request.get_json(silent=True) or {}
        name = (data.get("name") or "").strip()
        phone = (data.get("phone") or "").strip()
        password = (data.get("password") or "").strip()
        otp = (data.get("otp") or "").strip()
        if not name or not phone or not password or not otp:
            return jsonify({"error": "Name, mobile, password, and OTP are required."}), 400
        if not phone.isdigit() or len(phone) < 10:
            return jsonify({"error": "Enter a valid mobile number."}), 400
        if len(password) < 4:
            return jsonify({"error": "Password must be at least 4 characters."}), 400
        if not verify_patient_otp(phone, otp):
            return jsonify({"error": "Invalid or expired OTP. Request a new code."}), 400

        with get_connection() as conn:
            cur = conn.cursor(dictionary=True)
            try:
                cur.execute(
                    "INSERT INTO users (name, email, phone, password_hash) VALUES (%s, %s, %s, %s)",
                    (name, f"user_{phone}@example.com", phone, hash_password(password)),
                )

                conn.commit()
            except Exception:
                return jsonify({"error": "Mobile number already registered."}), 400

            cur.execute(
                "SELECT id, name, email, phone FROM users WHERE phone = %s",
                (phone,),
            )
            user = dict(cur.fetchone())
        return jsonify({"user": user})

    @app.route("/api/login", methods=["POST"])
    def api_login():
        data = request.get_json(silent=True) or {}
        phone = (data.get("phone") or "").strip()
        password = (data.get("password") or "").strip()

        if not phone or not password:
            return jsonify({"error": "Mobile number and password are required."}), 400

        with get_connection() as conn:
            cur = conn.cursor(dictionary=True)
            cur.execute(
                "SELECT id, name, email, phone, password_hash FROM users WHERE phone = %s",
                (phone,),
            )
            row = cur.fetchone()

            if not row or row["password_hash"] != hash_password(password):
                return jsonify({"error": "Invalid credentials."}), 401

            session["user_id"] = row["id"]
            user = {
                "id": row["id"],
                "name": row["name"],
                "email": row["email"],
                "phone": row["phone"],
            }

        return jsonify({"user": user})

    @app.route("/api/logout", methods=["POST"])
    def api_logout():
        session.clear()
        return jsonify({"ok": True})

    @app.route("/api/me")
    def api_me():
        user = get_current_user()
        if not user:
            return jsonify({"error": "Not authenticated."}), 401
        return jsonify({"user": user})

    @app.route("/api/meta")
    def api_meta():
        user = get_current_user()
        if not user:
            return jsonify({"error": "Not authenticated."}), 401
        return jsonify(
            {
                "user": user,
                "diseases": list_diseases(),
                "doctors": list_doctors(),
            }
        )

    @app.route("/api/disease_info")
    def api_disease_info():
        user = get_current_user()
        if not user:
            return jsonify({"error": "Not authenticated."}), 401
        try:
            disease_id = int(request.args.get("disease_id", "0"))
        except ValueError:
            return jsonify({"error": "Invalid disease id."}), 400
        details = get_disease_details(disease_id)
        if not details:
            return jsonify({"error": "Disease not found."}), 404
        return jsonify(details)

    @app.route("/api/healthbot_query", methods=["POST"])
    def api_healthbot_query():

        user = get_current_user()
        if not user:
            return jsonify({"error": "Not authenticated."}), 401

        data = request.get_json(silent=True) or {}
        query = data.get("query", "").strip()

        if not query:
            return jsonify({"error": "Query is required."}), 400

        try:

            response = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are HealthAssist, an AI healthcare assistant. "
                            "Provide general health information and possible causes of symptoms. "
                            "Always recommend consulting a doctor."
                        )
                    },
                    {
                        "role": "user",
                        "content": query
                    }
                ],
                temperature=0.3
            )

            answer = response.choices[0].message.content

            return jsonify({"answer": answer})

        except Exception as e:

            print("OPENAI ERROR:", e)

            return jsonify({
                "answer": "AI service temporarily unavailable."
            })
    @app.route("/api/appointments", methods=["POST", "GET"])
    def api_appointments():
        user = get_current_user()
        if not user:
            return jsonify({"error": "Not authenticated."}), 401
        if request.method == "GET":
            appts = list_user_appointments(user["id"])
            return jsonify({"appointments": appts})

        data = request.get_json(silent=True) or {}
        try:
            disease_id = int(data.get("disease_id"))
            doctor_id = int(data.get("doctor_id"))
        except (TypeError, ValueError):
            return jsonify({"error": "Invalid doctor or disease."}), 400
        date = (data.get("date") or "").strip()
        time = (data.get("time") or "").strip()
        if not date or not time:
            return jsonify({"error": "Date and time are required."}), 400
        appointment = create_appointment(
            user_id=user["id"],
            doctor_id=doctor_id,
            disease_id=disease_id,
            date_str=date,
            time_str=time,
        )
        return jsonify({"appointment": appointment})

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=True)

