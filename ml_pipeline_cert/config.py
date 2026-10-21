"""Central configuration for the Auditra ML pipeline.

EVERYTHING that depends on the dataset you downloaded lives in this file (file names, column names,
date format, company e-mail domain, URL keyword lists). If your dataset differs from the CERT-style
layout assumed here, change SCHEMA below after running 01_inspect_dataset.py. Nothing else should need
editing.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# ── paths (override with environment variables if the dataset lives on another drive) ──
import os
DATA_DIR = Path(os.environ.get('AUDITRA_DATA_DIR', ROOT / 'data' / 'raw'))             # raw dataset files
WORK_DIR = Path(os.environ.get('AUDITRA_WORK_DIR', ROOT / 'work'))                     # intermediate outputs
ARTIFACT_DIR = Path(os.environ.get('AUDITRA_ARTIFACT_DIR', ROOT / 'artifacts'))        # trained models
FEATURES_CSV = WORK_DIR / 'features_daily.csv'
LABELS_CSV = WORK_DIR / 'labels_daily.csv'
REPORT_DIR = WORK_DIR / 'evaluation'

# ── reading big files: rows per chunk. 200_000 rows is roughly 50-150 MB of RAM per chunk. ──
CHUNK_ROWS = 200_000

# ── same working-hours rule as Auditra's backend: outside hours when hour < 8 or hour > 18 ──
WORK_START_HOUR = 8
WORK_END_HOUR = 18

# ── dataset schema (CERT insider-threat style). VERIFY with 01_inspect_dataset.py ──
DATE_FORMAT = '%m/%d/%Y %H:%M:%S'          # e.g. 01/04/2010 07:12:00
COMPANY_DOMAIN = '@dtaa.com'               # e-mail addresses ending with this are "internal"
SCHEMA = {
    'logon':  {'file': 'logon.csv',  'cols': ['id', 'date', 'user', 'pc', 'activity']},
    'device': {'file': 'device.csv', 'cols': ['id', 'date', 'user', 'pc', 'activity']},
    'file':   {'file': 'file.csv',   'cols': ['id', 'date', 'user', 'pc', 'filename', 'content']},
    'email':  {'file': 'email.csv',  'cols': ['id', 'date', 'user', 'pc', 'to', 'cc', 'bcc', 'from', 'size',
                                              'attachments', 'content']},
    'http':   {'file': 'http.csv',   'cols': ['id', 'date', 'user', 'pc', 'url', 'content']},
}
# Columns that are huge free text and never needed: skipped at read time to save memory.
SKIP_COLUMNS = {'content', 'file_tree'}
INSIDERS_FILE = 'answers/insiders.csv'     # columns: dataset, scenario, details, user, start, end
INSIDERS_DATE_FORMAT = '%m/%d/%Y %H:%M:%S'

# Values of the 'activity' column
LOGON_VALUE, LOGOFF_VALUE = 'Logon', 'Logoff'
DEVICE_CONNECT_VALUE = 'Connect'

# URL keyword lists for the HTTP features (extend freely)
JOB_SITES = ['monster.com', 'indeed.com', 'careerbuilder.com', 'simplyhired.com', 'jobhuntersbible.com',
             'linkedin.com', 'craigslist.org']
LEAK_SITES = ['wikileaks.org', 'pastebin.com']
CLOUD_STORAGE = ['dropbox.com', 'drive.google.com', 'box.com', 'mega.nz', 'wetransfer.com']

# ── feature groups ──
# FULL = everything this dataset offers (used for research / ablation).
FULL_FEATURES = [
    'logon_count', 'logoff_count', 'logon_after_hours', 'logon_weekend', 'distinct_pcs',
    'first_logon_hour', 'last_logoff_hour',
    'usb_connects', 'usb_after_hours',
    'file_events', 'file_exe', 'file_after_hours',
    'emails_sent', 'emails_external', 'email_attachments', 'email_ext_attach', 'email_size_mb',
    'email_after_hours',
    'http_events', 'http_distinct_domains', 'http_jobsite', 'http_leaksite', 'http_cloud', 'http_after_hours',
    'after_hours_events', 'activity_events',
]
# COMMON = the subset Auditra can compute from its own Log table. THIS is what gets deployed.
# It must be computed identically from the dataset (features_from_dataset) and from Auditra events
# (auditra_features.py). The round-trip test in test_pipeline.py proves they match.
COMMON_FEATURES = [
    'activity_events',        # every logon, logoff, USB connect, file copy, e-mail sent
    'login_events',           # logons
    'logins_after_hours',     # logons outside 08:00-18:00
    'logins_weekend',         # logons on Saturday/Sunday
    'distinct_hosts',         # distinct PCs logged on to
    'after_hours_events',     # any event outside 08:00-18:00
    'exfil_events',           # file copies + e-mails with attachments to external recipients
    'removable_media_events', # USB connects
]

REMOVABLE_RESOURCE_NAME = 'removable_media'   # resource name used for USB events in Auditra's Log

# ── training ──
RANDOM_STATE = 42
TRAIN_FRACTION = 0.60       # earliest 60% of the date range
VALID_FRACTION = 0.15       # next 15%; the last 25% is the untouched TEST period
ALERT_RATE = 0.01           # alert budget: flag the 1% most unusual user-days
UNUSUAL_PCT = 60            # Auditra shows "Unusual" above this anomaly percentage (reports/config.py)
OCSVM_MAX_ROWS = 20_000     # One-Class SVM is O(n^2): train on a random sample of at most this many rows
