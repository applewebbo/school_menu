"""Guards on the static sources that only break at collectstatic time.

Production serves static files through whitenoise's CompressedManifestStaticFilesStorage,
which post-processes CSS and JS to rewrite every reference into its hashed name. A
reference pointing at a file that is not collected is not a warning there: it aborts
collectstatic, and with it the whole deploy. The suite never runs collectstatic, so
without these tests the failure surfaces for the first time in the container (#242).
"""

import re

from django.conf import settings
from django.contrib.staticfiles import finders

# Matches both the standard "//# sourceMappingURL=..." and the older "//@"/"// " spellings
# that some vendored bundles still carry.
SOURCE_MAPPING_URL = re.compile(r"//[#@]? *sourceMappingURL=(\S+)")
# The CSS side of the same problem. This deliberately mirrors Django's own pattern in
# HashedFilesMixin.patterns: non-greedy, so an inline SVG data URI containing its own
# url(#id) is consumed as a single match and skipped whole, rather than reported as a
# reference to a file named "%23a".
CSS_URL = re.compile(r"url\((.*?)\)")
# Prefixes HashedFilesMixin.url_converter leaves untouched.
SKIPPED_PREFIXES = ("data:", "http:", "https:", "//", "#")

STATIC_SOURCE = settings.BASE_DIR / "static"
TEMPLATE_SOURCE = settings.BASE_DIR / "templates"

# {% static 'path' %} / {% static "path" %}. A {% static some_var %} with a variable
# argument is left alone: there is no path to resolve at import time.
TEMPLATE_STATIC_REF = re.compile(r"""\{%\s*static\s+['"]([^'"]+)['"]""")


def _sources(suffix):
    return sorted(path for path in STATIC_SOURCE.rglob(f"*{suffix}") if path.is_file())


def test_no_js_references_a_missing_source_map():
    """A vendored bundle shipped without its .map aborts collectstatic."""
    missing = []
    for path in _sources(".js"):
        for reference in SOURCE_MAPPING_URL.findall(path.read_text(errors="replace")):
            if not (path.parent / reference).exists():
                missing.append(f"{path.relative_to(STATIC_SOURCE)} -> {reference}")

    assert not missing, "source map references with no file on disk: " + ", ".join(
        missing
    )


def test_no_css_references_a_missing_file():
    """A url() pointing nowhere aborts collectstatic just as a stale source map does."""
    missing = []
    for path in _sources(".css"):
        for match in CSS_URL.findall(path.read_text(errors="replace")):
            reference = match.strip().strip("'\"")
            if not reference or reference.startswith(SKIPPED_PREFIXES):
                continue
            target = (path.parent / reference.split("?")[0].split("#")[0]).resolve()
            if not target.exists():
                missing.append(f"{path.relative_to(STATIC_SOURCE)} -> {reference}")

    assert not missing, "url() references with no file on disk: " + ", ".join(missing)


def test_no_template_references_a_missing_static_file():
    """A {% static %} path that was never collected is a 500 at render time in prod.

    ManifestStaticFilesStorage.url() raises ValueError for any path missing from the
    manifest, so a stale reference takes down the page. Dev and test use the plain
    storage and render the broken URL without complaint, hiding it until the
    container (#242, #257).
    """
    missing = []
    for path in sorted(TEMPLATE_SOURCE.rglob("*.html")):
        for reference in TEMPLATE_STATIC_REF.findall(path.read_text(errors="replace")):
            if finders.find(reference) is None:
                missing.append(f"{path.relative_to(TEMPLATE_SOURCE)} -> {reference}")

    assert not missing, "{% static %} references with no file on disk: " + ", ".join(
        missing
    )
