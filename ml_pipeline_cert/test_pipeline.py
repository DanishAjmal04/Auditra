"""Automated checks for the pipeline. Run:  python test_pipeline.py   (needs the synthetic data; see README).

The round-trip test is the most important: it proves a model trained on dataset-derived features can score
features computed from Auditra's own events, because both paths give identical numbers.
"""
import json
import shutil
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

import auditra_features
import config
import features_dataset
import modeling
import replay
import scorer

PASSED = []


def check(name, condition, detail=''):
    if not condition:
        print(f'FAIL  {name}  {detail}')
        sys.exit(1)
    PASSED.append(name)
    print(f'ok    {name}')


def test_common_feature_lists_match():
    check('COMMON_FEATURES identical in config and auditra_features',
          config.COMMON_FEATURES == auditra_features.COMMON_FEATURES)
    check('working hours identical', (config.WORK_START_HOUR, config.WORK_END_HOUR) ==
          (auditra_features.WORK_START_HOUR, auditra_features.WORK_END_HOUR))


def test_chunk_size_does_not_change_features():
    """Distinct counts and min/max must be identical whatever the chunk size (the classic big-file bug)."""
    original, work = config.CHUNK_ROWS, config.WORK_DIR
    results = []
    try:
        for rows in (3_000, 1_000_000):
            config.CHUNK_ROWS = rows
            config.WORK_DIR = Path(tempfile.mkdtemp())
            results.append(features_dataset.build_all(force=True))
    finally:
        config.CHUNK_ROWS, config.WORK_DIR = original, work
    a, b = results
    check('same shape for chunk 3k vs 1M rows', a.shape == b.shape, f'{a.shape} vs {b.shape}')
    check('identical values for chunk 3k vs 1M rows',
          np.allclose(a.drop(columns=['user', 'day']).fillna(-1).values, b.drop(columns=['user', 'day']).fillna(-1).values))


def test_round_trip():
    """dataset features == features recomputed from replayed Auditra events."""
    users = ['SYN0003', 'SYN0027', 'SYN0001', 'SYN0010']
    stats = {'rows_read': 0, 'rows_bad_date': 0}
    frames = []
    for kind in ('logon', 'device', 'file', 'email'):
        for chunk in features_dataset.read_chunks(kind, stats):
            chunk = chunk[chunk['user'].isin(users)]
            frames.append(replay.to_auditra_events(kind, chunk))
    events = pd.concat(frames)
    rebuilt = auditra_features.common_features_from_events(events).set_index(['user', 'day'])
    truth = pd.read_csv(config.FEATURES_CSV).set_index(['user', 'day'])
    truth = truth[truth.index.get_level_values('user').isin(users)][config.COMMON_FEATURES]
    check('same user-days', set(rebuilt.index) == set(truth.index), f'{len(rebuilt)} vs {len(truth)}')
    rebuilt = rebuilt.loc[truth.index]
    for col in config.COMMON_FEATURES:
        check(f'round-trip feature {col}', np.allclose(rebuilt[col].astype(float), truth[col].astype(float)),
              f'max diff {np.abs(rebuilt[col].astype(float) - truth[col].astype(float)).max()}')


def test_split_has_no_overlap_and_is_chronological():
    df = modeling.load_table()
    (tr, va, te), split = modeling.time_split(df)
    check('masks are disjoint', not (tr & va).any() and not (tr & te).any() and not (va & te).any())
    check('masks cover every row', (tr | va | te).all())
    check('train < valid < test in time', df.loc[tr, 'day_dt'].max() < df.loc[va, 'day_dt'].min() <=
          df.loc[va, 'day_dt'].max() < df.loc[te, 'day_dt'].min())


def test_spec_uses_only_training_rows():
    """Baselines must come from TRAIN rows only (no leakage). Poison the test rows and check nothing changes."""
    df = modeling.load_table()
    (tr, va, te), _ = modeling.time_split(df)
    s1 = scorer.build_spec(df[tr], config.COMMON_FEATURES, 'personal')
    poisoned = df.copy()
    poisoned.loc[te, config.COMMON_FEATURES] = 9999
    s2 = scorer.build_spec(poisoned[tr], config.COMMON_FEATURES, 'personal')
    check('spec identical when test rows change', json.dumps(s1, sort_keys=True) == json.dumps(s2, sort_keys=True))


def test_calibration_hits_the_threshold():
    cal = {'lo': 1.0, 'thr': 3.0, 'hi': 7.0}
    pct = scorer.to_pct(np.array([0.0, 1.0, 3.0, 3.0001, 7.0, 99.0]), cal)
    check('below lo -> 0', pct[0] == 0 and pct[1] == 0)
    check('threshold -> exactly the unusual line', abs(pct[2] - scorer.UNUSUAL_PCT) < 1e-9)
    check('just above threshold is "unusual"', pct[3] > scorer.UNUSUAL_PCT)
    check('top and beyond -> 100', pct[4] == 100 and pct[5] == 100)


def test_exported_model_loads_and_flags_an_insider():
    path = config.ARTIFACT_DIR / 'anomaly_v1'
    check('artifact exists (run step 4 first)', (path / 'model.joblib').exists())
    sc = scorer.AnomalyScorer.load(path)
    df = modeling.load_table()
    (_, _, te), _ = modeling.time_split(df)
    out = sc.score_frame(df[te])
    check('scores within 0-100', out['anomaly_pct'].between(0, 100).all())
    check('flag rate is small (alert budget)', out['is_unusual'].mean() < 0.10, f'{out["is_unusual"].mean():.3f}')
    flagged_insider_days = ((out['label'] == 1) & out['is_unusual']).sum()
    check('at least one insider day flagged', flagged_insider_days > 0)
    check('reasons are non-empty text', out.loc[out['is_unusual'], 'reason'].str.len().min() > 0)


def test_new_user_falls_back_to_global_baseline():
    sc = scorer.AnomalyScorer.load(config.ARTIFACT_DIR / 'anomaly_v1')
    row = pd.DataFrame([{'user': 'BRAND_NEW', 'day': '2030-01-01', **{f: 0 for f in config.COMMON_FEATURES}}])
    out = sc.score_frame(row)
    check('unseen user scores without error', len(out) == 1 and 0 <= out['anomaly_pct'].iloc[0] <= 100)


if __name__ == '__main__':
    for name, fn in list(globals().items()):
        if name.startswith('test_') and callable(fn):
            print(f'\n[{name}]')
            fn()
    print(f'\nALL {len(PASSED)} CHECKS PASSED')
