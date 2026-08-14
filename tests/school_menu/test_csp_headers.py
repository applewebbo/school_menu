import pytest

pytestmark = pytest.mark.django_db


class TestCSPHeaders:
    """Test Content Security Policy headers."""

    def test_csp_nonce_generation(self, rf):
        """Test CSP middleware generates nonce."""
        from csp.middleware import CSPMiddleware
        from django.http import HttpResponse

        def get_response(request):
            return HttpResponse("test")

        request = rf.get("/")
        middleware = CSPMiddleware(get_response)
        middleware.process_request(request)

        assert hasattr(request, "csp_nonce")
        assert len(request.csp_nonce) > 0
        assert isinstance(request.csp_nonce, str)

    def test_csp_nonce_unique_per_request(self, rf):
        """Test each request gets a unique CSP nonce."""
        from csp.middleware import CSPMiddleware
        from django.http import HttpResponse

        def get_response(request):
            return HttpResponse("test")

        middleware = CSPMiddleware(get_response)

        request1 = rf.get("/")
        middleware.process_request(request1)
        nonce1 = request1.csp_nonce

        request2 = rf.get("/")
        middleware.process_request(request2)
        nonce2 = request2.csp_nonce

        assert nonce1 != nonce2

    def test_base_template_uses_dynamic_nonce(self, client):
        """Test base.html uses dynamic nonce instead of hardcoded value."""
        response = client.get("/")
        content = response.content.decode("utf-8")

        # Should not contain hardcoded nonce
        assert 'nonce="6qSLf5Dz"' not in content

    def test_the_facebook_sdk_is_not_loaded(self, client):
        """
        django-social-share renders a plain <a href> to the sharer, so the SDK was never
        needed. Loading it on every page bought a console error and a third-party request
        firing before the cookie banner had asked anything (#240).
        """
        from pathlib import Path

        base_template = Path("templates/base.html").read_text()
        content = client.get("/").content.decode("utf-8")

        assert "connect.facebook.net" not in base_template
        assert 'id="fb-root"' not in base_template
        assert "connect.facebook.net" not in content

    def test_alpine_script_has_nonce_placeholder(self):
        """Test Alpine.js script has nonce placeholder in template."""
        from pathlib import Path

        base_template = Path("templates/base.html").read_text()

        # Check Alpine script has dynamic nonce
        assert '<script nonce="{{ request.csp_nonce }}">' in base_template
        assert "Alpine.magic('tooltip'" in base_template


class TestCSPConfiguration:
    """Test CSP configuration settings."""

    def test_csp_middleware_installed(self):
        """Test CSP middleware is installed."""
        from django.conf import settings

        assert "csp.middleware.CSPMiddleware" in settings.MIDDLEWARE

    def test_csp_report_only_enabled(self):
        """Test CSP is in report-only mode."""
        from django.conf import settings

        assert settings.CSP_REPORT_ONLY is True

    def test_csp_default_src_configured(self):
        """Test CSP default-src is configured."""
        from django.conf import settings

        assert hasattr(settings, "CSP_DEFAULT_SRC")
        assert "'self'" in settings.CSP_DEFAULT_SRC

    def test_csp_script_src_configured(self):
        """Test CSP script-src includes required sources."""
        from django.conf import settings

        assert hasattr(settings, "CSP_SCRIPT_SRC")
        assert "'self'" in settings.CSP_SCRIPT_SRC
        assert "'nonce-{nonce}'" in settings.CSP_SCRIPT_SRC

    def test_no_facebook_origin_is_allowed(self):
        """Nothing loads from Facebook any more: the allowances went with the SDK (#240)."""
        from django.conf import settings

        assert "https://connect.facebook.net" not in settings.CSP_SCRIPT_SRC
        assert "https://www.facebook.com" not in settings.CSP_FRAME_SRC
