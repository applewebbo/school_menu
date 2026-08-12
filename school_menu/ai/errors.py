"""
Failure taxonomy for the AI menu import (#234).

Each error carries a stable code (stored on the draft), an Italian message shown to the
user, and whether the quota slot should be given back. The rule for `refundable`: give
the slot back only when Gemini produced nothing billable. A malformed or empty answer
still burned tokens upstream, so it must keep costing the user a slot — otherwise a file
the model cannot read becomes an unlimited retry loop.
"""


class AIImportError(Exception):
    """Base class: never raised directly."""

    code = "UNKNOWN"
    user_message = (
        "Non è stato possibile interpretare il file. Riprova o carica un CSV."
    )
    refundable = False

    def __init__(self, message="", *, user_message=""):
        self.user_message = user_message or self.user_message
        super().__init__(message or self.user_message)


class AIDisabled(AIImportError):
    """No API key configured, so no request was ever made."""

    code = "AI_DISABLED"
    user_message = (
        "L'importazione assistita non è al momento disponibile. Carica un file CSV."
    )
    refundable = True


class UnsupportedFile(AIImportError):
    """Extension or size we refuse before spending anything."""

    code = "UNSUPPORTED"
    user_message = "Formato del file non supportato."
    refundable = True


class UpstreamError(AIImportError):
    """Gemini answered with an error, or could not be reached."""

    code = "UPSTREAM"
    user_message = "Il servizio di interpretazione non è raggiungibile. Riprova fra qualche minuto."
    refundable = True


class ExtractionTimeout(AIImportError):
    """The call did not come back in time."""

    code = "TIMEOUT"
    user_message = "L'interpretazione ha impiegato troppo tempo. Riprova."
    refundable = True


class InvalidResponse(AIImportError):
    """Answer received but unusable: not JSON, or not matching the schema."""

    code = "INVALID_RESPONSE"
    user_message = (
        "Il file non è stato interpretato correttamente. "
        "Prova con un file più leggibile oppure carica un CSV."
    )
    refundable = False


class EmptyResult(AIImportError):
    """Answer received and valid, but no usable row survived normalisation."""

    code = "EMPTY"
    user_message = (
        "Non è stato trovato nessun menu valido nel file. "
        "Verifica che contenga i giorni della settimana e i piatti."
    )
    refundable = False
