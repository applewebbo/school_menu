"""Tests for the AI extraction pipeline: schemas, prompts and orchestration (#234)."""

import base64
import io
from types import SimpleNamespace

import httpx
import pytest
from django.test import override_settings
from google.genai._gaos.errors import GenAiError, NoResponseError
from google.genai._gaos.lib.compat_errors import APIConnectionError, APITimeoutError
from google.genai._gaos.lib.compat_errors import APIError as CompatAPIError
from google.genai._gaos.types.interactions.documentcontent import DocumentContent
from google.genai._gaos.types.interactions.usage import Usage
from google.genai.errors import APIError
from openpyxl import Workbook
from pydantic import ValidationError

from school_menu.ai import prompts, schemas
from school_menu.ai.client import ExtractionResponse, GeminiClient, get_client
from school_menu.ai.errors import (
    AIDisabled,
    EmptyResult,
    ExtractionTimeout,
    InvalidResponse,
    UnsupportedFile,
    UpstreamError,
)
from school_menu.ai.extraction import extract_menu
from school_menu.models import MenuImportDraft
from tests.school_menu import ai_fakes

SIMPLE = MenuImportDraft.Kinds.SIMPLE
DETAILED = MenuImportDraft.Kinds.DETAILED
ANNUAL = MenuImportDraft.Kinds.ANNUAL

FAKES = "tests.school_menu.ai_fakes."

# The SDK's own error classes all carry the request that failed.
REQUEST = httpx.Request("POST", "https://example.invalid/")


def use(client_class, **extra):
    """Point the client seam at a fake and keep the rest of the AI settings sane."""
    ai_fakes.RecordingClient.text = ai_fakes.SIMPLE_PAYLOAD
    for cls in vars(ai_fakes).values():
        if isinstance(cls, type) and issubclass(cls, ai_fakes.BaseFakeClient):
            cls.reset()
    options = {
        "AI_MENU_IMPORT_CLIENT": FAKES + client_class,
        "AI_MENU_IMPORT_MAX_RETRIES": 1,
    }
    options.update(extra)
    return override_settings(**options)


def xlsx_bytes(sheets):
    """Build a workbook in memory: {sheet title: [[row], ...]}."""
    workbook = Workbook()
    workbook.remove(workbook.active)
    for title, rows in sheets.items():
        sheet = workbook.create_sheet(title=title)
        for row in rows:
            sheet.append(row)
    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


class TestSchemas:
    @pytest.mark.parametrize(
        "kind,expected",
        [
            (SIMPLE, {"giorno", "settimana", "pranzo", "spuntino", "merenda"}),
            (
                DETAILED,
                {
                    "giorno",
                    "settimana",
                    "primo",
                    "secondo",
                    "contorno",
                    "frutta",
                    "spuntino",
                },
            ),
            (ANNUAL, {"data", "primo", "secondo", "contorno", "frutta", "altro"}),
        ],
    )
    def test_row_columns_match_the_csv_headers(self, kind, expected):
        """The rows must be usable by the CSV resources without renaming anything."""
        assert set(schemas.row_model(kind).model_fields) == expected

    def test_json_schema_is_a_flat_object_of_strings(self):
        """anyOf and integers are what structured output most often gets wrong."""
        schema = schemas.json_schema(SIMPLE)
        row = schema["$defs"]["SimpleRow"]["properties"]

        assert all(field["type"] == "string" for field in row.values())

    def test_numbers_and_nulls_are_accepted(self):
        payload = schemas.parse(SIMPLE, ai_fakes.SIMPLE_PAYLOAD)

        assert payload[0]["settimana"] == "1"
        assert payload[1]["spuntino"] == ""

    def test_absent_optional_columns_default_to_empty(self):
        payload = schemas.parse(SIMPLE, '{"righe": [{"giorno": "Lunedì"}]}')

        assert payload[0]["pranzo"] == ""

    def test_wrong_top_level_shape_is_rejected(self):
        with pytest.raises(ValidationError):
            schemas.parse(SIMPLE, '{"menu": []}')


class TestPrompts:
    @pytest.mark.parametrize("kind", [SIMPLE, DETAILED, ANNUAL])
    def test_every_column_is_named_in_the_instruction(self, kind):
        instruction = prompts.build_system_instruction(kind)

        for column in schemas.row_model(kind).model_fields:
            assert column in instruction

    def test_weekly_instruction_states_the_week_range(self):
        assert "1" in prompts.build_system_instruction(SIMPLE)
        assert "settimana" in prompts.build_system_instruction(SIMPLE)

    def test_annual_instruction_states_the_date_format(self):
        assert "GG/MM/AAAA" in prompts.build_system_instruction(ANNUAL)


