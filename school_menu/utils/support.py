"""
Reference codes for errors we cannot explain to the user (#251).

When something goes wrong in a way the user can do nothing about, the exception text is
noise to them and the only useful thing we can offer is a handle support can search the
logs with. `log_unexpected` writes the whole traceback under a code and returns just the
code, so the user-facing message stays plain.
"""

import uuid


def log_unexpected(logger, message: str, *args) -> str:
    """
    Log an unexpected failure with its traceback and return the reference code.

    Must be called from an `except` block: the traceback is what makes the code worth
    quoting. The code is per-occurrence, not per-error-type, so support can tell two
    reports apart.
    """
    code = f"ERR-{uuid.uuid4().hex[:6].upper()}"
    logger.exception(f"[{code}] {message}", *args)
    return code


def support_hint(code: str) -> str:
    """The sentence appended to a user-facing message carrying a reference code."""
    return f"Se il problema si ripete, contatta il supporto indicando il codice {code}."
