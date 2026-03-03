from django.conf import settings


def app_version(request):
    """Make APP_VERSION available in all template contexts."""
    return {"APP_VERSION": settings.APP_VERSION}
