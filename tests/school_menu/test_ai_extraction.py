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

from school_menu.ai import normalise, prompts, schemas
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
from school_menu.models import Meal, MenuImportDraft
from tests.school_menu import ai_fakes

SIMPLE = MenuImportDraft.Kinds.SIMPLE
DETAILED = MenuImportDraft.Kinds.DETAILED
ANNUAL = MenuImportDraft.Kinds.ANNUAL

INVERNALE = Meal.Seasons.INVERNALE
ESTIVO = Meal.Seasons.ESTIVO

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
        row = schemas.json_schema(SIMPLE)["properties"]["righe"]["items"]

        assert all(field["type"] == "string" for field in row["properties"].values())

    @pytest.mark.parametrize("kind", [SIMPLE, DETAILED, ANNUAL])
    def test_every_row_field_is_required(self, kind):
        """
        A partial row is how one day ends up split across two objects.

        Seen live: the model returned the same day twice, once with only `spuntino` and
        once with only `pranzo`. Requiring every field makes a row complete or invalid.
        """
        row = schemas.json_schema(kind)["properties"]["righe"]["items"]

        assert set(row["required"]) == set(row["properties"])

    @pytest.mark.parametrize("kind", [SIMPLE, DETAILED, ANNUAL])
    def test_the_row_shape_is_inlined(self, kind):
        """Gemini's handling of $ref in structured output is not dependable."""
        schema = schemas.json_schema(kind)

        assert "$defs" not in schema
        assert "$ref" not in str(schema)

    @pytest.mark.parametrize("kind", [SIMPLE, DETAILED, ANNUAL])
    def test_every_field_is_length_capped(self, kind):
        """
        Without an upper bound nothing stops a runaway generation.

        Seen live: one row whose `spuntino` was thousands of repeated zeroes, three times
        the output tokens of a good answer.
        """
        row = schemas.json_schema(kind)["properties"]["righe"]["items"]

        assert all("maxLength" in field for field in row["properties"].values())
        for column, max_length in normalise.COLUMNS[kind].items():
            assert row["properties"][column]["maxLength"] == max_length

    def test_numbers_and_nulls_are_accepted(self):
        parsed = schemas.parse(SIMPLE, ai_fakes.SIMPLE_PAYLOAD)

        assert parsed.rows[0]["settimana"] == "1"
        assert parsed.rows[1]["spuntino"] == ""

    def test_absent_optional_columns_default_to_empty(self):
        parsed = schemas.parse(SIMPLE, '{"righe": [{"giorno": "Lunedì"}]}')

        assert parsed.rows[0]["pranzo"] == ""

    def test_an_absent_season_parses_as_empty(self):
        assert schemas.parse(SIMPLE, '{"righe": []}').season == ""

    def test_the_annual_shape_has_no_season(self):
        """An annual menu is tied to dates, so there is no season to report."""
        assert "stagione" not in schemas.json_schema(ANNUAL)["properties"]

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

    @pytest.mark.parametrize(
        "season,wanted,other",
        [
            (INVERNALE, "invernale", "primaverile-estivo"),
            (ESTIVO, "primaverile-estivo", "invernale"),
        ],
    )
    def test_the_requested_season_is_named_in_the_instruction(
        self, season, wanted, other
    ):
        """Schools publish both seasons in one file; the model has to know which to take."""
        instruction = prompts.build_system_instruction(SIMPLE, season=season)

        assert wanted in instruction
        assert other in instruction  # named too, so it can be told apart and skipped

    def test_without_a_season_the_instruction_is_unchanged(self):
        assert prompts.build_system_instruction(SIMPLE, season=None) == (
            prompts.build_system_instruction(SIMPLE)
        )

    def test_the_annual_instruction_ignores_the_season(self):
        """An annual menu is tied to dates: seasons do not apply."""
        assert prompts.build_system_instruction(ANNUAL, season=INVERNALE) == (
            prompts.build_system_instruction(ANNUAL)
        )


