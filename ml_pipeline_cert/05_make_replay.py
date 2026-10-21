"""STEP 5 (demo tool): turn a slice of the REAL dataset into Auditra log events and optionally stream them in.

    # 1. build the replay file: every insider active in the test period + 3 ordinary users
    python 05_make_replay.py

    # 2. same, and send it to a running Auditra backend, 500 events per request
    python 05_make_replay.py --post http://127.0.0.1:8000/api/ingest/

Why this exists: the model was trained on dataset behaviour, so the most convincing live demo is to replay
that behaviour (including a malicious insider) through Auditra's real ingest endpoint and show the alert
appear. Timestamps are shifted by a whole number of weeks so the replay ends today (weekdays preserved);
otherwise 2010 data would never show up in 'last 30 days' reports.

Output: work/replay/replay_events.jsonl and work/replay/replay_summary.json
"""
import argparse
import json
import math
import os
import time
import urllib.request
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd

import config
import features_dataset
import modeling
import replay


def pick_users(args, df, masks):
    test = df[masks[2]]
    insiders = sorted(test.loc[test['label'] == 1, 'user'].unique())
    normal = sorted(set(test['user']) - set(insiders))
    rng = np.random.default_rng(config.RANDOM_STATE)
    extra = list(rng.choice(normal, size=min(args.normal_users, len(normal)), replace=False)) if normal else []
    users = args.users or (insiders[:args.max_insiders] + extra)
    return users, insiders


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--users', nargs='*', help='explicit user ids (default: test-period insiders + normal users)')
    ap.add_argument('--normal-users', type=int, default=3)
    ap.add_argument('--max-insiders', type=int, default=2)
    ap.add_argument('--from-day', help='YYYY-MM-DD (default: start of the test period)')
    ap.add_argument('--to-day', help='YYYY-MM-DD (default: end of the data)')
    ap.add_argument('--no-shift', action='store_true', help='keep the original (old) dates')
    ap.add_argument('--post', help='ingest URL, e.g. http://127.0.0.1:8000/api/ingest/')
    ap.add_argument('--batch', type=int, default=500)
    ap.add_argument('--delay', type=float, default=0.3, help='seconds between batches (demo pacing)')
    args = ap.parse_args()

    df = modeling.load_table()
    masks, split = modeling.time_split(df)
    users, insiders = pick_users(args, df, masks)
    start = pd.Timestamp(args.from_day or split['valid_end'])
    end = pd.Timestamp(args.to_day or split['last_day']) + pd.Timedelta(days=1)
    print(f'replaying users {users} from {start.date()} to {end.date()}')

    frames, stats = [], {'rows_read': 0, 'rows_bad_date': 0}
    for kind in ('logon', 'device', 'file', 'email'):
        for chunk in features_dataset.read_chunks(kind, stats):
            chunk = chunk[chunk['user'].isin(users) & (chunk['ts'] >= start) & (chunk['ts'] < end)]
            if len(chunk):
                frames.append(replay.to_auditra_events(kind, chunk))
    events = pd.concat(frames).sort_values('timestamp').reset_index(drop=True)

    shift_days = 0
    if not args.no_shift:
        last = events['timestamp'].max().normalize()
        today = pd.Timestamp(datetime.now(timezone.utc).date())
        weeks = max(0, math.ceil((today - last).days / 7))
        shift_days = 7 * weeks
        if (events['timestamp'].max() + pd.Timedelta(days=shift_days)).normalize() > today:
            shift_days -= 7                                       # never put events in the future
        events['timestamp'] = events['timestamp'] + pd.Timedelta(days=shift_days)
        print(f'shifted timestamps by {shift_days} days; replay now ends {events["timestamp"].max()}')

    outdir = config.WORK_DIR / 'replay'
    outdir.mkdir(parents=True, exist_ok=True)
    records = [{'user_id': r.user_id, 'timestamp': r.timestamp.strftime('%Y-%m-%dT%H:%M:%SZ'),
                'resource_accessed': r.resource_accessed, 'action': r.action,
                'resource_sensitivity': r.resource_sensitivity, 'ip_address': str(r.ip_address)[:50],
                'purpose': None} for r in events.itertuples()]
    with open(outdir / 'replay_events.jsonl', 'w') as f:
        for rec in records:
            f.write(json.dumps(rec) + '\n')
    mal = df[(df['label'] == 1) & df['user'].isin(users) & (df['day_dt'] >= start) & (df['day_dt'] < end)]
    mal_days = [{'user': str(r.user), 'day': (pd.Timestamp(r.day) + pd.Timedelta(days=shift_days)).strftime('%Y-%m-%d')}
                for r in mal.itertuples()]
    summary = {'events': len(records), 'users': [str(u) for u in users], 'shift_days': shift_days,
               'insiders_in_replay': [str(u) for u in users if u in insiders], 'malicious_days': mal_days,
               'expected': 'the insiders should be flagged on their malicious days (anomaly > 60%)'}
    (outdir / 'replay_summary.json').write_text(json.dumps(summary, indent=2))
    print(f'wrote {len(records):,} events -> {outdir / "replay_events.jsonl"}')

    if args.post:
        sent = 0
        for i in range(0, len(records), args.batch):
            body = json.dumps({'logs': records[i:i + args.batch]}).encode()
            headers = {
                'Content-Type': 'application/json',
                'X-Auditra-Ingest-Key': os.environ.get('AUDITRA_INGEST_KEY', 'auditra-ingest-dev-key'),
            }
            req = urllib.request.Request(args.post, data=body, headers=headers)
            with urllib.request.urlopen(req, timeout=60) as resp:
                result = json.loads(resp.read())
            sent += result.get('created', 0)
            print(f'  sent {min(i + args.batch, len(records)):,}/{len(records):,}  server created={result.get("created")}')
            time.sleep(args.delay)
        print(f'done: {sent:,} events ingested')


if __name__ == '__main__':
    main()
