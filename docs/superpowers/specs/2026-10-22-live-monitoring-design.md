# Auditra live monitoring: design

Date: 2026-10-22. Status: approved in chat, full scope of `Auditra_GDPR_Violation_Mapping.xlsx`.

## Goal

The FYP demo runs on two laptops. The employee laptop runs the Windows agent. The officer laptop opens the dashboard in a browser. Every row on screen comes from something that really happened on the employee laptop. There are no seeded logs, no simulated events and no mock scenes. The officer sees each potential violation within seconds, along with the GDPR articles, how the score was built, the evidence and actions to take.

Everything is labelled a *potential violation* or *risk indicator*, as the workbook's Legend requires.

## Topology

- Laptop B (this laptop, `E:\Auditra`) runs Postgres, Django (`0.0.0.0:8000`) and the Vite frontend (`--host`). It is also the monitored employee machine, running `agent.py` as Administrator. The employee uses a local standard account (`bilal`).
- Laptop A (officer) only needs a browser at `http://<laptop-B-ip>:5173`.
- Both laptops join a phone hotspot. `setup_server_firewall.ps1` opens ports 8000 and 5173.
- Railway and Vercel are optional. Every URL comes from an environment variable (`VITE_API_URL`, `AUDITRA_URL`, `ALLOWED_HOSTS`, `DATABASE_URL`).

## What is configuration and what is activity

Configuration is entered through the Admin and Officer screens. It is not mock data:
- employees and their Windows accounts
- the resource catalogue and data subjects
- consent, requests, breaches, the RoPA and the DPO record
- rules

The rule catalogue is created by a data migration because it is the system's policy.

Activity reaches the database only from the agent, or from the automated-decision ingest API for business systems.

`seed`, `load_anomaly_demo`, `load_case`, `stream_incident`, `log_generator.py`, the `demo/` fixture and the Simulate endpoint are deleted.

## Data model (migration 0006 onwards)

Removed: `Log`, `Violation`.

Changed:
- `ConsentRecord` gets a FK to `DataSubject`, plus `status` GIVEN/WITHDRAWN and timestamps.
- `DataSubjectRequest` gets a FK to `DataSubject`, the `DENIED` status, `completed_at` and `exemption_note`.
- `BreachRecord` gets a nullable FK to `Incident`, plus title, `high_risk`, `authority_notified_at` and `subjects_notified_at`.

New:
- `Employee`: name, code, department, role, type (STAFF/VENDOR), status (ACTIVE/LEFT), shift start and end, work days, `max_sensitivity`, `allowed_categories`.
- `EmployeeAccount`: Windows account to employee, for example `MACBOOK\bilal`.
- `Agent`: hostname, token, `last_seen`, `ip`, `is_admin`, version.
- `DataSubject`: name, reference, `path_prefix`.
- `CatalogueEntry`: `path_prefix`, category, sensitivity, processing activity, `retention_days`, owner department.
  - Categories: GENERAL, FINANCIAL, HR_EMPLOYEE, HEALTH, BIOMETRIC, CRIMINAL, NATIONAL_ID, CUSTOMER.
- `Event`: one clean, structured activity row.
  - type, `occurred_at` (aware, local offset kept), machine, account, employee, path, file name, process, domain, device, `logon_type`, details JSON, catalogue entry, data subject, `outside_shift`, `source_event_id`, and a unique `dedupe_key`.
- `Incident`:
  - kind: VIOLATION, INDICATOR or ANOMALY
  - rule, employee, account, machine, articles (JSON), title, summary
  - severity, score, `score_breakdown` (JSON list of `{label, points}`)
  - `ai_score`, `ai_reason`, status, evidence events (M2M), `dedupe_key`
- `IncidentAction`: actor, action, note, time.
- `AutomatedDecision`: system, subject reference, decision, significant, made at, reviewed by and reviewed at.
- `AuditEntry`: an admin or officer configuration change.
- `Rule` gets `code` (unique), `title`, `kind` and `articles`.

## Agent v2 (`backend/compliance/agent.py`)

- Every Security, Plug and Play and PrintService read uses `EvtQuery` with an EventID XPath filter, and reads named `Data[@Name=...]` fields. `ReadEventLog`/`StringInserts` is not used.
- `occurred_at` is sent with its UTC offset.
- Events collected:
  - 4624: types 2, 7, 10 and 11 only. Type 7 becomes UNLOCK. Machine accounts (`$`), SYSTEM, DWM-* and UMFD-* are dropped.
  - 4625 (LOGON_FAILED), 4720, 4732, 4740, 1102, 4719, 4698. For 4698, system-created tasks are dropped.
  - 4663 on catalogue paths. The access mask maps to READ, WRITE or DELETE. Indexer, Defender, Explorer and dllhost processes are dropped, along with temp, `~$` and `desktop.ini` files. Repeats of the same account, path and type within 60 s are dropped.
  - PnP 410 USBSTOR (USB_CONNECTED).
  - PrintService 307 (PRINT).
