"""Development tooling must not leak into the production configuration (#243).

django-debug-toolbar used to sit in the production dependencies with its app and
middleware registered unconditionally: shipped in the image, in the middleware chain of
every real request, inert only because DEBUG was False. django-devbar replaces it and is
wired inside the dev block alone.
"""

from django.conf import settings
from django.urls import URLPattern, URLResolver, get_resolver


def _url_prefixes():
    def walk(patterns, prefix=""):
        for entry in patterns:
            route = prefix + str(getattr(entry.pattern, "_route", entry.pattern))
            if isinstance(entry, URLResolver):
                yield from walk(entry.url_patterns, route)
            elif isinstance(entry, URLPattern):
                yield route

    return list(walk(get_resolver().url_patterns))


def test_the_debug_toolbar_is_gone():
    assert "debug_toolbar" not in settings.INSTALLED_APPS
    assert not any("debug_toolbar" in entry for entry in settings.MIDDLEWARE)
    assert not any(route.startswith("__debug__") for route in _url_prefixes())


def test_devbar_is_not_wired_outside_development():
    """The suite runs with ENVIRONMENT=test, where no debugging middleware belongs."""
    assert not any("devbar" in entry for entry in settings.MIDDLEWARE)