class TestSeasonMismatch:
    """A file holding both seasons must not import the wrong one in silence."""

    def payload(self, season):
        return (
            '{"stagione": "%s", "righe": [{"giorno": "Lunedì", "settimana": "1", '
            '"pranzo": "Pasta", "spuntino": "Mela", "merenda": "Yogurt"}]}' % season
        )

    def test_a_diverging_season_is_reported(self):
        with use("RecordingClient"):
            ai_fakes.RecordingClient.text = self.payload("primaverile-estivo")
            result = extract_menu(SIMPLE, b"contenuto", "menu.csv", season=INVERNALE)

        assert result.rows, "the rows stay editable: the user decides what to do"
        assert any(
            "primaverile-estivo" in w and "invernale" in w for w in result.warnings
        )

    def test_the_matching_season_says_nothing(self):
        with use("RecordingClient"):
            ai_fakes.RecordingClient.text = self.payload("invernale")
            result = extract_menu(SIMPLE, b"contenuto", "menu.csv", season=INVERNALE)

        assert not result.warnings

    def test_an_unstated_season_says_nothing(self):
        """Most documents do not name the season at all."""
        with use("RecordingClient"):
            ai_fakes.RecordingClient.text = self.payload("")
            result = extract_menu(SIMPLE, b"contenuto", "menu.csv", season=INVERNALE)

        assert not result.warnings

    def test_no_usable_row_blames_the_season_rather_than_the_file(self):
        """
        Otherwise the user reads "could not read the menu" and has no idea why.

        This is the case that costs a quota slot with nothing to show for it, so the
        message has to point at the one thing the user can act on.
        """
        with use("RecordingClient"):
            ai_fakes.RecordingClient.text = (
                '{"stagione": "primaverile-estivo", "righe": []}'
            )
            with pytest.raises(EmptyResult) as raised:
                extract_menu(SIMPLE, b"contenuto", "menu.csv", season=INVERNALE)

        assert "primaverile-estivo" in raised.value.user_message

    def test_no_usable_row_never_points_at_rows_that_do_not_exist(self):
        """
        The warning is written for the preview, where the rows are listed underneath.
        On the empty path there is no preview and no row, so reusing it verbatim sends
        the user to inspect something that is not there (#244).
        """
        with use("RecordingClient"):
            ai_fakes.RecordingClient.text = (
                '{"stagione": "primaverile-estivo", "righe": []}'
            )
            with pytest.raises(EmptyResult) as raised:
                extract_menu(SIMPLE, b"contenuto", "menu.csv", season=INVERNALE)

        message = raised.value.user_message
        assert "qui sotto" not in message
        assert "invernale" in message and "primaverile-estivo" in message

    def test_the_warning_still_points_at_the_rows_when_there_are_some(self):
        with use("RecordingClient"):
            ai_fakes.RecordingClient.text = self.payload("primaverile-estivo")
            result = extract_menu(SIMPLE, b"contenuto", "menu.csv", season=INVERNALE)

        assert any("qui sotto" in warning for warning in result.warnings)

    def test_no_usable_row_without_a_season_keeps_the_generic_message(self):
        with use("EmptyClient"):
            with pytest.raises(EmptyResult) as raised:
                extract_menu(SIMPLE, b"contenuto", "menu.csv", season=INVERNALE)

        assert raised.value.user_message == EmptyResult().user_message