- A USB file watcher (`watchdog`) watches removable drives. A new file is matched by name and size against an index of the catalogue folders and becomes FILE_COPY_TO_USB with the source path.
- Chrome and Edge history are read for every local profile. Only visits to domains in the server's watched-domain list are sent. This minimises personal data, which is itself a GDPR point.
- The inventory scan runs every 10 minutes. It sends path, size and modified time for files in the catalogue folders, and the server checks retention.
- The console user comes from `WTSGetActiveConsoleSessionId` and `WTSQuerySessionInformation`, for USB and inventory events.
- `POST /api/agent/register/` uses the enrolment key and returns a per-machine token.
- The heartbeat runs every 10 s, and its response carries the config: catalogue paths and watched domains.
- `setup_demo_machine.ps1` (Administrator) does the following, and `undo_demo_machine.ps1` reverts it:
  - auditpol: File System, Logon, Other Logon/Logoff, User Account Management, Security Group Management, Audit Policy Change, Other Object Access
  - folder SACLs on `C:\AuditraCompany\*`
  - enables the PrintService log
  - lockout policy: 5 attempts, 5 minutes
  - creates the local user `bilal`

## Detection

`compliance/detection/` holds three kinds of rules.

- **Per-event rules**: each one returns findings. All findings for one event are merged into one incident, with the union of articles and the highest severity.
- **Window rules**: brute force, mass read, mass delete, mass USB export, many machines and shared account. Each one uses a dedupe key per account per window.
- **Workflow rules**: run every 60 s by the scheduler. They cover overdue requests (Art. 15/16/17/18/21), denied portability (20), breach 72 h (33/34), automated decisions without review (22) and retention (5(1)(e)).

The DPO check (37) runs on HIGH events. It fires at most once a day while the DPO record is not COMPLIANT.

### Coverage

| Workbook row | Rule code | Kind | Articles | Severity |
|---|---|---|---|---|
| USB connected in shift | usb_in_shift | INDICATOR | 32 | LOW |
| USB connected outside shift | usb_after_shift | VIOLATION | 32 | HIGH |
| Sensitive file copied to USB | usb_copy_sensitive | VIOLATION | 32, 5(1)(f) (+9 / +87 by category) | HIGH, CRITICAL if HIGH sensitivity or special category |
| Mass copy to USB | usb_mass_export | VIOLATION | 5, 32 | CRITICAL |
| USB lost with personal data | officer action "Report lost device", which creates a BreachRecord | breach | 33, 34 | per breach |
| Role scope | role_scope | VIOLATION | 25 | HIGH |
| Special category | special_category | VIOLATION | 9 | CRITICAL |
| Criminal data | criminal_data | VIOLATION | 10 | CRITICAL |
| National ID | national_id | VIOLATION | 87 | HIGH |
| Employee data outside HR | employee_data | VIOLATION | 88 | HIGH |
| No lawful basis | no_lawful_basis | VIOLATION | 6 | HIGH |
| Not in RoPA | not_in_ropa | VIOLATION | 30 | MEDIUM |
| Consent withdrawn | consent_withdrawn | VIOLATION | 7 | CRITICAL |
| Accessed after erasure | after_erasure | VIOLATION | 17 | HIGH |
| Restricted subject | restricted_subject | VIOLATION | 18 | MEDIUM |
| Objection ignored | objection_ignored | VIOLATION | 21 | HIGH |
| After-shift sensitive access | after_shift_sensitive | VIOLATION | 32 | HIGH |
| Vendor beyond scope | vendor_scope | VIOLATION | 29 | HIGH |
| Departed employee active | departed_employee | VIOLATION | 32 | HIGH |
| Remote logon | remote_logon | INDICATOR (VIOLATION for a vendor, Art. 29) | 32, 25 | MEDIUM |
| Brute force | brute_force | VIOLATION | 32 | HIGH |
| Many machines | many_machines | VIOLATION | 32 | HIGH |
| Shared account | shared_account | VIOLATION | 32, 5(2) | MEDIUM |
| New account | account_created | VIOLATION | 32, 25 | MEDIUM |
| Admin group add | admin_group_add | VIOLATION | 25, 32 | HIGH |
| Lockout | account_lockout | INDICATOR | 32 | MEDIUM |
| Log cleared | log_cleared | VIOLATION | 32, 5(2) | CRITICAL |
| Audit policy changed | audit_policy_changed | VIOLATION | 32, 5(2) | HIGH |
| Scheduled task | task_created | INDICATOR | 32 | MEDIUM |
| Mass read | mass_read | VIOLATION | 5, 25, 32 | HIGH |
| Mass delete | mass_delete | VIOLATION | 32, 5(1)(f) | HIGH, CRITICAL if HIGH sensitivity |
| Print sensitive | print_sensitive | INDICATOR | 32 | LOW |
| Cloud upload site | file_sharing_site | VIOLATION if sensitive access in the previous 30 min, otherwise INDICATOR | 32, 5 | MEDIUM |
| Social media | social_media | INDICATOR (policy, no article) | Policy | LOW |
| Retention | retention_exceeded | VIOLATION | 5(1)(e) | MEDIUM |
| DSR overdue | dsr_overdue | VIOLATION | 15, 16, 17, 18, 21 | per right |
| Portability denied | portability_denied | VIOLATION | 20 | MEDIUM |
| Breach 72 h | breach_not_reported | VIOLATION | 33 | CRITICAL |
| Subjects not notified | subjects_not_notified | VIOLATION | 34 | HIGH |
| Automated decision | automated_decision | VIOLATION | 22 | HIGH |
| No DPO | dpo_missing | VIOLATION | 37 | HIGH |
| Repeat offender | none: score escalation | | 83 | +points |

