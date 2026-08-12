"""
Deterministic clean-up of the rows returned by the AI (#234).

The model is asked for a specific shape, but it is not trusted to get every detail
right. Everything that can be fixed by rule is fixed here rather than in the prompt:
accented weekday names, week numbers as strings, duplicates, ordering and field lengths.
Anything that cannot be fixed is dropped with a warning the user sees above the preview,
so a wrong row is never silently imported.

Rows use the Italian CSV headers, so the confirmed draft goes through exactly the same
validation and resources as a CSV upload.
"""

import unicodedata
from datetime import datetime

from school_menu.ai.errors import EmptyResult
from school_menu.models import AnnualMeal, DetailedMeal, MenuImportDraft, SimpleMeal

MENU_MAX_LENGTH = SimpleMeal._meta.get_field("menu").max_length
SNACK_MAX_LENGTH = SimpleMeal._meta.get_field("morning_snack").max_length
COURSE_MAX_LENGTH = DetailedMeal._meta.get_field("first_course").max_length
ANNUAL_MENU_MAX_LENGTH = AnnualMeal._meta.get_field("menu").max_length

WEEKDAYS = ["Lunedì", "Martedì", "Mercoledì", "Giovedì", "Venerdì"]
MIN_WEEK, MAX_WEEK = 1, 4
DATE_FORMAT = "%d/%m/%Y"

# column -> max length, per kind. Annual columns are capped as a group instead: they are
# joined with newlines into one AnnualMeal.menu field.
COLUMNS = {
    MenuImportDraft.Kinds.SIMPLE: {
        "pranzo": MENU_MAX_LENGTH,
        "spuntino": SNACK_MAX_LENGTH,
        "merenda": SNACK_MAX_LENGTH,
    },
    MenuImportDraft.Kinds.DETAILED: {
        "primo": COURSE_MAX_LENGTH,
        "secondo": COURSE_MAX_LENGTH,
        "contorno": COURSE_MAX_LENGTH,
        "frutta": COURSE_MAX_LENGTH,
        "spuntino": COURSE_MAX_LENGTH,
    },
    MenuImportDraft.Kinds.ANNUAL: {
        "primo": ANNUAL_MENU_MAX_LENGTH,
        "secondo": ANNUAL_MENU_MAX_LENGTH,
        "contorno": ANNUAL_MENU_MAX_LENGTH,
        "frutta": ANNUAL_MENU_MAX_LENGTH,
        "altro": ANNUAL_MENU_MAX_LENGTH,
    },
}


def _fold(value):
    """Lowercase and strip accents and stray punctuation, for matching only."""
    text = unicodedata.normalize("NFKD", str(value or "").strip().lower())
    return "".join(c for c in text if not unicodedata.combining(c)).strip(" '`")


WEEKDAY_LOOKUP = {_fold(day): day for day in WEEKDAYS}


def _clean(value):
    return str(value).strip() if value is not None else ""


def _normalise_weekday(row, index, warnings):
    """Return the canonical weekday name, or None if the row has to go."""
    raw = _clean(row.get("giorno"))
    day = WEEKDAY_LOOKUP.get(_fold(raw))
    if day is None:
        warnings.append(
            f"Riga {index}: giorno non riconosciuto ({raw or 'vuoto'}), riga ignorata."
        )
    return day


def _normalise_week(row, index, warnings):
    """Return the week as an int in 1-4, or None if the row has to go."""
    raw = _clean(row.get("settimana"))
    try:
        week = int(float(raw))
    except ValueError:
        warnings.append(
            f"Riga {index}: settimana non numerica ({raw or 'vuota'}), riga ignorata."
        )
        return None
    if not MIN_WEEK <= week <= MAX_WEEK:
        warnings.append(
            f"Riga {index}: settimana {week} fuori dall'intervallo "
            f"{MIN_WEEK}-{MAX_WEEK}, riga ignorata."
        )
        return None
    return week


