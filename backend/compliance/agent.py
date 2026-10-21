import ctypes
import json
import os
import socket
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from pathlib import Path

import requests
import win32evtlog


AUDITRA_URL = os.environ.get('AUDITRA_URL', 'http://127.0.0.1:8000/api/ingest/')
INGEST_KEY = os.environ.get('AUDITRA_INGEST_KEY', 'auditra-ingest-dev-key')
INTERVAL_SECONDS = int(os.environ.get('AUDITRA_INTERVAL_SECONDS', '10'))
USB_LOG = 'Microsoft-Windows-Kernel-PnP/Configuration'
MACHINE_NAME = socket.gethostname()
STATE_PATH = Path(__file__).resolve().parent / 'agent_state.json'

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
    4800: 'LOGOUT',
    4801: 'LOGIN',
    6416: 'WRITE',
}

# 6416 is "a new external device was recognized". That is the Security-log
# shape that matches the model's removable-media feature. Logons stay LOGIN.
RESOURCE_OVERRIDE = {
    6416: 'removable_media',
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
    6416: 'HIGH',
    4771: 'HIGH',
    4776: 'MEDIUM',
    4798: 'MEDIUM',
    4799: 'MEDIUM',
    4800: 'LOW',
    4801: 'LOW',
}


def is_windows_admin():
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except (AttributeError, OSError):
        return False


def get_current_user():
    return os.environ.get('USERNAME', 'unknown_user')


def get_ip():
    try:
        return socket.gethostbyname(socket.gethostname())
    except OSError:
        return '127.0.0.1'


