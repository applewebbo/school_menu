from django.utils.deprecation import MiddlewareMixin

from school_menu.models import AuditLog


class AuditLogMiddleware(MiddlewareMixin):
    """Middleware that provides request.audit_log() helper for logging critical actions."""

    def process_request(self, request):
        """Add audit_log helper method to request object."""

        def audit_log(action, model_name, object_id, object_repr, changes=None):
            """
            Log a critical system action.

            Args:
                action: AuditLog.Actions choice value
                model_name: Name of the model being modified
                object_id: Primary key of the object (optional)
                object_repr: String representation of the object
                changes: Dict of changed fields (optional)
            """
            ip = self.get_client_ip(request)
            user_agent = request.headers.get("user-agent", "")[:500]

            AuditLog.objects.create(
                user=request.user if request.user.is_authenticated else None,
                action=action,
                model_name=model_name,
                object_id=object_id,
                object_repr=object_repr,
                changes=changes,
                ip_address=ip,
                user_agent=user_agent,
            )

        request.audit_log = audit_log
        return None

    @staticmethod
    def get_client_ip(request):
        """Extract client IP address from request, handling proxies."""
        x_forwarded_for = request.headers.get("x-forwarded-for")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0].strip()
        else:
            ip = request.META.get("REMOTE_ADDR")
        return ip
