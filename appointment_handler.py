from typing import Dict, Any, List
from datetime import datetime

from database.db import get_connection


def create_appointment(
    user_id: int,
    doctor_id: int,
    disease_id: int,
    date_str: str,
    time_str: str,
) -> Dict[str, Any]:
    created_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    with get_connection() as conn:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            "INSERT INTO appointments "
            "(user_id, doctor_id, disease_id, appointment_date, appointment_time, status, created_at) "
            "VALUES (%s, %s, %s, %s, %s, 'pending', %s)",
            (user_id, doctor_id, disease_id, date_str, time_str, created_at),
        )
        appt_id = cur.lastrowid
        conn.commit()
        cur.execute("SELECT * FROM appointments WHERE id = %s", (appt_id,))
        row = cur.fetchone()

        if not row:
            return {}

        # Convert non-JSON types
        if row.get("appointment_date"):
            row["appointment_date"] = str(row["appointment_date"])

        if row.get("appointment_time"):
            row["appointment_time"] = str(row["appointment_time"])

        if row.get("created_at"):
            row["created_at"] = str(row["created_at"])

        return row



def list_user_appointments(user_id: int) -> List[Dict[str, Any]]:
    with get_connection() as conn:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            "SELECT a.*, d.name as doctor_name, ds.name as disease_name "
            "FROM appointments a "
            "JOIN doctors d ON a.doctor_id = d.id "
            "JOIN diseases ds ON a.disease_id = ds.id "
            "WHERE a.user_id = %s "
            "ORDER BY a.created_at DESC",
            (user_id,),
        )
        rows = cur.fetchall()

        for row in rows:
            if row.get("appointment_date"):
                row["appointment_date"] = str(row["appointment_date"])
            if row.get("appointment_time"):
                row["appointment_time"] = str(row["appointment_time"])
            if row.get("created_at"):
                row["created_at"] = str(row["created_at"])

        return rows


def list_doctor_appointments(doctor_id: int) -> List[Dict[str, Any]]:
    with get_connection() as conn:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            "SELECT a.*, u.name AS user_name, u.email AS user_email, ds.name AS disease_name "
            "FROM appointments a "
            "JOIN users u ON a.user_id = u.id "
            "JOIN diseases ds ON a.disease_id = ds.id "
            "WHERE a.doctor_id = %s "
            "ORDER BY a.created_at DESC",
            (doctor_id,),
        )
        rows = cur.fetchall()

        for row in rows:
            if row.get("appointment_date"):
                row["appointment_date"] = str(row["appointment_date"])
            if row.get("appointment_time"):
                row["appointment_time"] = str(row["appointment_time"])
            if row.get("created_at"):
                row["created_at"] = str(row["created_at"])

        return rows


def set_appointment_status(
    appointment_id: int,
    doctor_id: int,
    new_status: str,
) -> Dict[str, Any]:
    if new_status not in ("accepted", "rejected", "pending"):
        raise ValueError("Invalid status")
    with get_connection() as conn:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            "SELECT id, doctor_id FROM appointments WHERE id = %s",
            (appointment_id,),
        )
        row = cur.fetchone()
        if not row:
            return {}
        if int(row["doctor_id"]) != int(doctor_id):
            return {"_forbidden": True}

        cur.execute(
            "UPDATE appointments SET status = %s WHERE id = %s",
            (new_status, appointment_id),
        )
        conn.commit()

        cur.execute(
            "SELECT a.*, u.name AS user_name, u.email AS user_email, ds.name AS disease_name "
            "FROM appointments a "
            "JOIN users u ON a.user_id = u.id "
            "JOIN diseases ds ON a.disease_id = ds.id "
            "WHERE a.id = %s",
            (appointment_id,),
        )
        updated = cur.fetchone()

        if not updated:
            return {}

        if updated.get("appointment_date"):
            updated["appointment_date"] = str(updated["appointment_date"])
        if updated.get("appointment_time"):
            updated["appointment_time"] = str(updated["appointment_time"])
        if updated.get("created_at"):
            updated["created_at"] = str(updated["created_at"])

        return updated