class TestExtraction:
    def test_simple_rows_are_normalised(self):
        with use("RecordingClient"):
            result = extract_menu(SIMPLE, b"contenuto", "menu.csv")

        assert result.rows[0]["giorno"] == "Lunedì"
        assert result.rows[0]["settimana"] == 1
        assert result.usage == ai_fakes.USAGE

    def test_detailed_rows_are_normalised(self):
        with use("RecordingClient"):
            ai_fakes.RecordingClient.text = ai_fakes.DETAILED_PAYLOAD
            result = extract_menu(DETAILED, b"contenuto", "menu.csv")

        assert result.rows[0]["secondo"] == "Pollo"

    def test_annual_rows_are_sorted_by_date(self):
        with use("RecordingClient"):
            ai_fakes.RecordingClient.text = ai_fakes.ANNUAL_PAYLOAD
            result = extract_menu(ANNUAL, b"contenuto", "menu.csv")

        assert [row["data"] for row in result.rows] == ["01/09/2026", "02/09/2026"]

    def test_normalisation_warnings_are_returned(self):
        with use("RecordingClient"):
            ai_fakes.RecordingClient.text = (
                '{"righe": [{"giorno": "Lunedì", "settimana": 1},'
                ' {"giorno": "Sabato", "settimana": 1}]}'
            )
            result = extract_menu(SIMPLE, b"contenuto", "menu.csv")

        assert result.warnings


class TestFilePreparation:
    def test_pdf_is_sent_as_an_inline_document(self):
        with use("RecordingClient"):
            extract_menu(SIMPLE, b"%PDF-1.4 finto", "menu.pdf")

        content = ai_fakes.RecordingClient.calls[0]["contents"][0]
        assert content["type"] == "document"
        assert content["mime_type"] == "application/pdf"
        assert base64.b64decode(content["data"]) == b"%PDF-1.4 finto"

    def test_the_document_payload_is_what_the_sdk_accepts(self):
        """
        Validate our payload against the SDK's own type, not against our idea of it.

        `data` is a `Base64EncodedString`: raw bytes pass straight through its validator
        and pydantic then tries to decode them as UTF-8, which no real PDF survives. That
        only surfaced against the live API, so the contract is pinned here.
        """
        with use("RecordingClient"):
            extract_menu(SIMPLE, b"%PDF-1.4 \x93\xff binario", "menu.pdf")

        content = ai_fakes.RecordingClient.calls[0]["contents"][0]
        DocumentContent.model_validate(content).model_dump(
            by_alias=True, mode="json", exclude_none=True
        )

    def test_csv_is_sent_as_text(self):
        with use("RecordingClient"):
            extract_menu(SIMPLE, "giorno;pranzo\nLunedì;Pasta".encode(), "menu.csv")

        content = ai_fakes.RecordingClient.calls[0]["contents"][0]
        assert content["type"] == "text"
        assert "Lunedì;Pasta" in content["text"]

    def test_latin1_csv_is_decoded_instead_of_failing(self):
        with use("RecordingClient"):
            extract_menu(SIMPLE, "Lunedì;Pasta".encode("latin-1"), "menu.csv")

        assert "Pasta" in ai_fakes.RecordingClient.calls[0]["contents"][0]["text"]

    def test_utf8_bom_is_stripped(self):
        with use("RecordingClient"):
            extract_menu(SIMPLE, "giorno".encode("utf-8-sig"), "menu.csv")

        text = ai_fakes.RecordingClient.calls[0]["contents"][0]["text"]
        assert "﻿" not in text

    def test_text_is_truncated_to_the_configured_limit(self):
        with use("RecordingClient", AI_MENU_IMPORT_MAX_TEXT_CHARS=50):
            extract_menu(SIMPLE, b"a" * 500, "menu.txt")

        assert len(ai_fakes.RecordingClient.calls[0]["contents"][0]["text"]) == 50

    def test_every_xlsx_sheet_is_included(self):
        """tablib only reads the first sheet, and menus routinely use one sheet per week."""
        content = xlsx_bytes(
            {
                "Settimana 1": [["giorno", "pranzo"], ["Lunedì", "Pasta"]],
                "Settimana 2": [["giorno", "pranzo"], ["Lunedì", "Riso"]],
            }
        )

        with use("RecordingClient"):
            extract_menu(SIMPLE, content, "menu.xlsx")

        text = ai_fakes.RecordingClient.calls[0]["contents"][0]["text"]
        assert "Settimana 1" in text
        assert "Riso" in text

    def test_empty_xlsx_cells_do_not_become_none(self):
        content = xlsx_bytes({"Foglio": [["Lunedì", None, "Pasta"]]})

        with use("RecordingClient"):
            extract_menu(SIMPLE, content, "menu.xlsx")

        assert "None" not in ai_fakes.RecordingClient.calls[0]["contents"][0]["text"]

    def test_unreadable_xlsx_is_rejected_before_spending_anything(self):
        with use("RecordingClient"), pytest.raises(UnsupportedFile):
            extract_menu(SIMPLE, b"non sono uno xlsx", "menu.xlsx")

        assert ai_fakes.RecordingClient.calls == []

    @pytest.mark.parametrize("filename", ["menu.docx", "menu.jpg", "menu", "menu.xls"])
    def test_unsupported_extension_is_refused(self, filename):
        with use("RecordingClient"), pytest.raises(UnsupportedFile):
            extract_menu(SIMPLE, b"contenuto", filename)

        assert ai_fakes.RecordingClient.calls == []

    def test_extension_matching_ignores_case(self):
        with use("RecordingClient"):
            extract_menu(SIMPLE, b"%PDF", "MENU.PDF")

        assert ai_fakes.RecordingClient.calls


