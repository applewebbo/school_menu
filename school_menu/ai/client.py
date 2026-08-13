"""
The seam between the import pipeline and Gemini (#234).

`get_client()` resolves a dotted path from `settings.AI_MENU_IMPORT_CLIENT`, so tests
point it at a fake and exercise the whole pipeline without a network call — and so a
different provider can be swapped in without touching the callers.

The client's only job is: send, and translate transport failures into the error taxonomy.
Everything about what to send and what to do with the answer lives elsewhere.
"""

from dataclasses import dataclass, field
from typing import Protocol

import httpx
from django.conf import settings
from django.utils.module_loading import import_string
from google import genai
from google.genai._gaos.errors import GenAiError, NoResponseError
from google.genai._gaos.lib.compat_errors import (
    APITimeoutError,
    GeminiNextGenAPIClientError,
)
from google.genai.errors import APIError

from school_menu.ai.errors import AIDisabled, ExtractionTimeout, UpstreamError


@dataclass(frozen=True)
class ExtractionResponse:
    """What the model answered, plus what it cost."""

    text: str
    usage: dict = field(default_factory=dict)


class MenuExtractionClient(Protocol):
    """Anything that can turn a document into raw JSON text."""

    def extract(
        self, *, system_instruction: str, contents: list, schema: dict
    ) -> ExtractionResponse: ...


class GeminiClient:
    """Single-shot call to the Gemini interactions API."""

    def __init__(self):
        if not settings.GEMINI_API_KEY:
            raise AIDisabled()
        self._client = genai.Client(api_key=settings.GEMINI_API_KEY)

    def extract(self, *, system_instruction, contents, schema):
        try:
            interaction = self._call(system_instruction, contents, schema)
        # The SDK raises from three unrelated hierarchies: httpx, google.genai.errors and
        # its own compat layer (rooted at GeminiNextGenAPIClientError, which descends from
        # plain Exception). Missing one means the failure escapes as UNKNOWN: not
        # refundable, and not retried.
        except (httpx.TimeoutException, NoResponseError, APITimeoutError) as exc:
            raise ExtractionTimeout(str(exc)) from exc
        except (
            GenAiError,
            APIError,
            GeminiNextGenAPIClientError,
            httpx.HTTPError,
        ) as exc:
            raise UpstreamError(str(exc)) from exc
        return ExtractionResponse(
            text=interaction.output_text or "",
            usage=interaction.usage.model_dump(mode="json")
            if interaction.usage
            else {},
        )

    def _call(self, system_instruction, contents, schema):  # pragma: no cover
        # The only line that needs the network, kept alone so everything around it stays
        # testable: covering it would mean either a real API call or mocking the SDK.
        return self._client.interactions.create(
            model=settings.GEMINI_MODEL,
            system_instruction=system_instruction,
            input=contents,
            response_format={
                "type": "text",
                "mime_type": "application/json",
                "schema": schema,
            },
            timeout=settings.AI_MENU_IMPORT_HTTP_TIMEOUT,
        )


def get_client() -> MenuExtractionClient:
    """Build the configured extraction client."""
    return import_string(settings.AI_MENU_IMPORT_CLIENT)()
