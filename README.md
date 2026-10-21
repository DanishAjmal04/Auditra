# Auditra

GDPR compliance monitor: a Django REST API, a React console, a Windows event agent, and a CERT-trained One-Class SVM that scores unusual user-days. The rule engine is the compliance detector. The model is a supporting anomaly signal.

## Prerequisites

- Python 3.12
- Node.js 20+
- PostgreSQL with database `auditra_db` and user `auditra_user` / password `auditra123`

```sql
CREATE USER auditra_user WITH PASSWORD 'auditra123';
CREATE DATABASE auditra_db OWNER auditra_user;
```

Optional: copy `.env.example` to `.env`. The defaults in `backend/auditra/settings.py` already match that file, so a local demo runs without it.

## Backend

```powershell
cd backend
python -m venv venv
.\venv\Scripts\activate
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py create_default_users
python manage.py seed
python manage.py load_anomaly_demo
python manage.py runserver
```

`scikit-learn` must stay at **1.8.0**. The saved model was exported with that version.

## Frontend

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

| User | Password | Role |
|---|---|---|
| `compliance_officer` | `Auditra@2026` | Compliance officer |
| `admin` | `Admin@2026` (from `create_default_users`) or `Auditra@2026` (if `seed` ran afterwards) | Admin |

`seed` resets the admin password to `Auditra@2026`. Use that password after seeding.

`.env` in the repo root points at database `auditra_db` with user `auditra_user` and password `auditra123`. To run the test suite without creating a Postgres test database:

```powershell
$env:DB_ENGINE = "sqlite"
$env:DB_NAME = ":memory:"
python manage.py test compliance
```

Ingest key (header `X-Auditra-Ingest-Key`): `auditra-ingest-dev-key`.

## Presentation path

1. Log in as `compliance_officer` / `Auditra@2026`.
2. Open Violations. Rows labelled `ML-ANOMALY` are the One-Class SVM (score above 60, plain-language reason). Rule rows are GDPR articles.
3. Open User Activity and pick `demo_insider` to see the anomaly percent and reason.
4. On the dashboard, run Simulate to add a rule-based hit.
5. Open Reports and download the PDF (the request sends the access token).
6. Log in as `admin` / `Auditra@2026`. Toggle a rule on Configure Rules. System Health shows the last compliance cycle.
7. Optional live collection. An ordinary prompt still sends System and Application logs. An Administrator prompt is required for the Security log (logons, and event 6416 as `removable_media`). The agent does not invent file-export days, so the model demo remains `load_anomaly_demo`.

```powershell
cd backend
$env:AUDITRA_INGEST_KEY = "auditra-ingest-dev-key"
python -m compliance.agent
```

A Windows account such as `MACHINE\ataur` is staff. HIGH data for that account is an Art. 25 hit. Rule scores are fixed: critical 0.95, high 0.75, medium 0.50, low 0.25. Anomaly rows keep the model score.

What to say: the rules catch known GDPR patterns. The One-Class SVM, trained on CERT insider-threat data and selected by a fixed validation rule among four candidates, scores each user-day from 0 to 100 and alerts above 60. The Windows agent collects logs. The committed demo fixture is what makes the model visible without the full CERT dataset.

## Useful commands

```powershell
python manage.py run_compliance_cycle --trigger manual
python manage.py load_anomaly_demo
python manage.py test compliance
```

CERT replay (only if `ml_pipeline_cert` has the dataset) can post to ingest with the same key:

```powershell
python 05_make_replay.py --post http://127.0.0.1:8000/api/ingest/
```

Set header support in that script only if you extend it; the management command `load_anomaly_demo` is the supported presentation feed.
