"""Scoring core. THE SINGLE SOURCE OF TRUTH for how a feature table becomes an anomaly score.

Used by BOTH training (03/04 scripts) and the live Auditra backend. Because it is the same code in both
places, training and production cannot drift apart. It is deliberately:
  * Django-free (only numpy / pandas / scikit-learn / joblib),
  * free of custom pickled classes (the saved model is a plain dict + sklearn estimator), so the artifact
    loads no matter which folder this file is copied to.

Vocabulary
  feature table : DataFrame with columns user, day and the feature columns (one row per user per day)
  spec          : JSON-friendly dict describing the transformation (features, fills, baselines, scaling)
  raw score     : higher = more anomalous
  anomaly pct   : raw score mapped to 0-100 so that the alert threshold lands exactly on UNUSUAL_PCT (60)
"""
import json
import math
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

HOUR_FEATURES = {'first_logon_hour', 'last_logoff_hour'}      # not counts: no log1p
Z_CLIP = 10.0
MIN_USER_DAYS = 5                                              # below this a user falls back to the global baseline
UNUSUAL_PCT = 60

FEATURE_LABELS = {
    'logon_count': 'logons', 'logoff_count': 'logoffs', 'logon_after_hours': 'after-hours logons',
    'logon_weekend': 'weekend logons', 'distinct_pcs': 'distinct PCs', 'first_logon_hour': 'first logon hour',
    'last_logoff_hour': 'last logoff hour', 'usb_connects': 'USB connections',
    'usb_after_hours': 'after-hours USB connections', 'file_events': 'file copies', 'file_exe': 'executable copies',
    'file_after_hours': 'after-hours file copies', 'emails_sent': 'emails sent',
    'emails_external': 'emails to external addresses', 'email_attachments': 'emails with attachments',
    'email_ext_attach': 'external emails with attachments', 'email_size_mb': 'email volume (MB)',
    'email_after_hours': 'after-hours emails', 'http_events': 'web requests', 'http_distinct_domains': 'distinct websites',
    'http_jobsite': 'job-site visits', 'http_leaksite': 'leak-site visits', 'http_cloud': 'cloud-storage visits',
    'http_after_hours': 'after-hours web requests', 'after_hours_events': 'after-hours events',
    'activity_events': 'total activity', 'login_events': 'logins', 'logins_after_hours': 'after-hours logins',
    'logins_weekend': 'weekend logins', 'distinct_hosts': 'distinct hosts', 'exfil_events': 'data-export events',
    'removable_media_events': 'removable-media events',
}


# ───────────────────────── transformation ─────────────────────────
def prepare_values(df, spec):
    """Selected features as floats: NaN filled, counts log1p-transformed."""
    X = df[spec['features']].astype(float).copy()
    for f in spec['features']:
        X[f] = X[f].fillna(spec['fill'][f])
        if f in spec['log1p']:
            X[f] = np.log1p(X[f].clip(lower=0))
    return X


def personal_z(X, users, spec):
    """Robust z-score of each row against ITS USER's own baseline (global baseline for unknown/new users)."""
    feats = spec['features']
    g_med = np.array([spec['global_median'][f] for f in feats])
    g_scale = np.array([spec['global_scale'][f] for f in feats])
    med = np.tile(g_med, (len(X), 1))
    scale = np.tile(g_scale, (len(X), 1))
    users = np.asarray(users)
    for u in np.unique(users):
        st = spec['user_stats'].get(str(u))
        if st is None:
            continue
        idx = np.where(users == u)[0]
        med[idx] = np.array([st['median'][f] for f in feats])
        scale[idx] = np.maximum(np.array([st['scale'][f] for f in feats]), 0.5 * g_scale)
    return np.clip((X.values - med) / scale, -Z_CLIP, Z_CLIP)


def transform(df, spec):
    """Feature table -> numeric matrix, according to spec['mode'] ('raw' | 'personal' | 'both')."""
    X = prepare_values(df, spec)
    mode = spec['mode']
    if mode == 'raw':
        return X.values
    z = personal_z(X, df['user'].values, spec)
    return z if mode == 'personal' else np.hstack([X.values, z])


