# Auditra ML Task - Session Memory & State Checkpoint

> **Last Updated:** 2026-10-19 00:52 PKT  
> **Repository Path:** `D:\University\FYP\AI model\ml_pipeline_cert`  
> **Python Environment:** `D:\University\FYP\Auditra\venv\Scripts\python.exe` (Python 3.12.3)  
> **Dataset Path:** `D:\University\FYP\AI model\cert_data\r4.2` (`AUDITRA_DATA_DIR`)  
> **Backend Integration Path:** `D:\University\FYP\Auditra` (Archive in `D:\University\FYP\leftover\backend_ml_integration.zip`)  

---

## 1. Operating Rules & Constraints
1. **Strictly Protected Files:** Never edit `scorer.py` or `auditra_features.py` under any circumstances.
2. **Process Integrity:** Never interrupt, kill, or restart running Python processes unless CPU is verified idle for 10+ minutes.
3. **Background Execution:** Any command taking >2 minutes must run as a detached background process with output logged to `work\logs\<step>.log`.
4. **Time-Based Splitting Only:** Earliest 60% Train, next 15% Validation, final 25% Test. Never use random splits.
5. **No Data/Artifact Commits:** Do not commit raw data, `work/`, or `artifacts/` to version control.
6. **Model Selection Integrity:** Select models **exclusively** on validation period metrics. Read test results only once at the end and never alter model choice based on test metrics.
7. **Pipeline Boundaries:** Never touch `ml_pipeline` (LANL dataset folder). All work is confined to `ml_pipeline_cert` (CERT r4.2).

---

## 2. Completed Work Log

### Phase A: Dry Run on Synthetic Data (Completed)
- Cleaned prior directories and verified `AUDITRA_DATA_DIR` was unset.
- Ran `00_make_synthetic_data.py`: produced 19,980 logon rows, 80 users, 180 days, 7 injected insiders.
- Ran `01_inspect_dataset.py`, `02_build_features.py`: verified 9,939 user-days, 73 malicious user-days.
- Ran `03_train_evaluate.py --quick`, `04_export_model.py`, and `05_make_replay.py`.
- Ran `test_pipeline.py`: **ALL 27 CHECKS PASSED**.
- Cleared synthetic data before proceeding to Phase B.

### Phase B: Real CERT r4.2 Dataset & Feature Building (Completed)
- Set `$env:AUDITRA_DATA_DIR = "D:\University\FYP\AI model\cert_data\r4.2"`.
- Dataset Inspection (`01_inspect_dataset.py`):
  - Total raw size: 15.1 GB (`logon.csv`: 854k rows; `device.csv`: 405k rows; `file.csv`: 445k rows; `email.csv`: 2.6M rows; `http.csv`: 28.4M rows).
  - Schema fix: Raw `device.csv` lacks `file_tree` column; removed `file_tree` from `config.py` schema.
  - Label fix: `answers/insiders.csv` filtered strictly to `dataset == '4.2'` in `02_build_features.py`, isolating exactly 70 distinct insider users across scenarios 1, 2, and 3.
  - Memory safeguard: Free RAM is ~1.89 GB, so `02_build_features.py` was executed with `--skip-http-distinct`. This safely zeros `http_distinct_domains` in the `FULL` research set only and does not touch `COMMON` deployable features.
- **Gate 1 Metrics Reported & Confirmed:**
  - Total User-Days: `330,452` across `1,000` users.
  - Total Malicious User-Days: `1,364` (`0.413%` base rate).
  - Train (60%, 2010-01-02 to 2010-10-29): 208,167 user-days, 770 malicious days, 46 insiders.
  - Validation (15%, 2010-10-29 to 2011-01-12): 44,657 user-days, 268 malicious days, 20 insiders.
  - Test (25%, 2011-01-12 to 2011-05-17): 77,628 user-days, 326 malicious days, 17 insiders.

### Phase C: Model Training, Evaluation & Selection (Completed through Gate 4)
- **Gate 2 (Quick Run)**: Evaluated `isolation_forest` and `robust_z` in `raw` and `personal` modes on deployable `common` features.
- **Updated Selection Rule (Set 2026-10-18)**:
  - Rank strictly by **Validation PR-AUC**.
  - If candidates are within `0.002` of the top Validation PR-AUC, break the tie using **Validation Recall** at the calibrated threshold.
  - Zero test metrics are permitted in the selection decision.
