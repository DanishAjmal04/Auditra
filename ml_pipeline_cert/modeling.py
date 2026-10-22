"""Training helpers: data loading, time-based split, the candidate models, and evaluation metrics."""
import time

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.neighbors import LocalOutlierFactor
from sklearn.svm import OneClassSVM

import config
import scorer

MODELS = ['isolation_forest', 'lof', 'ocsvm', 'robust_z']
MODES = ['raw', 'personal', 'both']


def load_table():
    """Feature table joined with labels, sorted by date. Columns user, day, day_dt, label, features..."""
    feats = pd.read_csv(config.FEATURES_CSV)
    labels = pd.read_csv(config.LABELS_CSV)
    df = feats.merge(labels, on=['user', 'day'], how='left')
    df['label'] = df['label'].fillna(0).astype(int)
    df['day_dt'] = pd.to_datetime(df['day'])
    return df.sort_values(['day_dt', 'user']).reset_index(drop=True)


def time_split(df):
    """Earliest 60% of the calendar = train, next 15% = validation, last 25% = test. NEVER a random split:
    a random split would let the model peek at the future of the same user."""
    d0, d1 = df['day_dt'].min(), df['day_dt'].max()
    span = (d1 - d0).days + 1
    t1 = d0 + pd.Timedelta(days=int(span * config.TRAIN_FRACTION))
    t2 = d0 + pd.Timedelta(days=int(span * (config.TRAIN_FRACTION + config.VALID_FRACTION)))
    masks = (df['day_dt'] < t1, (df['day_dt'] >= t1) & (df['day_dt'] < t2), df['day_dt'] >= t2)
    return masks, {'train_end': str(t1.date()), 'valid_end': str(t2.date()),
                   'first_day': str(d0.date()), 'last_day': str(d1.date())}


def make_estimator(name):
    if name == 'isolation_forest':
        return IsolationForest(n_estimators=300, max_samples=256, contamination='auto',
                               random_state=config.RANDOM_STATE, n_jobs=-1)
    if name == 'lof':
        return LocalOutlierFactor(n_neighbors=35, novelty=True, n_jobs=-1)
    if name == 'ocsvm':
        return OneClassSVM(kernel='rbf', gamma='scale', nu=0.02)
    if name == 'robust_z':
        return None
    raise ValueError(name)


def fit_estimator(name, Ms_train, max_rows):
    """Fit one candidate. LOF / One-Class SVM get a random sample when the training set is large."""
    est = make_estimator(name)
    if est is None:
        return None
    X = Ms_train
    limit = config.OCSVM_MAX_ROWS if name == 'ocsvm' else max_rows
    if len(X) > limit:
        rng = np.random.default_rng(config.RANDOM_STATE)
        X = X[rng.choice(len(X), limit, replace=False)]
    est.fit(X)
    return est


def evaluate(scores, y, thr, n_days, users):
    """Metrics for one period. y = 1 for rows inside a labelled insider window."""
    y = np.asarray(y)
    pred = np.asarray(scores) >= thr
    out = {'alerts': int(pred.sum()), 'alerts_per_day': round(pred.sum() / max(n_days, 1), 2)}
    pos = y == 1
    if pos.any() and (~pos).any():
        out['roc_auc'] = float(roc_auc_score(y, scores))
        out['pr_auc'] = float(average_precision_score(y, scores))
    else:
        out['roc_auc'] = out['pr_auc'] = float('nan')
    tp, fp, fn = int((pred & pos).sum()), int((pred & ~pos).sum()), int((~pred & pos).sum())
    out['precision'] = tp / (tp + fp) if tp + fp else float('nan')
    out['recall'] = tp / (tp + fn) if tp + fn else float('nan')
    p, r = out['precision'], out['recall']
    out['f1'] = 2 * p * r / (p + r) if p == p and r == r and (p + r) > 0 else float('nan')
    users = np.asarray(users)
    insiders = np.unique(users[pos])
    caught = [u for u in insiders if (pred & pos & (users == u)).any()]
    out['insiders'] = len(insiders)
    out['insiders_detected'] = len(caught)
    out['insider_detection'] = f'{len(caught)}/{len(insiders)}'
    return out


def run_one(df, masks, features, mode, model, max_rows):
    """Train on the train period, calibrate on validation, report validation + test metrics."""
    train_m, valid_m, test_m = masks
    train, valid, test = df[train_m], df[valid_m], df[test_m]
    t0 = time.time()
    spec = scorer.build_spec(train, features, mode)
    Ms_train = scorer.standardize(scorer.transform(train, spec), spec)
    est = fit_estimator(model, Ms_train, max_rows)
    seconds = time.time() - t0
    s_train = scorer.raw_scores(train, spec, est, model)
    s_valid = scorer.raw_scores(valid, spec, est, model)
    s_test = scorer.raw_scores(test, spec, est, model)
    cal = scorer.make_calibration(s_train, s_valid, config.ALERT_RATE)
    days = lambda part: max(part['day_dt'].nunique(), 1)
    res_v = evaluate(s_valid, valid['label'], cal['thr'], days(valid), valid['user'])
    res_t = evaluate(s_test, test['label'], cal['thr'], days(test), test['user'])
    return {'model': model, 'mode': mode, 'n_features': len(features), 'train_seconds': round(seconds, 2),
            'val': res_v, 'test': res_t, 'cal': cal,
            'scores': {'valid': s_valid, 'test': s_test}, 'y': {'valid': valid['label'].values,
                                                                'test': test['label'].values}}