class TestFailures:
    def test_malformed_json_is_an_invalid_response(self):
        with use("InvalidJsonClient"), pytest.raises(InvalidResponse):
            extract_menu(SIMPLE, b"contenuto", "menu.csv")

    def test_wrong_schema_is_an_invalid_response(self):
        with use("WrongSchemaClient"), pytest.raises(InvalidResponse):
            extract_menu(SIMPLE, b"contenuto", "menu.csv")

    def test_no_usable_row_is_an_empty_result(self):
        with use("EmptyClient"), pytest.raises(EmptyResult):
            extract_menu(SIMPLE, b"contenuto", "menu.csv")

    def test_an_unusable_answer_is_never_retried(self):
        """It cost tokens once already: retrying is spending twice for the same answer."""
        with use("InvalidJsonClient"), pytest.raises(InvalidResponse):
            extract_menu(SIMPLE, b"contenuto", "menu.csv")

        assert len(ai_fakes.InvalidJsonClient.calls) == 1

    def test_a_transient_error_is_retried_once_and_can_succeed(self):
        with use("FlakyClient"):
            result = extract_menu(SIMPLE, b"contenuto", "menu.csv")

        assert len(ai_fakes.FlakyClient.calls) == 2
        assert result.rows

    def test_a_persistent_upstream_error_gives_up_after_the_retries(self):
        with use("UpstreamErrorClient"), pytest.raises(UpstreamError):
            extract_menu(SIMPLE, b"contenuto", "menu.csv")

        assert len(ai_fakes.UpstreamErrorClient.calls) == 2

    def test_retries_are_configurable(self):
        with (
            use("UpstreamErrorClient", AI_MENU_IMPORT_MAX_RETRIES=0),
            pytest.raises(UpstreamError),
        ):
            extract_menu(SIMPLE, b"contenuto", "menu.csv")

        assert len(ai_fakes.UpstreamErrorClient.calls) == 1


class TestClientSeam:
    def test_the_client_is_resolved_from_settings(self):
        with use("RecordingClient"):
            assert isinstance(get_client(), ai_fakes.RecordingClient)

    @override_settings(
        AI_MENU_IMPORT_CLIENT="school_menu.ai.client.GeminiClient", GEMINI_API_KEY=""
    )
    def test_without_an_api_key_nothing_is_attempted(self):
        with pytest.raises(AIDisabled):
            get_client()

    def test_response_carries_text_and_usage(self):
        response = ExtractionResponse(text="{}", usage={"total_tokens": 1})

        assert response.text == "{}"
        assert response.usage["total_tokens"] == 1


class TestGeminiClient:
    """
    The real client, with `_call` — its only networked line — replaced by a subclass.

    Everything around that line is ours: what comes back, and how a transport failure
    becomes an error the user can read.
    """

    def build(self, outcome):
        class Client(GeminiClient):
            def _call(self, system_instruction, contents, schema):
                if isinstance(outcome, Exception):
                    raise outcome
                return outcome

        with override_settings(GEMINI_API_KEY="chiave-di-prova"):
            return Client()

    def test_output_text_and_usage_are_returned(self):
        usage = Usage(total_tokens=99)
        response = self.build(
            SimpleNamespace(output_text='{"righe": []}', usage=usage)
        ).extract(system_instruction="", contents=[], schema={})

        assert response.text == '{"righe": []}'
        assert response.usage["total_tokens"] == 99

    def test_a_missing_answer_is_not_a_crash(self):
        response = self.build(SimpleNamespace(output_text=None, usage=None)).extract(
            system_instruction="", contents=[], schema={}
        )

        assert response.text == ""
        assert response.usage == {}

    @pytest.mark.parametrize(
        "raised",
        [
            httpx.ConnectTimeout("lenta"),
            NoResponseError("nessuna risposta"),
            # The SDK wraps transport failures in its own hierarchy, unrelated to httpx
            # and to google.genai.errors: uncaught, these escape as UNKNOWN, which is not
            # refundable and is not retried.
            APITimeoutError(REQUEST),
        ],
    )
    def test_no_answer_in_time_is_a_timeout(self, raised):
        with pytest.raises(ExtractionTimeout):
            self.build(raised).extract(system_instruction="", contents=[], schema={})

    @pytest.mark.parametrize(
        "raised",
        [
            GenAiError("errore", httpx.Response(500)),
            APIError(503, {"message": "non disponibile"}),
            httpx.ConnectError("rete assente"),
            CompatAPIError("errore dell'sdk", REQUEST, body=None),
            APIConnectionError(message="connessione caduta", request=REQUEST),
        ],
    )
    def test_a_transport_failure_is_an_upstream_error(self, raised):
        with pytest.raises(UpstreamError):
            self.build(raised).extract(system_instruction="", contents=[], schema={})
