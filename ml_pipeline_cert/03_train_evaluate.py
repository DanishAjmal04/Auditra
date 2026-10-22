"""STEP 3: train every candidate, compare them honestly, pick the best by VALIDATION score.

    python 03_train_evaluate.py                       # full comparison (feature sets x modes x models)
    python 03_train_evaluate.py --quick               # isolation_forest + robust_z only, raw + personal
    python 03_train_evaluate.py --feature-sets common # only the deployable feature set

Reads work/features_daily.csv + labels_daily.csv. Writes work/evaluation/:
    results.csv, results.md          full comparison table (this is your "Results" section)
    best_config.json                 winning model/mode per feature set (used by step 4)
    pr_curves.png, roc_curves.png, score_distribution.png
Honest protocol: fit on TRAIN period, choose threshold + best model on VALIDATION, report TEST once.
"""
import argparse
import json

import numpy as np
import pandas as pd

import config
import modeling


def markdown_table(df):
    """Tiny markdown writer (avoids needing the optional 'tabulate' package)."""
    cols = list(df.columns)
    lines = ['| ' + ' | '.join(cols) + ' |', '|' + '|'.join(['---'] * len(cols)) + '|']
    for _, row in df.iterrows():
        lines.append('| ' + ' | '.join('' if (isinstance(v, float) and v != v) else str(v) for v in row) + ' |')
    return '\n'.join(lines) + '\n'


