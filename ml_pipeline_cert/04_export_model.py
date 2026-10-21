"""STEP 4: fit the chosen model on ALL data before the test period and save it for Auditra.

    python 04_export_model.py                       # uses work/evaluation/best_config.json (feature set 'common')
    python 04_export_model.py --model isolation_forest --mode personal --name anomaly_v1

Writes artifacts/<name>/model.joblib and meta.json. Only the COMMON feature set can be deployed, because
those are the only features Auditra can compute from its own logs (see config.py).
"""
import argparse
import datetime
import hashlib
import json
import platform

import joblib
import numpy as np
import sklearn

import config
import modeling
import scorer


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--name', default='anomaly_v1')
    ap.add_argument('--model', choices=modeling.MODELS)
    ap.add_argument('--mode', choices=modeling.MODES)
    ap.add_argument('--feature-set', default='common', choices=['common', 'full'])
    ap.add_argument('--max-train-rows', type=int, default=200_000)
    args = ap.parse_args()

    best_path = config.REPORT_DIR / 'best_config.json'
    chosen = {}
    if best_path.exists():
        chosen = json.loads(best_path.read_text()).get(args.feature_set, {})
    model = args.model or chosen.get('model') or 'isolation_forest'
    mode = args.mode or chosen.get('mode') or 'personal'
    features = config.COMMON_FEATURES if args.feature_set == 'common' else config.FULL_FEATURES
    if args.feature_set == 'full':
        print('WARNING: a model on the FULL feature set cannot be scored by Auditra (it lacks those logs).')

    df = modeling.load_table()
    masks, split = modeling.time_split(df)
    train_df = df[masks[0]]                               # train period only: all train rows, no labels
    valid_df = df[masks[1]]                               # validation period: used for threshold calibration
    print(f'exporting {model}/{mode} on {len(train_df):,} train user-days up to {split["train_end"]} (calibrated on valid up to {split["valid_end"]})')

    spec = scorer.build_spec(train_df, features, mode)
    Ms_train = scorer.standardize(scorer.transform(train_df, spec), spec)
    est = modeling.fit_estimator(model, Ms_train, args.max_train_rows)
    s_train = scorer.raw_scores(train_df, spec, est, model)
    s_valid = scorer.raw_scores(valid_df, spec, est, model)
    cal = scorer.make_calibration(s_train, s_valid, config.ALERT_RATE)

    bundle = {'spec': spec, 'estimator': est, 'kind': model, 'calibration': cal}
    outdir = config.ARTIFACT_DIR / args.name
    outdir.mkdir(parents=True, exist_ok=True)
    joblib.dump(bundle, outdir / 'model.joblib', compress=3)

    sha = hashlib.sha256(config.FEATURES_CSV.read_bytes()).hexdigest()
    meta = {
        'name': args.name, 'created_at': datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds'),
        'model': model, 'mode': mode, 'feature_set': args.feature_set, 'features': features,
        'alert_rate': config.ALERT_RATE, 'unusual_pct': scorer.UNUSUAL_PCT, 'calibration': cal,
        'trained_rows': int(len(train_df)), 'trained_users': int(train_df['user'].nunique()), 'split': split,
        'evaluation_on_test': chosen.get('test'), 'features_csv_sha256': sha,
        'versions': {'python': platform.python_version(), 'scikit_learn': sklearn.__version__,
                     'numpy': np.__version__, 'joblib': joblib.__version__},
        'random_state': config.RANDOM_STATE,
        'note': 'Load with scorer.AnomalyScorer.load(<this folder>). Retrain if scikit-learn major version changes.'}
    (outdir / 'meta.json').write_text(json.dumps(meta, indent=2, default=float))

    # smoke test on the untouched test period
    sc = scorer.AnomalyScorer.load(outdir)
    test = df[masks[2]]
    out = sc.score_frame(test.head(2000))
    print(f'saved {outdir}')
    print(f'test-period check: {int(out["is_unusual"].sum())} of {len(out)} user-days flagged unusual '
          f'({100 * out["is_unusual"].mean():.2f}%), max anomaly pct {out["anomaly_pct"].max():.0f}')
    top = out.sort_values('anomaly_pct', ascending=False).head(3)
    for _, r in top.iterrows():
        print(f'  {r["user"]} {r["day"]} -> {r["anomaly_pct"]:.0f}%  label={int(r["label"])}  {r["reason"]}')


if __name__ == '__main__':
    main()
