from django.utils import timezone

from ..models import SENSITIVITY_RANK

DATA_ACCESS_TYPES = {'FILE_READ', 'FILE_WRITE', 'FILE_DELETE', 'FILE_COPY_TO_USB', 'PRINT'}
PROCESSING_TYPES = {'FILE_READ', 'FILE_WRITE', 'FILE_COPY_TO_USB', 'PRINT'}
ALWAYS_ALLOWED_CATEGORIES = {'GENERAL'}

ACTION_WORDS = {
    'FILE_READ': 'opened',
    'FILE_WRITE': 'modified',
    'FILE_DELETE': 'deleted',
    'FILE_COPY_TO_USB': 'copied to USB',
    'PRINT': 'printed',
}


def who(event):
    if event.employee:
        return f'{event.employee.full_name} ({event.account})'
    return f'{event.account} (not linked to an employee)'


def what(event):
    target = event.file_name or event.path or event.domain or event.device
    return f'{ACTION_WORDS.get(event.event_type, event.get_event_type_display().lower())} {target}'.strip()


def at(event):
    return timezone.localtime(event.occurred_at).strftime('%H:%M:%S')


def allowed_categories(employee):
    if not employee:
        return set(ALWAYS_ALLOWED_CATEGORIES)
    return set(employee.allowed_categories or []) | ALWAYS_ALLOWED_CATEGORIES


def max_sensitivity_rank(employee):
    if not employee:
        return SENSITIVITY_RANK['LOW']
    return SENSITIVITY_RANK.get(employee.max_sensitivity, 2)


def shift_text(employee):
    if not employee:
        return 'default hours 08:00-18:00'
    return f"shift {employee.shift_start.strftime('%H:%M')}-{employee.shift_end.strftime('%H:%M')}"