- **Full Run**: Backed up quick evaluation to `work\evaluation_quick`, executed `03_train_evaluate.py --max-train-rows 100000` across all 24 configurations (2 feature sets × 3 modes × 4 models). Output saved in `work\evaluation\results.md`.
- **Seed Stability Evaluation (`work\final\seed_stability_results.json`)**:
  - Top 4 COMMON candidates evaluated across 5 random seeds (42..46):
    1. **`ocsvm / personal`**: Mean Val PR-AUC = `0.0177 ± 0.0017` | Mean Val Recall = `0.0493 ± 0.0083` (**CHAMPION**)
    2. `lof / raw`: Mean Val PR-AUC = `0.0154 ± 0.0005` | Mean Val Recall = `0.0149 ± 0.0000`
    3. `isolation_forest / personal`: Mean Val PR-AUC = `0.0137 ± 0.0003` | Mean Val Recall = `0.0522 ± 0.0062`
    4. `robust_z / personal`: Mean Val PR-AUC = `0.0136 ± 0.0000` | Mean Val Recall = `0.0149 ± 0.0000`
- **Bootstrap 95% Confidence Intervals for Champion (`ocsvm / personal`)**:
  - 1,000 user-level trajectory resamples on test period ($77,628$ user-days, $326$ malicious days):
    - **Test ROC-AUC**: `0.757` (95% CI: `[0.709, 0.802]`)
    - **Test PR-AUC**: `0.013` (95% CI: `[0.006, 0.022]`)
    - **Alerts**: 591 total (7 true positive days, 584 false alarms; `1.18%` precision / positive predictive value; budget pace of 4.69 alerts/day).
    - **Insiders Detected**: `7 / 17` (optimistic user-level count).
- **COMMON vs. FULL Quantitative Comparison**:
  - Validation PR-AUC: `0.017` (COMMON) vs `0.060` (FULL, 3.53x higher).
  - Test PR-AUC: `0.013` (COMMON) vs `0.039` (FULL, 3.00x higher).
  - Recall: `3.7%` val / `2.1%` test (COMMON) vs `7.8%` val / `5.2%` test (FULL).
  - Lift over Base: `3.67x` val / `2.86x` test (COMMON) vs `7.83x` val / `6.19x` test (FULL).
- **Backend Architecture Audit (Read-Only)**:
  - Cold-start handling: Unknown employees without historical records in `user_stats` default to population `global_median` and `global_scale`.
  - History threshold: Minimum 5 active days (`MIN_USER_DAYS = 5`) required to establish personal baseline.
  - Telemetry gap: Backend logs record local exports as `action == 'EXPORT'`, but Windows agent cannot inspect email attachments/MIME headers (`email_ext_attach` gap).

---

## 3. Current State & Immediate Next Steps (Phase D)

### Current Checkpoint
**Gate 4 is complete and fully documented. Paused before running `04_export_model.py`.**

### Next Steps When Resuming:
1. **Export Chosen Model**:
   - Run `04_export_model.py --model ocsvm --mode personal --feature-set common --name anomaly_v1`.
   - Verify artifact contents in `artifacts\anomaly_v1\` (`model.joblib` and `meta.json`).
2. **Behavioral Smoke Check**:
   - Check how the deployed model behaves when USB (`removable_media_events`) or exfiltration (`exfil_events`) counts are nonzero.
3. **Backend Integration**:
   - Ensure backend directory `D:\University\FYP\Auditra\compliance\ml\artifacts\anomaly_v1` is populated.
   - Verify that `scorer.py` in `ml_pipeline_cert` is byte-identical to `D:\University\FYP\Auditra\compliance\ml\scorer.py`.
4. **Backend Test Suite & Replay**:
   - Run backend ML tests (`python manage.py test compliance.tests_ml`).
   - Run `05_make_replay.py` to stream simulated CERT r4.2 insider logs through Auditra ingest endpoint.
5. **Final Viva / Report Presentation**:
   - Compile final charts (`pr_curves.png`, `roc_curves.png`, `score_distribution.png`) from `work\evaluation\`.
