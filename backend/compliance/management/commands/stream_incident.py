import time

import requests
from django.conf import settings
from django.core.management.base import BaseCommand

from compliance.management.commands.load_case import SARA, Command as CaseCommand


class Command(BaseCommand):
    help = 'Send Sara Ahmed\'s after-hours incident into the live ingest API.'

    def handle(self, *args, **options):
        case = CaseCommand()
        events = []
        for entry in case.incident_events():
            payload = dict(entry)
            payload['timestamp'] = entry['timestamp'].isoformat()
            events.append(payload)

        url = 'http://127.0.0.1:8000/api/ingest/'
        headers = {
            'Content-Type': 'application/json',
            'X-Auditra-Ingest-Key': settings.INGEST_API_KEY,
        }
        self.stdout.write(f'Sending {len(events)} events for {SARA}')
        self.stdout.write('Watch the dashboard. It refreshes every 5 seconds.')

        created = 0
        violations = 0
        batch_size = 4
        for start in range(0, len(events), batch_size):
            batch = events[start:start + batch_size]
            try:
                response = requests.post(
                    url,
                    json={'logs': batch},
                    headers=headers,
                    timeout=30,
                )
            except requests.exceptions.ConnectionError:
                self.stderr.write(self.style.ERROR(
                    'Backend is not running. Start it with: python manage.py runserver'
                ))
                return
            if response.status_code != 200:
                self.stderr.write(self.style.ERROR(
                    f'Ingest failed ({response.status_code}): {response.text[:300]}'
                ))
                return
            body = response.json()
            created += body.get('created', 0)
            violations += body.get('violations_detected', 0)
            self.stdout.write(
                f'  sent {start + len(batch)}/{len(events)} '
                f'| new violations in this batch: {body.get("violations_detected", 0)}'
            )
            time.sleep(2)

        self.stdout.write(self.style.SUCCESS(
            f'Done. {created} logs ingested, {violations} rule hits. '
            'The dashboard should now show Sara Ahmed.'
        ))
