"""Turn the raw multi-GB event files into ONE small table: a row per user per active day.

Why: the raw data (tens of millions of rows) cannot be loaded into 8 GB of RAM, and the model does not need
it. It needs a few numbers per user per day. We read each file in chunks, aggregate every chunk, merge the
small aggregates, and never hold the raw rows. Intermediate results are saved per file, so a crash after
40 minutes does not lose the work (re-run to resume; use --force to redo).
"""
import json
import re
import time

import numpy as np
import pandas as pd

import config

# aggregation spec per file: column -> how to combine chunks ('sum' | 'min' | 'max')
AGG = {
    'logon': {'logon_count': 'sum', 'logoff_count': 'sum', 'logon_after_hours': 'sum', 'logon_weekend': 'sum',
              'after_hours_events': 'sum', 'first_logon_hour': 'min', 'last_logoff_hour': 'max'},
    'device': {'usb_connects': 'sum', 'usb_after_hours': 'sum', 'after_hours_events': 'sum'},
    'file': {'file_events': 'sum', 'file_exe': 'sum', 'file_after_hours': 'sum', 'after_hours_events': 'sum'},
    'email': {'emails_sent': 'sum', 'emails_external': 'sum', 'email_attachments': 'sum', 'email_ext_attach': 'sum',
              'email_size_mb': 'sum', 'email_after_hours': 'sum', 'after_hours_events': 'sum'},
    'http': {'http_events': 'sum', 'http_jobsite': 'sum', 'http_leaksite': 'sum', 'http_cloud': 'sum',
             'http_after_hours': 'sum'},
}
CONSOLIDATE_EVERY = 20          # merge partial aggregates every N chunks to keep memory flat


def is_after_hours(hour):
    return (hour < config.WORK_START_HOUR) | (hour > config.WORK_END_HOUR)


def read_chunks(kind, stats):
    """Yield cleaned chunks of one raw file with parsed timestamp columns."""
    spec = config.SCHEMA[kind]
    path = config.DATA_DIR / spec['file']
    if not path.exists():
        raise FileNotFoundError(f'{path} not found. Check DATA_DIR / SCHEMA in config.py')
    header = pd.read_csv(path, nrows=0).columns.tolist()
    expected = spec['cols']
    missing = [c for c in expected if c not in header]
    if missing:                                   # extra columns in the file are fine; missing ones are not
        raise ValueError(f'{path.name}: expected column(s) {missing} not found. File has {header}. '
                         f'Run 01_inspect_dataset.py and update SCHEMA in config.py')
    use = [c for c in expected if c not in config.SKIP_COLUMNS]
    for chunk in pd.read_csv(path, usecols=use, dtype=str, chunksize=config.CHUNK_ROWS):
        stats['rows_read'] += len(chunk)
        ts = pd.to_datetime(chunk['date'], format=config.DATE_FORMAT, errors='coerce')
        bad = ts.isna()
        if bad.any():
            stats['rows_bad_date'] += int(bad.sum())
            chunk, ts = chunk[~bad], ts[~bad]
        chunk = chunk.copy()
        chunk['ts'] = ts
        chunk['day'] = ts.dt.normalize()
        chunk['hour_f'] = ts.dt.hour + ts.dt.minute / 60.0
        chunk['after'] = is_after_hours(ts.dt.hour)
        chunk['weekend'] = ts.dt.dayofweek >= 5
        yield chunk


def _num(series):
    return pd.to_numeric(series, errors='coerce').fillna(0)


def email_flags(chunk):
    """(sent to at least one external address, has an attachment) as boolean Series.
    Shared with replay.py so the training features and the replayed events can never disagree."""
    to_all = chunk['to'].fillna('') + ';' + chunk['cc'].fillna('') + ';' + chunk['bcc'].fillna('')
    total = to_all.str.count('@')
    internal = to_all.str.lower().str.count(re.escape(config.COMPANY_DOMAIN))
    external = (total - internal) > 0
    has_att = chunk['attachments'].fillna('').str.strip() != ''
    return external, has_att