def _normalise_date(row, index, warnings):
    """Return (display, sort key) for a DD/MM/YYYY date, or None if unusable."""
    raw = _clean(row.get("data"))
    try:
        parsed = datetime.strptime(raw, DATE_FORMAT).date()
    except ValueError:
        warnings.append(
            f"Riga {index}: data non valida ({raw or 'vuota'}), riga ignorata. "
            "Il formato atteso è GG/MM/AAAA."
        )
        return None
    return raw, parsed


def _truncate_columns(row, index, columns, warnings):
    """Cap each column at the length its model field allows."""
    for column, max_length in columns.items():
        value = _clean(row.get(column))
        if len(value) > max_length:
            warnings.append(
                f'Riga {index}: il campo "{column}" superava i {max_length} '
                "caratteri ed è stato accorciato."
            )
            value = value[:max_length]
        row[column] = value
    return row


def _truncate_annual_menu(row, index, warnings):
    """The annual columns share one 600 char field, so cap their total."""
    columns = list(COLUMNS[MenuImportDraft.Kinds.ANNUAL])
    joined = "\n".join(row[c] for c in columns if row[c])
    if len(joined) <= ANNUAL_MENU_MAX_LENGTH:
        return row

    warnings.append(
        f"Riga {index}: il menu superava i {ANNUAL_MENU_MAX_LENGTH} caratteri "
        "complessivi ed è stato accorciato."
    )
    # Fill the columns in order until the budget runs out. Every value after the first
    # also costs the newline that joins it, exactly as AnnualMenuResource builds the field.
    budget = ANNUAL_MENU_MAX_LENGTH
    is_first = True
    for column in columns:
        value = row[column]
        if not value:
            continue
        separator = 0 if is_first else 1
        allowed = max(budget - separator, 0)
        row[column] = value[:allowed]
        if row[column]:
            budget -= separator + len(row[column])
            is_first = False
    return row


def _normalise_weekly(kind, rows, warnings):
    columns = COLUMNS[kind]
    seen = set()
    cleaned = []
    for index, raw_row in enumerate(rows, start=1):
        row = dict(raw_row)
        day = _normalise_weekday(row, index, warnings)
        week = _normalise_week(row, index, warnings)
        if day is None or week is None:
            continue
        if (day, week) in seen:
            warnings.append(
                f"Riga {index}: {day} della settimana {week} era già presente, "
                "riga ignorata."
            )
            continue
        seen.add((day, week))
        row = _truncate_columns(row, index, columns, warnings)
        row["giorno"] = day
        row["settimana"] = week
        cleaned.append(
            {"giorno": day, "settimana": week, **{c: row[c] for c in columns}}
        )

    cleaned.sort(key=lambda r: (r["settimana"], WEEKDAYS.index(r["giorno"])))
    return cleaned


def _normalise_annual(rows, warnings):
    columns = COLUMNS[MenuImportDraft.Kinds.ANNUAL]
    seen = set()
    cleaned = []
    for index, raw_row in enumerate(rows, start=1):
        row = dict(raw_row)
        parsed = _normalise_date(row, index, warnings)
        if parsed is None:
            continue
        display, sort_key = parsed
        if sort_key in seen:
            warnings.append(
                f"Riga {index}: la data {display} era già presente, riga ignorata."
            )
            continue
        seen.add(sort_key)
        row = _truncate_columns(row, index, columns, warnings)
        row = _truncate_annual_menu(row, index, warnings)
        cleaned.append(
            {"data": display, **{c: row[c] for c in columns}, "_sort": sort_key}
        )

    cleaned.sort(key=lambda r: r["_sort"])
    for row in cleaned:
        del row["_sort"]
    return cleaned


def normalise_rows(kind, rows):
    """
    Clean the rows the AI produced.

    Args:
        kind: MenuImportDraft.Kinds value
        rows: list of dicts keyed by the Italian CSV column names

    Returns:
        Tuple of (rows, warnings), rows sorted and free of duplicates.

    Raises:
        EmptyResult: nothing usable survived, so there is nothing to preview.
    """
    warnings = []
    if kind == MenuImportDraft.Kinds.ANNUAL:
        cleaned = _normalise_annual(rows, warnings)
    else:
        cleaned = _normalise_weekly(kind, rows, warnings)

    if not cleaned:
        raise EmptyResult()
    return cleaned, warnings
