"""
Response schemas for the AI menu import (#234).

Two jobs: tell Gemini the exact shape to answer with (`json_schema`), and re-validate
the answer locally (`parse`) so a violation becomes an error instead of a bad DB write.

Every field is a string, on purpose. Structured output is least reliable on unions and
numbers, and the deterministic clean-up in `normalise` already coerces the week number
and drops what it cannot fix — so accepting whatever the model sends and fixing it by
rule beats failing the whole file because one cell came back as `1` instead of `"1"`.

Field names are the Italian CSV headers, so a confirmed draft goes through exactly the
same resources as a CSV upload.
"""

from typing import Annotated

from pydantic import BaseModel, BeforeValidator

from school_menu.models import MenuImportDraft


def _as_text(value):
    """Accept anything the model sends: numbers, nulls, booleans."""
    return "" if value is None else str(value)


Text = Annotated[str, BeforeValidator(_as_text)]


class SimpleRow(BaseModel):
    giorno: Text = ""
    settimana: Text = ""
    pranzo: Text = ""
    spuntino: Text = ""
    merenda: Text = ""


class DetailedRow(BaseModel):
    giorno: Text = ""
    settimana: Text = ""
    primo: Text = ""
    secondo: Text = ""
    contorno: Text = ""
    frutta: Text = ""
    spuntino: Text = ""


class AnnualRow(BaseModel):
    data: Text = ""
    primo: Text = ""
    secondo: Text = ""
    contorno: Text = ""
    frutta: Text = ""
    altro: Text = ""


class SimpleMenu(BaseModel):
    righe: list[SimpleRow]


class DetailedMenu(BaseModel):
    righe: list[DetailedRow]


class AnnualMenu(BaseModel):
    righe: list[AnnualRow]


MENUS = {
    MenuImportDraft.Kinds.SIMPLE: SimpleMenu,
    MenuImportDraft.Kinds.DETAILED: DetailedMenu,
    MenuImportDraft.Kinds.ANNUAL: AnnualMenu,
}
ROWS = {
    MenuImportDraft.Kinds.SIMPLE: SimpleRow,
    MenuImportDraft.Kinds.DETAILED: DetailedRow,
    MenuImportDraft.Kinds.ANNUAL: AnnualRow,
}


def row_model(kind):
    """The pydantic model of a single row for this kind of menu."""
    return ROWS[kind]


def json_schema(kind):
    """The JSON schema handed to the model as the required response format."""
    return MENUS[kind].model_json_schema()


def parse(kind, text):
    """
    Validate the raw answer and return plain dicts keyed by the CSV headers.

    Raises:
        pydantic.ValidationError: the answer does not match the schema.
    """
    payload = MENUS[kind].model_validate_json(text)
    return [row.model_dump() for row in payload.righe]
