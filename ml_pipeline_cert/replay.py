"""Convert dataset events into Auditra Log events (the contract is documented in auditra_features.py).

Used for (a) the round-trip correctness test and (b) the live "replay" demo: stream a real insider's
behaviour through Auditra's /api/ingest/ endpoint and watch the model flag it.
"""
import pandas as pd

import config
import features_dataset


def to_auditra_events(kind, chunk):
    """DataFrame with Auditra's fields for one cleaned chunk (from features_dataset.read_chunks).
    http events are not replayed (Auditra has no web-proxy connector)."""
    base = {'user_id': chunk['user'].values, 'timestamp': chunk['ts'].values, 'ip_address': chunk['pc'].values,
            'purpose': None}
    n = len(chunk)
    if kind == 'logon':
        login = (chunk['activity'] == config.LOGON_VALUE).values
        keep = login | (chunk['activity'] == config.LOGOFF_VALUE).values
        action = pd.Series(['LOGIN' if v else 'LOGOUT' for v in login])
        res, sens = pd.Series(['workstation'] * n), pd.Series(['LOW'] * n)
    elif kind == 'device':
        keep = (chunk['activity'] == config.DEVICE_CONNECT_VALUE).values
        action, res, sens = (pd.Series(['WRITE'] * n), pd.Series([config.REMOVABLE_RESOURCE_NAME] * n),
                             pd.Series(['HIGH'] * n))
    elif kind == 'file':
        keep = [True] * n
        action = pd.Series(['EXPORT'] * n)
        res = pd.Series(('file:' + chunk['filename'].fillna('').astype(str).str.slice(0, 150)).values)
        sens = pd.Series(['MEDIUM'] * n)
    elif kind == 'email':
        external, has_att = features_dataset.email_flags(chunk)
        exfil = (external & has_att).values
        keep = [True] * n
        action = pd.Series(['EXPORT' if v else 'WRITE' for v in exfil])
        res = pd.Series(['email_attachment' if v else 'email' for v in exfil])
        sens = pd.Series(['MEDIUM' if v else 'LOW' for v in exfil])
    else:
        return pd.DataFrame(columns=['user_id', 'timestamp', 'action', 'resource_accessed',
                                     'resource_sensitivity', 'ip_address', 'purpose'])
    out = pd.DataFrame(base)
    out['action'], out['resource_accessed'], out['resource_sensitivity'] = action.values, res.values, sens.values
    return out[pd.Series(keep).values].reset_index(drop=True)
