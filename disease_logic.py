from typing import List, Dict, Any

from database.db import get_connection


def list_diseases() -> List[Dict[str, Any]]:
    with get_connection() as conn:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            "SELECT id, name FROM diseases ORDER BY name"
        )
        return [dict(row) for row in cur.fetchall()]


def get_disease_details(disease_id: int) -> Dict[str, Any]:
    with get_connection() as conn:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM diseases WHERE id = %s", (disease_id,))
        disease = cur.fetchone()
        if not disease:
            return {}
        cur.execute(
            "SELECT medicine_name, dosage FROM medicines WHERE disease_id = %s",
            (disease_id,),
        )
        medicines = [dict(row) for row in cur.fetchall()]
        cur.execute(
            "SELECT step_order, step_text FROM cure_steps "
            "WHERE disease_id = %s ORDER BY step_order ASC",
            (disease_id,),
        )
        steps = [dict(row) for row in cur.fetchall()]
        return {
            "disease": dict(disease),
            "medicines": medicines,
            "cure_steps": steps,
        }


def list_doctors() -> List[Dict[str, Any]]:
    with get_connection() as conn:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            "SELECT id, name, specialization, hospital_name, hospital_address "
            "FROM doctors ORDER BY name"
        )
        doctors = [dict(r) for r in cur.fetchall()]

        # Attach disease ids each doctor handles (used by UI filtering)
        cur.execute("SELECT doctor_id, disease_id FROM doctor_diseases")
        mapping_rows = cur.fetchall()
        disease_ids_by_doctor = {}
        for r in mapping_rows:
            disease_ids_by_doctor.setdefault(r["doctor_id"], []).append(r["disease_id"])

        for doc in doctors:
            doc["disease_ids"] = disease_ids_by_doctor.get(doc["id"], [])

        return doctors