def load_state():
    if not STATE_PATH.is_file():
        return {}
    try:
        return json.loads(STATE_PATH.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        return {}


def save_state(state):
    STATE_PATH.write_text(json.dumps(state), encoding='utf-8')


def cutoff_for(state, log_type):
    raw = state.get(log_type)
    if raw:
        try:
            return datetime.fromisoformat(raw)
        except ValueError:
            pass
    return datetime.now() - timedelta(minutes=15)


def read_windows_events(log_type, cutoff):
    events = []
    newest = cutoff
    try:
        hand = win32evtlog.OpenEventLog(None, log_type)
        flags = win32evtlog.EVENTLOG_BACKWARDS_READ | win32evtlog.EVENTLOG_SEQUENTIAL_READ

        while True:
            records = win32evtlog.ReadEventLog(hand, flags, 0)
            if not records:
                break

            passed_cutoff = False
            for record in records:
                try:
                    event_time = record.TimeGenerated.replace(tzinfo=None)
                    if event_time <= cutoff:
                        passed_cutoff = True
                        break
                    if event_time > newest:
                        newest = event_time

                    event_id = record.EventID & 0xFFFF
                    if event_id not in ACTION_MAP:
                        continue

                    try:
                        strings = record.StringInserts
                        user_id = strings[5] if strings and len(strings) > 5 else get_current_user()
                        if user_id in ('-', '', None):
                            user_id = get_current_user()
                    except (TypeError, IndexError):
                        user_id = get_current_user()

                    events.append({
                        'user_id': f'{MACHINE_NAME}\\{user_id}'[:100],
                        'timestamp': event_time.isoformat(),
                        'resource_accessed': RESOURCE_OVERRIDE.get(
                            event_id,
                            RESOURCE_MAP.get(log_type, 'windows_logs'),
                        ),
                        'action': ACTION_MAP[event_id],
                        'resource_sensitivity': SENSITIVITY_MAP.get(event_id, 'MEDIUM'),
                        'ip_address': get_ip(),
                        'purpose': 'Windows event log',
                        'event_id': event_id,
                        'machine': MACHINE_NAME,
                        'log_source': log_type,
                    })
                except Exception:
                    continue

            if passed_cutoff:
                break

        win32evtlog.CloseEventLog(hand)
    except Exception as exc:
        message = str(exc)
        print(f'[WARNING] Could not read {log_type}: {message}')
        if log_type == 'Security' and not is_windows_admin():
            print(
                '[WARNING] The Security log needs an Administrator prompt. '
                'System and Application logs will still be sent. '
                'Logons from those channels are not a CERT insider day; '
                'run python manage.py load_anomaly_demo to show the trained model.'
            )

    return events, newest


def read_usb_events(cutoff):
    """USB insertion is written to the Plug and Play channel, which the old event API cannot read."""
    events = []
    newest = cutoff
    seen = set()
    window_ms = max(60_000, int((datetime.now() - cutoff).total_seconds() * 1000))
    query_xml = (
        f"*[System[(EventID=410) and TimeCreated[timediff(@SystemTime) <= {window_ms}]]]"
    )
    namespace = '{http://schemas.microsoft.com/win/2004/08/events/event}'
    try:
        query = win32evtlog.EvtQuery(
            USB_LOG,
            win32evtlog.EvtQueryReverseDirection,
            query_xml,
        )
        while True:
            batch = win32evtlog.EvtNext(query, 20)
            if not batch:
                break
            for record in batch:
                xml_text = win32evtlog.EvtRender(record, win32evtlog.EvtRenderEventXml)
                root = ET.fromstring(xml_text)
                created = root.find(f'.//{namespace}TimeCreated')
                device_node = root.find(f".//{namespace}Data[@Name='DeviceInstanceId']")
                if created is None or device_node is None or not device_node.text:
                    continue
                aware = datetime.fromisoformat(
                    created.attrib['SystemTime'].replace('Z', '+00:00')
                ).astimezone()
                event_time = aware.replace(tzinfo=None)
                if event_time <= cutoff:
                    continue
                if event_time > newest:
                    newest = event_time
                device = device_node.text
                if not device.upper().startswith('USBSTOR\\'):
                    continue
                if device in seen:
                    continue
                seen.add(device)
                events.append({
                    'user_id': f'{MACHINE_NAME}\\{get_current_user()}'[:100],
                    'timestamp': aware.isoformat(),
                    'resource_accessed': 'removable_media',
                    'action': 'WRITE',
                    'resource_sensitivity': 'HIGH',
                    'ip_address': get_ip(),
                    'purpose': 'USB storage device connected',
                    'event_id': 410,
                    'machine': MACHINE_NAME,
                    'log_source': USB_LOG,
                })
    except Exception as exc:
        print(f'[WARNING] Could not read USB devices: {exc}')
    return events, newest


def send_to_auditra(logs):
    if not logs:
        return True

    try:
        response = requests.post(
            AUDITRA_URL,
            json={'logs': logs},
            timeout=15,
            headers={
                'Content-Type': 'application/json',
                'X-Auditra-Ingest-Key': INGEST_KEY,
            },
        )
        if response.status_code == 200:
            data = response.json()
            print(
                f'[OK] Sent {data.get("created", 0)} logs | '
                f'Violations: {data.get("violations_detected", 0)}'
            )
            return True
        print(f'[FAIL] Server error: {response.status_code} {response.text[:200]}')
        return False
    except requests.exceptions.ConnectionError:
        print(f'[FAIL] Cannot connect to Auditra at {AUDITRA_URL}')
        return False
    except Exception as exc:
        print(f'[FAIL] Error: {exc}')
        return False


def run_agent():
    print('=' * 50)
    print('  Auditra Windows Agent')
    print(f'  Machine  : {MACHINE_NAME}')
    print(f'  Server   : {AUDITRA_URL}')
    print(f'  Interval : {INTERVAL_SECONDS} seconds')
    print('  USB      : a storage stick is read from the Plug and Play log.')
    print('  Unlock   : Win+L is a Security-log event and needs this window')
    print('             to be Run as administrator.')
    print('=' * 50)

    admin = is_windows_admin()
    if admin:
        log_sources = ['Security', 'System', 'Application']
    else:
        print('[WARNING] Not running as Administrator, so unlock/login will not be collected.')
        print('          USB storage is still collected.')
        log_sources = ['System', 'Application']

    while True:
        print(f'\n[{datetime.now().strftime("%H:%M:%S")}] Reading logs...')
        state = load_state()
        all_events = []
        scanned_until = {}

        for source in log_sources:
            cutoff = cutoff_for(state, source)
            events, newest = read_windows_events(source, cutoff)
            all_events.extend(events)
            scanned_until[source] = newest.isoformat()
            if events:
                print(f'  {source}: {len(events)} new events')

        usb_cutoff = cutoff_for(state, USB_LOG)
        usb_events, usb_newest = read_usb_events(usb_cutoff)
        all_events.extend(usb_events)
        scanned_until[USB_LOG] = usb_newest.isoformat()
        if usb_events:
            print(f'  USB storage: {len(usb_events)} device(s)')

        if all_events:
            sent = send_to_auditra(all_events)
        else:
            print('  No new events found')
            sent = True

        if sent:
            state.update(scanned_until)
            save_state(state)

        print(f'  Next check in {INTERVAL_SECONDS} seconds...')
        time.sleep(INTERVAL_SECONDS)


if __name__ == '__main__':
    run_agent()
