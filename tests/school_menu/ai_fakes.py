"""
Fake extraction clients used in place of Gemini (#234).

`get_client()` resolves a dotted path from settings, so a test only has to point
`AI_MENU_IMPORT_CLIENT` at one of these classes to exercise the whole pipeline — view,
task and extraction — without a network call and without `unittest.mock`.

Each class records its calls on the class itself, because `get_client()` builds a fresh
instance every time and the test needs to inspect what was actually sent.
"""

from school_menu.ai.client import ExtractionResponse
from school_menu.ai.errors import ExtractionTimeout, UpstreamError

SIMPLE_PAYLOAD = """
{"righe": [
    {"giorno": "lunedi", "settimana": 1, "pranzo": "Pasta al pomodoro",
     "spuntino": "Mela", "merenda": "Yogurt"},
    {"giorno": "Martedì", "settimana": "1", "pranzo": "Riso", "spuntino": null,
     "merenda": "Pane"}
]}
"""

DETAILED_PAYLOAD = """
{"righe": [
    {"giorno": "lunedi", "settimana": 1, "primo": "Pasta", "secondo": "Pollo",
     "contorno": "Insalata", "frutta": "Mela", "spuntino": "Yogurt"}
]}
"""

ANNUAL_PAYLOAD = """
{"righe": [
    {"data": "02/09/2026", "primo": "Riso", "secondo": "Merluzzo", "contorno": "Patate",
     "frutta": "Pera", "altro": ""},
    {"data": "01/09/2026", "primo": "Pasta", "secondo": "Pollo", "contorno": "Insalata",
     "frutta": "Mela", "altro": null}
]}
"""

USAGE = {"total_tokens": 1234}


class BaseFakeClient:
    """Records every call so a test can assert on what was sent upstream."""

    calls: list = []

    @classmethod
    def reset(cls):
        cls.calls = []

    def _record(self, system_instruction, contents, schema):
        type(self).calls.append(
            {
                "system_instruction": system_instruction,
                "contents": contents,
                "schema": schema,
            }
        )

    def extract(self, *, system_instruction, contents, schema):
        raise NotImplementedError


class RecordingClient(BaseFakeClient):
    """Answers with whatever the test put in `text`."""

    calls: list = []
    text = SIMPLE_PAYLOAD

    def extract(self, *, system_instruction, contents, schema):
        self._record(system_instruction, contents, schema)
        return ExtractionResponse(text=type(self).text, usage=USAGE)


class InvalidJsonClient(BaseFakeClient):
    calls: list = []

    def extract(self, *, system_instruction, contents, schema):
        self._record(system_instruction, contents, schema)
        return ExtractionResponse(text="non sono JSON", usage=USAGE)


class WrongSchemaClient(BaseFakeClient):
    """Valid JSON, wrong shape: the top level key the schema requires is missing."""

    calls: list = []

    def extract(self, *, system_instruction, contents, schema):
        self._record(system_instruction, contents, schema)
        return ExtractionResponse(text='{"menu": ["Pasta"]}', usage=USAGE)


class EmptyClient(BaseFakeClient):
    """Well formed answer, but no row survives normalisation."""

    calls: list = []

    def extract(self, *, system_instruction, contents, schema):
        self._record(system_instruction, contents, schema)
        return ExtractionResponse(
            text='{"righe": [{"giorno": "Domenica", "settimana": 9}]}', usage=USAGE
        )


class UpstreamErrorClient(BaseFakeClient):
    calls: list = []

    def extract(self, *, system_instruction, contents, schema):
        self._record(system_instruction, contents, schema)
        raise UpstreamError("503")


class TimeoutClient(BaseFakeClient):
    calls: list = []

    def extract(self, *, system_instruction, contents, schema):
        self._record(system_instruction, contents, schema)
        raise ExtractionTimeout()


class FlakyClient(BaseFakeClient):
    """Fails once with a transient error, then answers."""

    calls: list = []

    def extract(self, *, system_instruction, contents, schema):
        self._record(system_instruction, contents, schema)
        if len(type(self).calls) == 1:
            raise UpstreamError("429")
        return ExtractionResponse(text=SIMPLE_PAYLOAD, usage=USAGE)
