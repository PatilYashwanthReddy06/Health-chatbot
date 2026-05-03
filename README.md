## HealthBot – Disease Selection Based Healthcare Chatbot with Doctor Appointment System

### Overview

HealthBot is a simple end‑to‑end demo of a healthcare chatbot and a doctor‑side appointment management system sharing a single SQLite database.

- **HealthBot (patient side)**: Web UI (HTML/CSS + Flask backend) where users can register/login, select diseases from dropdowns, view medicines, cure steps, precautions, and book appointments.
- **Doctor App (doctor side)**: Tkinter desktop UI where doctors can log in, see pending appointments, and accept/reject them. Status changes are reflected back in HealthBot.

> **Disclaimer:** This application does not provide medical diagnosis. Please consult a certified doctor before taking any medication.

---

### Tech Stack

- **Backend**: Python 3.x, Flask
- **Frontend**: HTML, CSS (simple responsive layout)
- **Doctor App**: Python Tkinter
- **Database**: SQLite (shared `healthbot.db`)

---

### Project Structure

```text
HealthBot/
├── backend/
│   ├── app.py
│   ├── disease_logic.py
│   ├── appointment_handler.py
├── doctor_app/
│   ├── doctor_ui.py
│   ├── appointment_manager.py
├── database/
│   ├── db.py
│   ├── schema.sql
│   ├── healthbot.db  (created automatically on first run)
├── datasets/
│   ├── diseases.csv
│   ├── medicines.csv
├── frontend/
│   ├── index.html
│   ├── style.css
│   ├── logo.svg   (placeholder logo, you can replace with your own PNG)
├── requirements.txt
└── README.md
```

---

### Setup Instructions

1. **Create and activate a virtual environment (recommended)**

```bash
cd "d:\projects\csp project\second try ai chatbot(wui)"
python -m venv venv
venv\Scripts\activate
```

2. **Install dependencies**

```bash
pip install -r requirements.txt
```

3. **Initialize the database**

The first run of either `backend/app.py` or `doctor_app/doctor_ui.py` will automatically create `healthbot.db` using `database/schema.sql` and seed some sample data (users, doctors, diseases, medicines, cure steps).

You can also initialize manually:

```bash
python -m database.db
```

---

### Running the HealthBot (Patient Web App)

From the project root:

```bash
venv\Scripts\activate
python backend/app.py
```

Then open a browser and go to:

```text
http://127.0.0.1:5000/
```

**Default sample user credentials:**

- **Email**: `user1@example.com`
- **Password**: `password123`

You can also register a new user from the login page.

---

### Running the Doctor Application (Tkinter)

From the project root:

```bash
venv\Scripts\activate
python doctor_app/doctor_ui.py
```

**Default sample doctor credentials:**

- **Email**: `drsmith@example.com`
- **Password**: `docpass`

---

### Key Features

- **User Registration & Login**
  - Stored securely in `users` table (passwords hashed with SHA-256 for demo purposes only).

- **Disease & Symptom Selection (No Free Text)**
  - Users choose from dropdowns; the backend looks up disease info from `diseases`, `medicines`, and `cure_steps`.

- **Chatbot‑style Conversation**
  - The web UI renders responses as chat bubbles, including:
    - Disease description
    - Common medicines
    - Cure/management steps
    - Precautions and lifestyle tips
  - A mandatory disclaimer is always shown.

- **Appointment Booking**
  - User selects doctor/specialization and preferred date/time.
  - Appointment stored in `appointments` table with status:
    - `pending`, `accepted`, or `rejected`.

- **Doctor Dashboard**
  - Doctors log in via Tkinter UI.
  - View pending and all appointments with:
    - Patient name
    - Selected disease
    - Requested date & time
  - Accept or reject appointments; status is updated in the shared DB and visible to the user via HealthBot.

---

### Database Schema (High‑Level)

- **users**: `id`, `name`, `email`, `password_hash`
- **doctors**: `id`, `name`, `email`, `password_hash`, `specialization`
- **diseases**: `id`, `name`, `description`, `precautions`
- **medicines**: `id`, `disease_id`, `medicine_name`, `dosage`
- **cure_steps**: `id`, `disease_id`, `step_order`, `step_text`
- **appointments**: `id`, `user_id`, `doctor_id`, `disease_id`, `appointment_date`, `appointment_time`, `status`, `created_at`

---

### Notes & Customization

- **Logo/Icon**: A simple `logo.svg` is provided. Replace it with your own PNG or SVG (and update `index.html` if you change the filename).
- **Medical Content**: The included diseases/medicines/steps are simplistic demo data. Replace with vetted content for any serious use.
- **Security**: This project is for educational/demo purposes and is **not** production‑ready (e.g., no HTTPS, advanced auth, or RBAC).

---

### Mandatory Disclaimer

> **This application does not provide medical diagnosis. Please consult a certified doctor before taking any medication.**

