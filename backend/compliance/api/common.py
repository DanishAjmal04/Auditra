from rest_framework.pagination import PageNumberPagination

from ..models import AuditEntry


class Pages(PageNumberPagination):
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 500


def audit(request, action, target, **details):
    AuditEntry.objects.create(
        actor=request.user if request.user and request.user.is_authenticated else None,
        action=action,
        target=str(target)[:200],
        details=details,
    )


class AuditedModelMixin:
    """Writes an audit entry for every create, update and delete through a viewset."""

    audit_label = 'record'

    def perform_create(self, serializer):
        obj = serializer.save()
        audit(self.request, f'{self.audit_label}.create', obj, data=_jsonable(serializer.data))

    def perform_update(self, serializer):
        obj = serializer.save()
        audit(self.request, f'{self.audit_label}.update', obj, data=_jsonable(serializer.data))

    def perform_destroy(self, instance):
        audit(self.request, f'{self.audit_label}.delete', instance)
        instance.delete()


def _jsonable(data):
    out = {}
    for key, value in dict(data).items():
        if isinstance(value, (str, int, float, bool, type(None), list, dict)):
            out[key] = value
        else:
            out[key] = str(value)
    return out
