from django.shortcuts import render
from rest_framework.views import exception_handler


def custom_exception_handler(exc, context):
    """Custom exception handler with Italian messages for rate limiting."""
    response = exception_handler(exc, context)

    if response is not None and response.status_code == 429:
        request = context.get("request")
        if request and not _is_api_request(request):
            return render(request, "429.html", status=429)
        response.data = {
            "error": "Troppe richieste",
            "detail": "Hai superato il limite di richieste consentite.",
            "retry_after": response.get("Retry-After", 3600),
        }

    return response


def _is_api_request(request) -> bool:
    """Return True if the request expects a JSON response."""
    accept = request.headers.get("accept", "")
    return "application/json" in accept or request.path.startswith("/api/")
