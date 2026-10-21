"""Compute the COMMON feature set from Auditra's own events.

This file is copied into the backend (backend/compliance/ml/). It must stay self-contained (pandas only) and
must produce EXACTLY the same numbers as features_dataset.add_common_columns does for the dataset. The test
`test_round_trip` in test_pipeline.py enforces this by replaying dataset events through both paths.

An "event" is a row with: user_id, timestamp, action, resource_accessed, ip_address (Auditra's Log fields).

Mapping contract (dataset event -> Auditra event) is implemented in replay.py:
    logon                         -> action LOGIN,  resource 'workstation'
    logoff                        -> action LOGOUT, resource 'workstation'
    USB connect                   -> action WRITE,  resource 'removable_media'
    file copy                     -> action EXPORT, resource 'file:<name>'
    e-mail with external recipient AND attachment -> action EXPORT, resource 'email_attachment'
    any other e-mail              -> action WRITE,  resource 'email'
"""
import pandas as pd

WORK_START_HOUR = 8      # keep equal to config.WORK_START_HOUR / compliance.reports.config.WORKING_HOURS
WORK_END_HOUR = 18

COMMON_FEATURES = [
    'activity_events', 'login_events', 'logins_after_hours', 'logins_weekend', 'distinct_hosts',
    'after_hours_events', 'exfil_events', 'removable_media_events',
]
REMOVABLE_RESOURCE = 'removable_media'


def empty_frame():
    return pd.DataFrame(columns=['user', 'day'] + COMMON_FEATURES)


def common_features_from_events(events):
    """One row per (user, UTC day) with the COMMON features. `events` may be empty."""
    if events is None or len(events) == 0:
        return empty_frame()
    ts = pd.to_datetime(events['timestamp'], utc=True).dt.tz_localize(None)
    hour = ts.dt.hour
    after = (hour < WORK_START_HOUR) | (hour > WORK_END_HOUR)
    weekend = ts.dt.dayofweek >= 5
    login = events['action'].values == 'LOGIN'
    base = pd.DataFrame({
        'user': events['user_id'].astype(str).values, 'day': ts.dt.normalize().values,
        'activity_events': 1, 'login_events': login.astype(int),
        'logins_after_hours': (login & after.values).astype(int),
        'logins_weekend': (login & weekend.values).astype(int),
        'after_hours_events': after.astype(int).values,
        'exfil_events': (events['action'].values == 'EXPORT').astype(int),
        'removable_media_events': (events['resource_accessed'].values == REMOVABLE_RESOURCE).astype(int)})
    out = base.groupby(['user', 'day']).sum()
    hosts = pd.DataFrame({'user': base['user'][login], 'day': base['day'][login],
                          'host': events['ip_address'].astype(str).values[login]}).drop_duplicates()
    out['distinct_hosts'] = hosts.groupby(['user', 'day']).size().reindex(out.index).fillna(0).astype(int)
    out = out.reset_index()
    out['day'] = pd.to_datetime(out['day']).dt.strftime('%Y-%m-%d')
    return out[['user', 'day'] + COMMON_FEATURES]
