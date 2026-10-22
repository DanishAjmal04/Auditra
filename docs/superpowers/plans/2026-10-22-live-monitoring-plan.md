# Auditra live monitoring: build plan

Spec: `docs/superpowers/specs/2026-10-22-live-monitoring-design.md`. Commit after every phase.

## Session 1: backend and agent

1. **Clean-up**
   - Back up the DB (`backups/`, gitignored).
   - Delete the mock generators, the Simulate endpoint, `demo/` and the old views and rule engine.
   - Add the `reset_monitoring_data` command.
2. **Models**
   - Write the new models and migration 0006.
   - Write the rule-catalogue data migration.
   - Export `ml/cert_baseline.json` from `anomaly_v1`.
   - Set `TIME_ZONE='Asia/Karachi'`.
3. **Core pipeline**
   - `ingest.py`: normalise, resolve employee, catalogue and subject, set `outside_shift`, dedupe.
   - `detection/`: event, window and workflow rules.
   - `scoring.py` and `ai.py`.
   - `incidents.py`: merge, dedupe, escalate.
4. **API**
   - Agent endpoints with tokens.
   - Live feed.
   - Officer and admin endpoints; serializers.
   - Compact PDF report.
   - Scheduler thread for the workflow rules.
5. **Agent v2 and scripts**
   - `agent.py` collectors.
   - `setup_demo_machine.ps1` and `undo_demo_machine.ps1`.
   - `setup_server_firewall.ps1`.
6. **Tests**
   - Payload replays for every rule, a clean baseline, AI monotonicity, permissions and the agent token flow.
7. **First end-to-end check on this laptop**
   - Run the agent, plug in USB, open a catalogue file, check the API.

## Session 2: frontend and rehearsal

8. **Frontend rebuild**: Tailwind setup, layout, auth, live polling, every officer and admin page, toasts.
9. **Two-laptop guide**: README "Demo day" steps, configuration walkthrough and scene script.
10. **Rehearsal**: run every scene for real, fix gaps, and update the report notes (OCSVM, then the robust-z decision).
11. **Optional**: Railway and Vercel environment configuration.
