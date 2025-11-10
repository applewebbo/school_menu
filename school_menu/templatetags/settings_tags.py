from django import template
from django.conf import settings

register = template.Library()


@register.simple_tag
def get_setting(name, default=None):
    """
    Get a setting value by name.

    Usage:
        {% load settings_tags %}
        {% get_setting 'UMAMI_SCRIPT_URL' as umami_url %}
        {% get_setting 'UMAMI_WEBSITE_ID' 'default-id' as website_id %}

    Args:
        name: The setting name to retrieve
        default: Optional default value if setting doesn't exist

    Returns:
        The setting value or default/None if not found
    """
    return getattr(settings, name, default)