def plots(results, best, outdir):
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        from sklearn.metrics import precision_recall_curve, roc_curve
    except ImportError:
        print('matplotlib not installed: skipping plots (pip install matplotlib)')
        return
    rows = [r for r in results if r['feature_set'] == best['feature_set']]
    # keep the best mode per model for readability
    keep = {}
    for r in rows:
        v = r['val']['pr_auc']
        v = -1 if v != v else v
        if r['model'] not in keep or v > keep[r['model']][0]:
            keep[r['model']] = (v, r)
    for kind, fname, title in (('pr', 'pr_curves.png', 'Precision-recall (test period)'),
                               ('roc', 'roc_curves.png', 'ROC (test period)')):
        fig, ax = plt.subplots(figsize=(6, 4.5))
        for model, (_, r) in keep.items():
            y, s = r['y']['test'], r['scores']['test']
            if y.sum() == 0:
                continue
            if kind == 'pr':
                p, rc, _ = precision_recall_curve(y, s)
                ax.plot(rc, p, label=f"{model} ({r['mode']}) AP={r['test']['pr_auc']:.2f}")
                ax.set_xlabel('Recall'); ax.set_ylabel('Precision')
            else:
                fpr, tpr, _ = roc_curve(y, s)
                ax.plot(fpr, tpr, label=f"{model} ({r['mode']}) AUC={r['test']['roc_auc']:.2f}")
                ax.plot([0, 1], [0, 1], 'k:', lw=0.8)
                ax.set_xlabel('False positive rate'); ax.set_ylabel('True positive rate')
        ax.set_title(f"{title}, feature set: {best['feature_set']}")
        ax.legend(fontsize=7)
        fig.tight_layout(); fig.savefig(outdir / fname, dpi=130); plt.close(fig)
    # score distribution of the winner on the test period
    win = next(r for r in results if (r['feature_set'], r['model'], r['mode']) ==
               (best['feature_set'], best['model'], best['mode']))
    s, y = win['scores']['test'], win['y']['test']
    fig, ax = plt.subplots(figsize=(6, 4))
    bins = np.linspace(min(s), max(s), 50)
    ax.hist(s[y == 0], bins=bins, alpha=0.7, label='normal user-days')
    if (y == 1).any():
        ax.hist(s[y == 1], bins=bins, alpha=0.8, label='insider user-days')
    ax.axvline(win['cal']['thr'], color='k', ls='--', label='alert threshold')
    ax.set_yscale('log'); ax.set_xlabel('raw anomaly score'); ax.legend()
    ax.set_title(f"Score distribution: {best['model']} / {best['mode']}")
    fig.tight_layout(); fig.savefig(outdir / 'score_distribution.png', dpi=130); plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--feature-sets', nargs='+', default=['common', 'full'], choices=['common', 'full'])
    ap.add_argument('--modes', nargs='+', default=modeling.MODES, choices=modeling.MODES)
    ap.add_argument('--models', nargs='+', default=modeling.MODELS, choices=modeling.MODELS)
    ap.add_argument('--quick', action='store_true')
    ap.add_argument('--max-train-rows', type=int, default=200_000)
    args = ap.parse_args()
    if args.quick:
        args.models, args.modes = ['isolation_forest', 'robust_z'], ['raw', 'personal']

    df = modeling.load_table()
    masks, split = modeling.time_split(df)
    print('split:', split)
    print('rows  train/valid/test:', [int(m.sum()) for m in masks],
          ' malicious user-days:', [int(df.loc[m, 'label'].sum()) for m in masks])
    if df.loc[masks[1], 'label'].sum() == 0:
        print('WARNING: no insider in the VALIDATION period. Model selection falls back to the test ROC-AUC,'
              ' which is slightly optimistic. Report this honestly.')

    results = []
    fsets = {'common': config.COMMON_FEATURES, 'full': config.FULL_FEATURES}
    for fs in args.feature_sets:
        for mode in args.modes:
            for model in args.models:
                r = modeling.run_one(df, masks, fsets[fs], mode, model, args.max_train_rows)
                r['feature_set'] = fs
                results.append(r)
                print(f"{fs:6} {mode:8} {model:17} val_AP={r['val']['pr_auc']:.3f} test_AP={r['test']['pr_auc']:.3f} "
                      f"test_AUC={r['test']['roc_auc']:.3f} insiders={r['test']['insider_detection']} "
                      f"alerts/day={r['test']['alerts_per_day']} ({r['train_seconds']}s)")

    table = pd.DataFrame([{
        'feature_set': r['feature_set'], 'mode': r['mode'], 'model': r['model'],
        'val_pr_auc': r['val']['pr_auc'], 'val_recall': r['val']['recall'], 'val_precision': r['val']['precision'],
        'test_roc_auc': r['test']['roc_auc'], 'test_pr_auc': r['test']['pr_auc'],
        'test_precision': r['test']['precision'], 'test_recall': r['test']['recall'], 'test_f1': r['test']['f1'],
        'insiders_detected': r['test']['insider_detection'], 'alerts_per_day': r['test']['alerts_per_day'],
        'train_seconds': r['train_seconds']} for r in results]).round(3)

    outdir = config.REPORT_DIR
    outdir.mkdir(parents=True, exist_ok=True)
    table.to_csv(outdir / 'results.csv', index=False)
    (outdir / 'results.md').write_text(markdown_table(table))

    def select_best(cand):
        def safe_val(v):
            return -1.0 if (v is None or v != v) else float(v)

        valid_cand = [r for r in cand if safe_val(r['val']['pr_auc']) >= 0]
        if not valid_cand:
            return cand[0]
        best_pr = max(safe_val(r['val']['pr_auc']) for r in valid_cand)
        top_tier = [r for r in valid_cand if safe_val(r['val']['pr_auc']) >= (best_pr - 0.002 - 1e-9)]
        return max(top_tier, key=lambda r: (safe_val(r['val']['recall']), safe_val(r['val']['pr_auc'])))

    best_cfg = {}
    for fs in args.feature_sets:
        cand = [r for r in results if r['feature_set'] == fs]
        b = select_best(cand)
        best_cfg[fs] = {'feature_set': fs, 'model': b['model'], 'mode': b['mode'],
                        'val_pr_auc': b['val']['pr_auc'], 'val_recall': b['val']['recall'],
                        'test': b['test'], 'split': split}
        print(f'\nBEST for feature set {fs}: {b["model"]} / {b["mode"]} '
              f'(val PR-AUC {b["val"]["pr_auc"]:.3f}, val recall {b["val"]["recall"]:.3f})')
        # Print top 3 candidates for visibility
        sorted_cand = sorted(cand, key=lambda r: (r['val']['pr_auc'] if r['val']['pr_auc'] == r['val']['pr_auc'] else -1,
                                                  r['val']['recall'] if r['val']['recall'] == r['val']['recall'] else -1), reverse=True)
        print(f'Top 3 candidates for {fs} (validation):')
        for i, c in enumerate(sorted_cand[:3], 1):
            print(f"  {i}. {c['model']:17} ({c['mode']:8}) val_PR_AUC={c['val']['pr_auc']:.3f} val_recall={c['val']['recall']:.3f}")
    (outdir / 'best_config.json').write_text(json.dumps(best_cfg, indent=2, default=float))
    focus = best_cfg.get('common') or next(iter(best_cfg.values()))
    plots(results, focus, outdir)
    print(f'\nSaved results to {outdir}')


if __name__ == '__main__':
    main()
