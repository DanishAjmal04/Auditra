"""STEP 2: raw files -> work/features_daily.csv (one row per user per active day) and work/labels_daily.csv.

    python 02_build_features.py                  # resumes if interrupted
    python 02_build_features.py --force          # rebuild everything
    python 02_build_features.py --skip-http-distinct   # saves RAM if the http file is huge

Expect minutes for a few hundred MB, tens of minutes for several GB. Run it once, then never touch the raw
data again.
"""
import argparse
import json

import pandas as pd

import config
import features_dataset


def make_labels(features):
    """1 for a (user, day) that falls inside a labelled insider window, else 0."""
    labels = features[['user', 'day']].copy()
    labels['label'] = 0
    labels['scenario'] = 0
    path = config.DATA_DIR / config.INSIDERS_FILE
    if not path.exists():
        print('No insiders file: labels_daily.csv will contain only zeros.')
        return labels
    ins = pd.read_csv(path)
    if 'dataset' in ins.columns:
        ins = ins[ins['dataset'].astype(str).str.strip().isin(['4.2', '4.20', 'r4.2'])].copy()
    ins['start'] = pd.to_datetime(ins['start'], format=config.INSIDERS_DATE_FORMAT, errors='coerce').dt.normalize()
    ins['end'] = pd.to_datetime(ins['end'], format=config.INSIDERS_DATE_FORMAT, errors='coerce').dt.normalize()
    valid_ins = ins.dropna(subset=['start', 'end'])
    print(f'\n[labels] release 4.2 insiders: {len(valid_ins)} windows across {valid_ins["user"].nunique()} distinct users')
    print(f'[labels] overall date window: {valid_ins["start"].min().strftime("%Y-%m-%d")} to {valid_ins["end"].max().strftime("%Y-%m-%d")}')
    for _, r in valid_ins[['scenario', 'user', 'start', 'end']].iterrows():
        print(f"  user: {r['user']} (scenario {r['scenario']}) from {r['start'].strftime('%Y-%m-%d')} to {r['end'].strftime('%Y-%m-%d')}")
    day = pd.to_datetime(labels['day'])
    for _, r in valid_ins.iterrows():
        hit = (labels['user'] == r['user']) & (day >= r['start']) & (day <= r['end'])
        labels.loc[hit, 'label'] = 1
        labels.loc[hit, 'scenario'] = int(r['scenario']) if str(r['scenario']).isdigit() else 1
    return labels


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--force', action='store_true')
    ap.add_argument('--skip-http-distinct', action='store_true')
    args = ap.parse_args()

    features = features_dataset.build_all(force=args.force, skip_http_distinct=args.skip_http_distinct)
    labels = make_labels(features)

    config.WORK_DIR.mkdir(parents=True, exist_ok=True)
    features.to_csv(config.FEATURES_CSV, index=False)
    labels.to_csv(config.LABELS_CSV, index=False)

    summary = {'user_days': len(features), 'users': int(features['user'].nunique()),
               'first_day': features['day'].min(), 'last_day': features['day'].max(),
               'malicious_user_days': int(labels['label'].sum()),
               'malicious_share_pct': round(100 * labels['label'].mean(), 3),
               'insider_users': int(labels.loc[labels['label'] == 1, 'user'].nunique())}
    (config.WORK_DIR / 'features_summary.json').write_text(json.dumps(summary, indent=2))
    print('\nFEATURE TABLE READY')
    print(json.dumps(summary, indent=2))
    print('\nSanity checks you should do by eye:')
    print(features.describe().T[['mean', 'min', 'max']].round(2).to_string())


if __name__ == '__main__':
    main()
