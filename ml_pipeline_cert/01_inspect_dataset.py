"""STEP 1: look at the dataset before doing anything else.

    python 01_inspect_dataset.py

For every file in DATA_DIR it prints: size on disk, the header, 3 sample rows, row count, date range and
number of distinct users. It then checks the files against SCHEMA in config.py and tells you exactly what
to change. Output is also saved to work/dataset_profile.json (paste it into the report's "Dataset" section).
"""
import json
import time

import pandas as pd

import config


def human(n):
    for unit in ('B', 'KB', 'MB', 'GB', 'TB'):
        if n < 1024:
            return f'{n:.1f} {unit}'
        n /= 1024
    return f'{n:.1f} PB'


def main():
    print(f'DATA_DIR = {config.DATA_DIR}')
    if not config.DATA_DIR.exists():
        raise SystemExit('DATA_DIR does not exist. Extract the dataset there or set AUDITRA_DATA_DIR.')

    print('\n== every file found ==')
    total = 0
    for p in sorted(config.DATA_DIR.rglob('*')):
        if p.is_file():
            total += p.stat().st_size
            print(f'  {human(p.stat().st_size):>10}  {p.relative_to(config.DATA_DIR)}')
    print(f'  total: {human(total)}')

    profile = {'total_bytes': total, 'files': {}}
    for kind, spec in config.SCHEMA.items():
        path = config.DATA_DIR / spec['file']
        print(f'\n== {kind}: {spec["file"]} ==')
        if not path.exists():
            print('  MISSING: not found. Update SCHEMA[...]["file"] in config.py (or this dataset has no such log).')
            continue
        head = pd.read_csv(path, nrows=3, dtype=str)
        print('  columns :', head.columns.tolist())
        missing = [c for c in spec['cols'] if c not in head.columns]
        extra = [c for c in head.columns if c not in spec['cols']]
        print('  expected:', spec['cols'], '  <-- OK' if not missing else f'  <-- MISSING {missing}: fix SCHEMA')
        if extra:
            print(f'  note: file has extra columns {extra} (ignored; use them if they help, e.g. a removable-media flag)')
        print(head.drop(columns=[c for c in config.SKIP_COLUMNS if c in head.columns], errors='ignore')
              .to_string(max_colwidth=40, index=False))
        rows, users, dmin, dmax, bad = 0, set(), None, None, 0
        t0 = time.time()
        for chunk in pd.read_csv(path, usecols=['date', 'user'], dtype=str, chunksize=config.CHUNK_ROWS):
            rows += len(chunk)
            users.update(chunk['user'].unique())
            ts = pd.to_datetime(chunk['date'], format=config.DATE_FORMAT, errors='coerce')
            bad += int(ts.isna().sum())
            if ts.notna().any():
                dmin = ts.min() if dmin is None else min(dmin, ts.min())
                dmax = ts.max() if dmax is None else max(dmax, ts.max())
        print(f'  rows={rows:,}  users={len(users):,}  from {dmin} to {dmax}  unparseable dates={bad:,} '
              f'({time.time() - t0:.0f}s)')
        if bad:
            print('  WARNING: dates did not match DATE_FORMAT in config.py -> fix the format string.')
        profile['files'][kind] = {'bytes': path.stat().st_size, 'rows': rows, 'users': len(users),
                                  'first': str(dmin), 'last': str(dmax), 'bad_dates': bad}

    ins = config.DATA_DIR / config.INSIDERS_FILE
    print(f'\n== labels: {config.INSIDERS_FILE} ==')
    if ins.exists():
        df = pd.read_csv(ins)
        if 'dataset' in df.columns:
            df = df[df['dataset'].astype(str).str.strip().isin(['4.2', '4.20', 'r4.2'])]
        print(df.to_string(index=False, max_colwidth=40))
        profile['insiders'] = len(df)
    else:
        print('  not found: the dataset may have NO labels. Then evaluation must use injected scenarios'
              ' (see the guide, section "No labels").')

    config.WORK_DIR.mkdir(parents=True, exist_ok=True)
    (config.WORK_DIR / 'dataset_profile.json').write_text(json.dumps(profile, indent=2))
    print(f'\nsaved {config.WORK_DIR / "dataset_profile.json"}')


if __name__ == '__main__':
    main()