def process(kind, chunk):
    """Return (aggregate frame indexed by user/day, dict of 'unique' frames) for one chunk."""
    key = ['user', 'day']
    uniq = {}
    if kind == 'logon':
        logon = chunk['activity'] == config.LOGON_VALUE
        logoff = chunk['activity'] == config.LOGOFF_VALUE
        part = pd.DataFrame({
            'user': chunk['user'], 'day': chunk['day'],
            'logon_count': logon.astype(int), 'logoff_count': logoff.astype(int),
            'logon_after_hours': (logon & chunk['after']).astype(int),
            'logon_weekend': (logon & chunk['weekend']).astype(int),
            'after_hours_events': (chunk['after'] & (logon | logoff)).astype(int),
            'first_logon_hour': chunk['hour_f'].where(logon), 'last_logoff_hour': chunk['hour_f'].where(logoff)})
        uniq['distinct_pcs'] = chunk.loc[logon, ['user', 'day', 'pc']].drop_duplicates()
    elif kind == 'device':
        conn = chunk['activity'] == config.DEVICE_CONNECT_VALUE
        part = pd.DataFrame({'user': chunk['user'], 'day': chunk['day'], 'usb_connects': conn.astype(int),
                             'usb_after_hours': (conn & chunk['after']).astype(int),
                             'after_hours_events': (conn & chunk['after']).astype(int)})
    elif kind == 'file':
        part = pd.DataFrame({'user': chunk['user'], 'day': chunk['day'], 'file_events': 1,
                             'file_exe': chunk['filename'].fillna('').str.lower().str.endswith('.exe').astype(int),
                             'file_after_hours': chunk['after'].astype(int),
                             'after_hours_events': chunk['after'].astype(int)})
    elif kind == 'email':
        external, has_att = email_flags(chunk)
        part = pd.DataFrame({'user': chunk['user'], 'day': chunk['day'], 'emails_sent': 1,
                             'emails_external': external.astype(int), 'email_attachments': has_att.astype(int),
                             'email_ext_attach': (external & has_att).astype(int),
                             'email_size_mb': _num(chunk['size']) / 1e6,
                             'email_after_hours': chunk['after'].astype(int),
                             'after_hours_events': chunk['after'].astype(int)})
    elif kind == 'http':
        domain = (chunk['url'].fillna('').str.extract(r'^(?:[a-zA-Z]+://)?([^/:?#]+)', expand=False)
                  .fillna('').str.lower().str.replace(r'^www\.', '', regex=True))
        pat = lambda words: '|'.join(re.escape(w) for w in words)
        part = pd.DataFrame({'user': chunk['user'], 'day': chunk['day'], 'http_events': 1,
                             'http_jobsite': domain.str.contains(pat(config.JOB_SITES)).astype(int),
                             'http_leaksite': domain.str.contains(pat(config.LEAK_SITES)).astype(int),
                             'http_cloud': domain.str.contains(pat(config.CLOUD_STORAGE)).astype(int),
                             'http_after_hours': chunk['after'].astype(int)})
        # hash the domain to a 64-bit integer: far smaller in memory than millions of strings
        h = pd.util.hash_pandas_object(domain, index=False).astype('uint64')
        uniq['http_distinct_domains'] = pd.DataFrame({'user': chunk['user'].values, 'day': chunk['day'].values,
                                                      'd': h.values}).drop_duplicates()
    else:
        raise ValueError(kind)
    agg = part.groupby(key).agg(AGG[kind])
    return agg, uniq


def _consolidate(frames, kind):
    return pd.concat(frames).groupby(level=[0, 1]).agg(AGG[kind])


def build_kind(kind, force=False, skip_http_distinct=False):
    """Aggregate one raw file; saves work/part_<kind>.csv and returns it."""
    out = config.WORK_DIR / f'part_{kind}.csv'
    if out.exists() and not force:
        print(f'[{kind}] already built -> reusing {out.name} (use --force to rebuild)')
        return pd.read_csv(out, parse_dates=['day'], index_col=['user', 'day'])
    stats = {'rows_read': 0, 'rows_bad_date': 0}
    t0 = time.time()
    frames, uniques = [], {}
    for i, chunk in enumerate(read_chunks(kind, stats), 1):
        agg, uniq = process(kind, chunk)
        frames.append(agg)
        for name, u in uniq.items():
            if name == 'http_distinct_domains' and skip_http_distinct:
                continue
            uniques.setdefault(name, []).append(u)
        if i % CONSOLIDATE_EVERY == 0:
            frames = [_consolidate(frames, kind)]
            for name in uniques:
                uniques[name] = [pd.concat(uniques[name]).drop_duplicates()]
        if i % 10 == 0:
            print(f'  [{kind}] {stats["rows_read"]:,} rows  ({time.time() - t0:,.0f}s)')
    if not frames:
        raise RuntimeError(f'{kind}: no rows read')
    result = _consolidate(frames, kind)
    for name, parts in uniques.items():
        u = pd.concat(parts).drop_duplicates()
        result[name] = u.groupby(['user', 'day']).size().reindex(result.index).fillna(0).astype(int)
    config.WORK_DIR.mkdir(parents=True, exist_ok=True)
    result.reset_index().to_csv(out, index=False)
    stats['seconds'] = round(time.time() - t0, 1)
    stats['user_days'] = len(result)
    (config.WORK_DIR / f'part_{kind}.stats.json').write_text(json.dumps(stats, indent=2))
    print(f'[{kind}] done: {stats}')
    return result


def add_common_columns(df):
    """Derived columns, including the COMMON deployable set (must mirror auditra_features.py)."""
    df['activity_events'] = (df['logon_count'] + df['logoff_count'] + df['usb_connects'] + df['file_events']
                             + df['emails_sent'])
    df['exfil_events'] = df['file_events'] + df['email_ext_attach']
    df['login_events'] = df['logon_count']
    df['logins_after_hours'] = df['logon_after_hours']
    df['logins_weekend'] = df['logon_weekend']
    df['distinct_hosts'] = df['distinct_pcs']
    df['removable_media_events'] = df['usb_connects']
    return df


def build_all(force=False, skip_http_distinct=False):
    parts = [build_kind(k, force, skip_http_distinct) for k in config.SCHEMA]
    merged = None
    for p in parts:
        if 'after_hours_events' in p.columns:
            p = p.rename(columns={'after_hours_events': f'_ah_{id(p)}'})
        merged = p if merged is None else merged.join(p, how='outer')
    ah_cols = [c for c in merged.columns if c.startswith('_ah_')]
    merged['after_hours_events'] = merged[ah_cols].fillna(0).sum(axis=1)
    merged = merged.drop(columns=ah_cols)
    count_cols = [c for c in merged.columns if c not in ('first_logon_hour', 'last_logoff_hour')]
    merged[count_cols] = merged[count_cols].fillna(0)
    for col in config.FULL_FEATURES:                       # guarantee every expected column exists
        if col not in merged.columns and col not in ('activity_events',):
            merged[col] = 0
    merged = add_common_columns(merged)
    merged = merged.reset_index()
    merged['day'] = pd.to_datetime(merged['day']).dt.strftime('%Y-%m-%d')
    merged = merged.sort_values(['day', 'user']).reset_index(drop=True)
    return merged