## Score (0 to 100, every component stored)

- Severity base: CRITICAL 70, HIGH 55, MEDIUM 35, LOW 15.
- Extra articles: +5 each beyond the first, up to +10.
- Outside the employee's shift: +10, unless the shift is already the reason for the rule.
- Special category or national ID data: +10, unless the category is already the reason.
- AI anomaly: when the employee-day score is 60 or more, add `round((ai - 60) / 40 * 15)`, up to +15.
- Art. 83 repeat: +10 when the employee has 3 or more violations in the last 7 days.
- Cap at 100. Displayed risk level: 85 or more CRITICAL, 65 or more HIGH, 40 or more MEDIUM, otherwise LOW.

## AI anomaly score

- One row per employee per local day, with the 8 COMMON features.
- Mapping:
  - LOGON and UNLOCK count as logins.
  - FILE_COPY_TO_USB counts as an export.
  - USB_CONNECTED counts as removable media.
  - "After hours" means outside the employee's shift.
- `z = (log1p(x) - median) / scale`, counting only positive deviations and clipped to 10.
  - `median` and `scale` come from the CERT r4.2 training split (`cert_baseline.json`, exported from `anomaly_v1`).
  - Once an employee has 5 or more days of history, their own median and MAD are used, with the scale floored at half the CERT scale. This matches the pipeline's personal mode.
- `deviation = sqrt(sum z^2)` and `score = 100 * (1 - exp(-deviation / 3.274))`. A deviation of 3 maps to 60, which is the alert line.
- Explanation: features with z of 2 or more, written as "after-shift events: 15 (typical 1.0)".
- An ANOMALY incident is created when the score is 60 or more and no rule incident covers the same employee in the last 30 minutes. There is one per employee-day, and its score is updated as the day continues.
- Why not the exported OCSVM: the behavioural smoke check (planned in `memory.md`) shows it saturates outside the training range. An after-hours USB copy with 3 exports scores 51.7 while a normal day scores 57.4. A score that can go down as risk goes up cannot be defended. The OCSVM evaluation stays in the report as the research result.

## API

- Agent: `register`, `heartbeat` (returns config), `events`, `inventory`. Plus `decisions/` for business systems, which uses the enrolment key.
- Live: `GET /api/live/?since=` returns new incidents and events, KPIs and agent status. The frontend polls it every 2 s.
- Officer:
  - incidents: list, detail, actions, report lost device
  - employees: list and detail with risk trend
  - events: filterable
  - GDPR records: CRUD for subjects, consent, requests, breaches, RoPA, DPO and decisions
  - reports: PDF
- Admin: users, employees and accounts, catalogue, rules on/off, agents (revoke), audit trail, unlinked accounts seen, and reset monitoring data.

## Frontend

React 19, Vite, Tailwind v4, lucide-react and recharts, in a dark security-console style. The old pages are deleted.

**Officer**
- Overview
- Incidents and incident detail: breakdown bar, evidence chain, timeline of ±30 minutes, actions
- Employees and employee detail: access matrix, risk trend
- Activity
- GDPR Records (tabs)
- Reports

**Admin**
- Users
- Employees and Accounts
- Catalogue and Data subjects
- Rules
- Agents
- Audit trail

A toast and a sound play for new HIGH and CRITICAL incidents.

## Validation

`manage.py test compliance` (SQLite in memory) replays recorded agent payloads for every rule, including a clean baseline with no false positives. A test also asserts that the AI score rises monotonically with risk. The results table goes into the report.
