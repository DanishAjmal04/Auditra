# Auditra ML pipeline

Trains and evaluates the anomaly-detection model on a large activity-log dataset, then exports a small model
file that the Auditra backend loads. Read `ML_TEAM_GUIDE.md` first; this file is only the quick reference.

## One-time setup (Windows PowerShell)
    cd ml_pipeline
    python -m venv venv
    .\venv\Scripts\activate
    python -m pip install -r requirements.txt

## Run order
| Step | Command | What it does | Time |
|---|---|---|---|
| 0 (practice only) | `python 00_make_synthetic_data.py` | writes a small fake dataset into data\raw | 20 s |
| 1 | `python 01_inspect_dataset.py` | profiles the dataset, checks column names | 1-10 min |
| 2 | `python 02_build_features.py` | raw files -> work\features_daily.csv | 5 min - 1 h |
| 3 | `python 03_train_evaluate.py` | compares models, writes work\evaluation\* | 1-15 min |
| 4 | `python 04_export_model.py` | saves artifacts\anomaly_v1\ for the backend | seconds |
| 5 | `python 05_make_replay.py --post http://127.0.0.1:8000/api/ingest/` | replays real insider behaviour into Auditra | 1 min |
| test | `python test_pipeline.py` | 27 automatic checks | 30 s |

## Paths
Defaults live in `config.py`. Override with environment variables when the data is on another drive:
    $env:AUDITRA_DATA_DIR = "D:\datasets\insider"
    $env:AUDITRA_WORK_DIR = "D:\auditra_work"

## Files
config.py (all dataset-specific settings) | features_dataset.py (chunked feature builder) |
scorer.py (scoring core, also used by the backend) | modeling.py (models + metrics) |
auditra_features.py + replay.py (Auditra-side features and the dataset->Auditra event mapping)
