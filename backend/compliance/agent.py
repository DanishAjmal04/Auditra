import win32evtlog
import win32evtlogutil
import win32security
import requests
import time
import json
import socket
import datetime
import os


AUDITRA_URL = 'http://192.168.18.8:8000/api/ingest/'
INTERVAL_SECONDS = 30
MACHINE_NAME = socket.gethostname()

RESOURCE_MAP = {
    'Security': 'security_logs',
    'System': 'system_logs',
    'Application': 'application_logs',
    'Microsoft-Windows-PowerShell/Operational': 'powershell_logs',
    'Microsoft-Windows-TaskScheduler/Operational': 'task_scheduler_logs',
}

ACTION_MAP = {
    4624: 'LOGIN',
    4625: 'LOGIN',
    4634: 'LOGOUT',
    4648: 'LOGIN',
    4656: 'READ',
    4663: 'READ',
    4670: 'WRITE',
    4688: 'READ',
    4698: 'WRITE',
    4700: 'WRITE',
    4702: 'WRITE',
    4720: 'WRITE',
    4726: 'DELETE',
    4732: 'WRITE',
    4740: 'WRITE',
    4756: 'WRITE',
    4767: 'WRITE',
    4771: 'LOGIN',
    4776: 'LOGIN',
    4798: 'READ',
    4799: 'READ',
}

SENSITIVITY_MAP = {
    4624: 'LOW',
    4625: 'HIGH',
    4634: 'LOW',
    4648: 'HIGH',
    4656: 'HIGH',
    4663: 'HIGH',
    4670: 'HIGH',
    4688: 'MEDIUM',
    4698: 'HIGH',
    4700: 'HIGH',
    4702: 'HIGH',
    4720: 'HIGH',
    4726: 'HIGH',
    4732: 'HIGH',
    4740: 'HIGH',
    4756: 'HIGH',
    4767: 'HIGH',
    4771: 'HIGH',
    4776: 'MEDIUM',
    4798: 'MEDIUM',
    4799: 'MEDIUM',
}

last_read_time = {}


def get_current_user():
    try:
        return os.environ.get('USERNAME', 'unknown_user')
    except:
        return 'unknown_user'


def get_ip():
    try:
        return socket.gethostbyname(socket.gethostname())
    except:
        return '127.0.0.1'


def read_windows_events(log_type='Security', hours_back=1):
    events = []
    try:
        hand = win32evtlog.OpenEventLog(None, log_type)
        flags = win32evtlog.EVENTLOG_BACKWARDS_READ | win32evtlog.EVENTLOG_SEQUENTIAL_READ

        cutoff = datetime.datetime.now() - datetime.timedelta(hours=hours_back)

        while True:
            records = win32evtlog.ReadEventLog(hand, flags, 0)
            if not records:
                break

            for record in records:
                try:
                    event_time = record.TimeGenerated.replace(tzinfo=None)
                    if event_time < cutoff:
                        break

                    event_id = record.EventID & 0xFFFF

                    if event_id not in ACTION_MAP:
                        continue

                    action = ACTION_MAP.get(event_id, 'READ')
                    sensitivity = SENSITIVITY_MAP.get(event_id, 'MEDIUM')
                    resource = RESOURCE_MAP.get(log_type, 'windows_logs')

                    try:
                        strings = record.StringInserts
                        user_id = strings[5] if strings and len(strings) > 5 else get_current_user()
                        if user_id in ('-', '', None):
                            user_id = get_current_user()
                    except:
                        user_id = get_current_user()

                    user_id = f"{MACHINE_NAME}\\{user_id}"

                    events.append({
                        'user_id': user_id[:100],
                        'timestamp': event_time.isoformat(),
                        'resource_accessed': resource,
                        'action': action,
                        'resource_sensitivity': sensitivity,
                        'ip_address': get_ip(),
                        'purpose': None,
                        'event_id': event_id,
                        'machine': MACHINE_NAME,
                        'log_source': log_type
                    })

                except Exception:
                    continue

        win32evtlog.CloseEventLog(hand)

    except Exception as e:
        print(f"[WARNING] Could not read {log_type}: {e}")

    return events


def send_to_auditra(logs):
    if not logs:
        return

    try:
        payload = {'logs': logs}
        response = requests.post(
            AUDITRA_URL,
            json=payload,
            timeout=15,
            headers={'Content-Type': 'application/json'}
        )

        if response.status_code == 200:
            data = response.json()
            print(f"[✓] Sent {data['created']} logs | "
                  f"Violations: {data['violations_detected']}")
        else:
            print(f"[✗] Server error: {response.status_code}")

    except requests.exceptions.ConnectionError:
        print(f"[✗] Cannot connect to Auditra at {AUDITRA_URL}")
    except Exception as e:
        print(f"[✗] Error: {e}")


def run_agent():
    print("=" * 50)
    print("  Auditra Windows Agent")
    print(f"  Machine  : {MACHINE_NAME}")
    print(f"  Server   : {AUDITRA_URL}")
    print(f"  Interval : {INTERVAL_SECONDS} seconds")
    print("=" * 50)

    log_sources = ['Security', 'System', 'Application']

    while True:
        print(f"\n[{datetime.datetime.now().strftime('%H:%M:%S')}] Reading logs...")

        all_events = []
        for source in log_sources:
            events = read_windows_events(
                log_type=source,
                hours_back=1
            )
            all_events.extend(events)
            if events:
                print(f"  {source}: {len(events)} events")

        if all_events:
            send_to_auditra(all_events)
        else:
            print("  No new events found")

        print(f"  Next check in {INTERVAL_SECONDS} seconds...")
        time.sleep(INTERVAL_SECONDS)


if __name__ == '__main__':
    run_agent()

    