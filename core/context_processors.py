from django.conf import settings


def app_version(request):
    """Make APP_VERSION available in all template contexts."""
    return {"APP_VERSION": settings.APP_VERSION}


def site_settings(request):
    """Make the admin-editable SiteSettings singleton available everywhere (#327)."""
    from school_menu.models import SiteSettings

    return {"site_settings": SiteSettings.get_solo()}