def build_spec(train_df, features, mode):
    """Learn everything the transformation needs from TRAINING rows only (no leakage from valid/test)."""
    spec = {'features': list(features), 'mode': mode,
            'log1p': [f for f in features if f not in HOUR_FEATURES], 'fill': {}, 'user_stats': {}}
    for f in features:
        med = train_df[f].median()
        spec['fill'][f] = 0.0 if pd.isna(med) else float(med)
    X = prepare_values(train_df, spec)
    med = X.median()
    mad = (X - med).abs().median()
    std = X.std(ddof=0)
    spec['global_median'] = {f: float(med[f]) for f in features}
    spec['global_scale'] = {f: float(max(1.4826 * mad[f], std[f], 0.05)) for f in features}
    users = train_df['user'].astype(str).values
    for u in np.unique(users):
        idx = np.where(users == u)[0]
        if len(idx) < MIN_USER_DAYS:
            continue
        Xu = X.iloc[idx]
        mu = Xu.median()
        mu_mad = (Xu - mu).abs().median()
        spec['user_stats'][str(u)] = {'median': {f: float(mu[f]) for f in features},
                                      'scale': {f: float(1.4826 * mu_mad[f]) for f in features}}
    M = transform(train_df, spec)
    spec['matrix_mean'] = M.mean(axis=0).tolist()
    spec['matrix_scale'] = np.where(M.std(axis=0) < 1e-6, 1.0, M.std(axis=0)).tolist()
    return spec


def standardize(M, spec):
    return (M - np.array(spec['matrix_mean'])) / np.array(spec['matrix_scale'])


# ───────────────────────── scoring ─────────────────────────
def robust_z_score(Ms):
    """Baseline 'model' without ML: mean of the 3 largest absolute standardised values in a row."""
    top = np.sort(np.abs(Ms), axis=1)[:, -3:]
    return top.mean(axis=1)


def raw_scores(df, spec, estimator, kind):
    Ms = standardize(transform(df, spec), spec)
    if kind == 'robust_z':
        return robust_z_score(Ms)
    return -estimator.decision_function(Ms)


def make_calibration(train_scores, valid_scores, alert_rate):
    """lo = typical normal level, thr = alert threshold (alert budget on validation), hi = largest seen."""
    lo = float(np.percentile(train_scores, 5))
    thr = float(np.quantile(valid_scores, 1 - alert_rate))
    thr = max(thr, lo + 1e-6)
    hi = float(max(np.max(train_scores), np.max(valid_scores), thr + 1e-6))
    return {'lo': lo, 'thr': thr, 'hi': hi, 'alert_rate': alert_rate}


def to_pct(scores, cal):
    """Piecewise-linear map: [lo, thr] -> [0, UNUSUAL_PCT]; [thr, hi] -> [UNUSUAL_PCT, 100]."""
    s = np.asarray(scores, dtype=float)
    below = UNUSUAL_PCT * np.clip((s - cal['lo']) / (cal['thr'] - cal['lo']), 0, 1)
    above = UNUSUAL_PCT + (100 - UNUSUAL_PCT) * np.clip((s - cal['thr']) / (cal['hi'] - cal['thr']), 0, 1)
    return np.where(s < cal['thr'], below, above)


def explain_rows(df, spec, top_n=3, min_z=2.0):
    """For each row: the features that deviate most from the user's own usual behaviour, as short sentences."""
    X = prepare_values(df, spec)
    z = personal_z(X, df['user'].values, spec)
    feats = spec['features']
    out = []
    for i in range(len(df)):
        order = np.argsort(-z[i])[:top_n]
        parts = []
        for j in order:
            if z[i, j] < min_z:
                break
            f = feats[j]
            usual = spec['global_median'][f]
            st = spec['user_stats'].get(str(df['user'].iloc[i]))
            if st:
                usual = st['median'][f]
            value = df[f].iloc[i]
            usual_val = usual if f in HOUR_FEATURES else math.expm1(usual)
            parts.append(f"{FEATURE_LABELS.get(f, f)}: {value:g} (usual {usual_val:.1f})")
        out.append('; '.join(parts) if parts else 'No single feature stands out')
    return out


class AnomalyScorer:
    """Loads a saved model directory and scores feature tables."""

    def __init__(self, bundle, meta):
        self.spec = bundle['spec']
        self.estimator = bundle['estimator']
        self.kind = bundle['kind']
        self.calibration = bundle['calibration']
        self.meta = meta

    @classmethod
    def load(cls, directory):
        directory = Path(directory)
        bundle = joblib.load(directory / 'model.joblib')
        meta = json.loads((directory / 'meta.json').read_text())
        return cls(bundle, meta)

    def score_frame(self, df, explain=True):
        """df needs columns user, day + the model's features. Returns df plus anomaly_raw/pct/is_unusual/reason."""
        out = df.copy()
        raw = raw_scores(out, self.spec, self.estimator, self.kind)
        out['anomaly_raw'] = raw
        out['anomaly_pct'] = np.round(to_pct(raw, self.calibration), 1)
        out['is_unusual'] = out['anomaly_pct'] > UNUSUAL_PCT
        if explain:
            out['reason'] = explain_rows(out, self.spec)
        return out

    @property
    def features(self):
        return self.spec['features']
