from rest_framework.views import exception_handler


def custom_exception_handler(exc, context):
    """Custom exception handler with Italian messages for rate limiting."""
    response = exception_handler(exc, context)

    if response is not None and response.status_code == 429:
        response.data = {
            "error": "Troppe richieste",
            "detail": "Hai superato il limite di richieste consentite.",
            "retry_after": response.get("Retry-After", 3600),
        }

    return response
