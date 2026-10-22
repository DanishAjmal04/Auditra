"""Generate a SMALL synthetic dataset in the same file layout as the CERT-style insider-threat data.

Purpose: let you test the whole pipeline in minutes on a laptop BEFORE touching the real multi-GB dataset.
The numbers it produces are NOT research results: the behaviour is simulated by us.

    python 00_make_synthetic_data.py                 # writes into data/raw/
    python 00_make_synthetic_data.py --users 120 --days 200

It writes logon.csv, device.csv, file.csv, email.csv, http.csv and answers/insiders.csv.
"""
import argparse
import csv
from datetime import datetime, timedelta

import numpy as np

import config

DOMAINS = [f'site{i}.com' for i in range(150)] + ['news.example.com', 'mail.example.com', 'docs.example.com']


def fmt(dt):
    return dt.strftime(config.DATE_FORMAT)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--users', type=int, default=80)
    ap.add_argument('--days', type=int, default=180)
    ap.add_argument('--seed', type=int, default=7)
    ap.add_argument('--out', default=str(config.DATA_DIR))
    args = ap.parse_args()

    rng = np.random.default_rng(args.seed)
    out = config.Path(args.out)
    (out / 'answers').mkdir(parents=True, exist_ok=True)
    start = datetime(2010, 1, 4)                       # a Monday
    users = [f'SYN{i:04d}' for i in range(args.users)]
    home_pc = {u: f'PC-{rng.integers(1000, 9999)}' for u in users}

    # per-user habits (so "normal" differs between people)
    habit = {u: dict(
        login_hour=rng.normal(9.0, 0.8), logoff_hour=rng.normal(17.5, 0.8),
        usb_p=rng.choice([0.0, 0.02, 0.06], p=[0.5, 0.35, 0.15]),
        files=rng.uniform(0.3, 3.0), emails=rng.uniform(3, 14), ext_p=rng.uniform(0.02, 0.2),
        http=rng.uniform(15, 70)) for u in users}

    # insiders: (user index, scenario, first day, last day)
    n_days = args.days
    plan = [
        (3, 1, int(n_days * 0.64), int(n_days * 0.69)),   # in the VALIDATION period
        (11, 2, int(n_days * 0.66), int(n_days * 0.72)),
        (19, 3, int(n_days * 0.62), int(n_days * 0.67)),
        (27, 1, int(n_days * 0.80), int(n_days * 0.86)),  # in the TEST period
        (35, 2, int(n_days * 0.84), int(n_days * 0.90)),
        (43, 3, int(n_days * 0.78), int(n_days * 0.83)),
        (51, 4, int(n_days * 0.88), int(n_days * 0.93)),
    ]
    insider_days = {}                                   # (user, day_index) -> scenario
    for ui, sc, d0, d1 in plan:
        if ui < len(users):
            for d in range(d0, d1 + 1):
                insider_days[(users[ui], d)] = sc

    files = {k: open(out / v['file'], 'w', newline='') for k, v in config.SCHEMA.items()}
    writers = {k: csv.writer(f) for k, f in files.items()}
    for k, v in config.SCHEMA.items():
        writers[k].writerow(v['cols'])
    counters = {k: 0 for k in files}

    def emit(kind, row):
        counters[kind] += 1
        writers[kind].writerow([f'{kind[0].upper()}{counters[kind]:09d}'] + row)

    for d in range(n_days):
        day = start + timedelta(days=d)
        weekend = day.weekday() >= 5
        for u in users:
            sc = insider_days.get((u, d), 0)
            if weekend and sc == 0 and rng.random() > 0.03:
                continue
            if not weekend and rng.random() < 0.06:           # absent
                continue
            h = habit[u]
            pc = home_pc[u]
            lg_hour = float(np.clip(rng.normal(h['login_hour'], 0.5), 6, 11))
            lo_hour = float(np.clip(rng.normal(h['logoff_hour'], 0.6), lg_hour + 4, 21))
            n_logon = 1
            usb_p, files_l, emails_l, http_l, ext_p = h['usb_p'], h['files'], h['emails'], h['http'], h['ext_p']
            att_p, extra_after = 0.2, False
            domains_extra = []

            if sc == 1:                         # after-hours work + USB + big copies + leak-site browsing
                lg_hour, lo_hour = rng.uniform(19, 22), rng.uniform(23, 23.9)
                usb_p, files_l = 0.95, 25
                domains_extra = ['wikileaks.org'] * int(rng.integers(2, 6))
            elif sc == 2:                       # job-site browsing, then a USB copy spree
                usb_p, files_l = 0.9, 18
                domains_extra = [str(rng.choice(config.JOB_SITES)) for _ in range(int(rng.integers(5, 15)))]
            elif sc == 3:                       # e-mailing attachments to external addresses
                ext_p, att_p, emails_l = 0.8, 0.9, emails_l + 12
            elif sc == 4:                       # logging on to many other PCs after hours (account sharing)
                n_logon = int(rng.integers(4, 8))
                lg_hour, lo_hour = rng.uniform(19, 21), rng.uniform(22, 23.5)

            def t(hour, jitter=0.0):
                hh = float(np.clip(hour + (rng.random() * jitter), 0, 23.99))
                return day + timedelta(hours=hh)

            for i in range(n_logon):
                host = pc if i == 0 else f'PC-{rng.integers(1000, 9999)}'
                emit('logon', [fmt(t(lg_hour, 0.2)), u, host, config.LOGON_VALUE])
                emit('logon', [fmt(t(lo_hour, 0.2)), u, host, config.LOGOFF_VALUE])

            if rng.random() < usb_p:
                th = float(np.clip(rng.uniform(lg_hour, lo_hour), 0, 23.9))
                emit('device', [fmt(day + timedelta(hours=th)), u, pc, 'x:\\', config.DEVICE_CONNECT_VALUE])
                emit('device', [fmt(day + timedelta(hours=min(th + 0.4, 23.99))), u, pc, 'x:\\', 'Disconnect'])

            for _ in range(rng.poisson(files_l)):
                th = float(np.clip(rng.uniform(lg_hour, lo_hour), 0, 23.9))
                ext = rng.choice(['doc', 'pdf', 'zip', 'exe', 'jpg'], p=[0.4, 0.3, 0.1, 0.05, 0.15])
                emit('file', [fmt(day + timedelta(hours=th)), u, pc, f'R{rng.integers(100000, 999999)}.{ext}', ''])

            for _ in range(rng.poisson(emails_l)):
                th = float(np.clip(rng.uniform(lg_hour, lo_hour), 0, 23.9))
                external = rng.random() < ext_p
                to = f'{u.lower()}{rng.integers(1, 99)}@' + ('gmail.com' if external else 'dtaa.com')
                att = f'doc{rng.integers(1, 99)}.zip({rng.integers(1000, 90000)})' if rng.random() < att_p else ''
                emit('email', [fmt(day + timedelta(hours=th)), u, pc, to, '', '', f'{u.lower()}@dtaa.com',
                               int(rng.integers(500, 90000)), att, ''])

            urls = [f'http://{rng.choice(DOMAINS)}/page{rng.integers(1, 9999)}' for _ in range(rng.poisson(http_l))]
            urls += [f'http://{dm}/x' for dm in domains_extra]
            for url in urls:
                th = float(np.clip(rng.uniform(lg_hour, lo_hour), 0, 23.9))
                emit('http', [fmt(day + timedelta(hours=th)), u, pc, url, ''])

    for f in files.values():
        f.close()

    with open(out / config.INSIDERS_FILE, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['dataset', 'scenario', 'details', 'user', 'start', 'end'])
        for ui, sc, d0, d1 in plan:
            if ui < len(users):
                w.writerow(['synthetic', sc, f'scenario {sc}', users[ui],
                            fmt(start + timedelta(days=d0)), fmt(start + timedelta(days=d1, hours=23, minutes=59))])
    print('rows written:', counters)
    print('output folder:', out)


if __name__ == '__main__':
    main()