class TestKindMismatch:
    """
    The kind comes from the school, never from the file, so a mismatch cannot fail loudly.

    Only the divergences that actually cost the user anything are worth a warning. A
    detailed document imported into a simple school is collapsed into `pranzo` by design,
    so that one stays silent.
    """

    WEEKLY_ROW = (
        '{"giorno": "Lunedì", "settimana": "1", "pranzo": "Pasta", '
        '"spuntino": "Mela", "merenda": "Yogurt"}'
    )

    def payload(self, tipo, rows=None):
        return '{{"tipo": "{}", "stagione": "", "righe": [{}]}}'.format(
            tipo,
            self.WEEKLY_ROW if rows is None else rows,
        )

    def test_an_annual_document_in_a_weekly_school_is_reported(self):
        with use("RecordingClient"):
            ai_fakes.RecordingClient.text = self.payload("annuale")
            result = extract_menu(SIMPLE, b"contenuto", "menu.csv")

        assert result.rows, "the rows stay editable"
        assert "annuale" in result.warnings[0]

    def test_a_weekly_document_in_an_annual_school_is_reported(self):
        with use("RecordingClient"):
            ai_fakes.RecordingClient.text = (
                '{"tipo": "settimanale_semplice", "righe": '
                '[{"data": "01/09/2026", "primo": "Pasta", "secondo": "", '
                '"contorno": "", "frutta": "", "altro": ""}]}'
            )
            result = extract_menu(ANNUAL, b"contenuto", "menu.csv")

        assert "settimanale" in result.warnings[0]

    def test_a_simple_document_in_a_detailed_school_is_reported(self):
        """The model has to split one blob into five columns: some will come back empty."""
        with use("RecordingClient"):
            ai_fakes.RecordingClient.text = self.payload(
                "settimanale_semplice",
                '{"giorno": "Lunedì", "settimana": "1", "primo": "Pasta", '
                '"secondo": "", "contorno": "", "frutta": "", "spuntino": ""}',
            )
            result = extract_menu(DETAILED, b"contenuto", "menu.csv")

        assert result.warnings

    def test_a_detailed_document_in_a_simple_school_says_nothing(self):
        """Collapsing the courses into `pranzo` is what the simple menu is meant to do."""
        with use("RecordingClient"):
            ai_fakes.RecordingClient.text = self.payload("settimanale_dettagliato")
            result = extract_menu(SIMPLE, b"contenuto", "menu.csv")

        assert not result.warnings

    def test_the_matching_kind_says_nothing(self):
        with use("RecordingClient"):
            ai_fakes.RecordingClient.text = self.payload("settimanale_semplice")
            result = extract_menu(SIMPLE, b"contenuto", "menu.csv")

        assert not result.warnings

    def test_an_unknown_kind_says_nothing(self):
        """An older model that does not return the field must not break the import."""
        with use("RecordingClient"):
            ai_fakes.RecordingClient.text = self.payload("qualcos'altro")
            result = extract_menu(SIMPLE, b"contenuto", "menu.csv")

        assert result.rows
        assert not result.warnings

    def test_no_usable_row_blames_the_kind_rather_than_the_file(self):
        with use("RecordingClient"):
            ai_fakes.RecordingClient.text = self.payload("annuale", rows="")
            with pytest.raises(EmptyResult) as raised:
                extract_menu(SIMPLE, b"contenuto", "menu.csv")

        assert "annuale" in raised.value.user_message

    def test_no_usable_row_never_points_at_rows_that_do_not_exist(self):
        """Same defect as the season message, on the kind axis (#244)."""
        with use("RecordingClient"):
            ai_fakes.RecordingClient.text = self.payload(
                "settimanale_semplice", rows=""
            )
            with pytest.raises(EmptyResult) as raised:
                extract_menu(DETAILED, b"contenuto", "menu.csv")

        message = raised.value.user_message
        assert "vuote o divise male" not in message
        assert "dettagliato" in message

    def test_the_kind_outranks_the_season_when_both_diverge(self):
        """Reconfiguring the school comes first: the season is picked at upload time."""
        with use("RecordingClient"):
            ai_fakes.RecordingClient.text = (
                '{"tipo": "annuale", "stagione": "primaverile-estivo", "righe": [%s]}'
                % self.WEEKLY_ROW
            )
            result = extract_menu(SIMPLE, b"contenuto", "menu.csv", season=INVERNALE)

        assert "annuale" in result.warnings[0]
        assert len(result.warnings) == 2


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
