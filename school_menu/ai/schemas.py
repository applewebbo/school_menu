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

from dataclasses import dataclass, field
from typing import Annotated

from pydantic import BaseModel, BeforeValidator

from school_menu.ai.normalise import COLUMNS
from school_menu.models import MenuImportDraft

# The columns that identify a row are not in COLUMNS: they are not stored as they arrive,
# they are matched against the weekday list, the 1-4 range and the date format. The caps
# only have to be wide enough for what those parsers accept.
KEY_MAX_LENGTHS = {"giorno": 20, "settimana": 4, "data": 10}
# Wide enough for "primaverile-estivo", the longer of the two labels we ask for.
SEASON_MAX_LENGTH = 30


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
    # Which season the model actually read, so a file holding both does not silently
    # import the wrong one. Empty when the document does not say.
    stagione: Text = ""


class DetailedMenu(BaseModel):
    righe: list[DetailedRow]
    stagione: Text = ""


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


@dataclass(frozen=True)
class ParsedMenu:
    """A validated answer: the rows, plus what the model says it was looking at."""

    rows: list = field(default_factory=list)
    season: str = ""


def row_model(kind):
    """The pydantic model of a single row for this kind of menu."""
    return ROWS[kind]


def json_schema(kind):
    """
    The JSON schema handed to the model as the required response format.

    Built by hand rather than taken from `model_json_schema()`, because what the model
    needs and what pydantic emits differ in three ways that all cost data:

    - pydantic marks nothing required (every field has a default), which lets the model
      split one day across two partial objects;
    - it puts the row behind a `$ref`, and Gemini's handling of references in structured
      output is not dependable;
    - it carries no upper bound, so nothing stops a generation that starts repeating.

    The local `parse()` stays deliberately permissive: a partial answer should be cleaned
    up by `normalise`, never rejected wholesale after the tokens have been spent.
    """
    row_columns = COLUMNS[kind]
    properties = {}
    for name in row_model(kind).model_fields:
        max_length = row_columns.get(name) or KEY_MAX_LENGTHS[name]
        properties[name] = {"type": "string", "maxLength": max_length}
    schema = {
        "type": "object",
        "properties": {
            "righe": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": properties,
                    "required": list(properties),
                },
            }
        },
        "required": ["righe"],
    }
    if "stagione" in MENUS[kind].model_fields:
        schema["properties"]["stagione"] = {
            "type": "string",
            "maxLength": SEASON_MAX_LENGTH,
        }
        schema["required"].append("stagione")
    return schema


def parse(kind, text):
    """
    Validate the raw answer.

    Returns:
        ParsedMenu with the rows as plain dicts keyed by the CSV headers, and the season
        the model says it read ("" for annual menus, which have none).

    Raises:
        pydantic.ValidationError: the answer does not match the schema.
    """
    payload = MENUS[kind].model_validate_json(text)
    return ParsedMenu(
        rows=[row.model_dump() for row in payload.righe],
        season=getattr(payload, "stagione", ""),
    )
