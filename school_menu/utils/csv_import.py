"""CSV import, validation, and widget utilities for school menu management."""

import csv
from collections.abc import Sequence
from typing import Any

from import_export.widgets import Widget
from tablib import Dataset

from school_menu.constants import (
    CSV_HEADER_LINES,
    CSV_SAMPLE_SIZE,
    MAX_WEEK_NUMBER,
    MIN_WEEK_NUMBER,
)
from school_menu.models import School


def detect_csv_format(content: str) -> tuple[str, str]:
    """
    Detect CSV delimiter and quote character.

    Uses csv.Sniffer for automatic detection with fallback to manual counting
    if the sniffer fails.

    Args:
        content: CSV file content as string

    Returns:
        Tuple of (delimiter, quotechar)
        - delimiter: Field separator character (usually ',' or ';')
        - quotechar: Character used for quoting fields (usually '"')

    Example:
        >>> content = 'name,age\\n"John",30'
        >>> detect_csv_format(content)
        (',', '"')
    """
    # Try csv.Sniffer first on a sample of the content
    try:
        sample = content[:CSV_SAMPLE_SIZE]  # Use first 1KB for detection
        sniffer = csv.Sniffer()
        dialect = sniffer.sniff(sample, delimiters=",;")
        return dialect.delimiter, dialect.quotechar or '"'
    except Exception:  # nosec B110
        # Sniffer failed, use fallback manual detection
        pass  # Intentionally fall through to manual detection

    # Fallback: try to detect by counting delimiters in first few lines
    lines = content.split("\\n")[:CSV_HEADER_LINES]  # Check first 5 lines
    comma_count = sum(line.count(",") for line in lines)
    semicolon_count = sum(line.count(";") for line in lines)

    if semicolon_count > comma_count:
        return ";", '"'

    # Default to comma (backward compatibility)
    return ",", '"'


def detect_menu_type(headers: list[str]) -> str | None:
    """
    Detect menu type based on CSV column headers.

    Analyzes the column names to determine which type of menu format
    the CSV file uses.

    Args:
        headers: List of column header names from CSV

    Returns:
        Menu type string:
        - 'simple': Simple menu format (has 'pranzo' column)
        - 'detailed': Detailed menu format (has 'primo', 'secondo', 'contorno', 'frutta')
        - 'annual': Annual menu format (has 'data' instead of 'settimana')
        - None: Unknown/unrecognized format

    Example:
        >>> headers = ['giorno', 'settimana', 'pranzo', 'spuntino']
        >>> detect_menu_type(headers)
        'simple'
    """
    if not headers:
        return None

    # Convert to lowercase set for case-insensitive comparison
    headers_set = {h.lower() for h in headers if h and h.strip()}

    # Annual menu has 'data' instead of 'settimana'
    if "data" in headers_set:
        return "annual"

    # Detailed menu has primo, secondo, contorno, frutta
    detailed_cols = {"primo", "secondo", "contorno", "frutta"}
    if detailed_cols.issubset(headers_set):
        return "detailed"

    # Simple menu has pranzo
    if "pranzo" in headers_set:
        return "simple"

    return None  # Unknown format


def filter_dataset_columns(
    dataset: Dataset, allowed_columns: list[str]
) -> tuple[Dataset, list[str]]:
    """
    Filter dataset to remove unnamed, whitespace-only, and extra columns.

    Cleans up CSV datasets by removing invalid or unnecessary columns.

    Args:
        dataset: tablib Dataset object
        allowed_columns: List of column names that are allowed (required + optional)

    Returns:
        Tuple of (filtered_dataset, removed_columns):
        - filtered_dataset: Dataset with only valid columns
        - removed_columns: List of column names that were removed

    Removes:
        - Columns with empty names ('')
        - Columns with whitespace-only names ('   ')
        - Columns not in the allowed_columns list

    Example:
        >>> dataset = Dataset(headers=['name', '', 'age', 'extra'])
        >>> allowed = ['name', 'age']
        >>> filtered, removed = filter_dataset_columns(dataset, allowed)
        >>> removed
        ['(unnamed)', 'extra']
    """
    original_headers = dataset.headers
    removed_columns = []

    # Identify columns to keep
    columns_to_keep = []
    for i, header in enumerate(original_headers):
        # Skip empty or whitespace-only column names
        if not header or not header.strip():
            removed_columns.append(header if header else "(unnamed)")
            continue

        # Skip columns not in allowed list
        if header not in allowed_columns:
            removed_columns.append(header)
            continue

        columns_to_keep.append(i)

    # If no columns need to be removed, return original dataset
    if not removed_columns:
        return dataset, []

    # Create new dataset with only valid columns
    filtered_dataset = Dataset()
    filtered_headers = [original_headers[i] for i in columns_to_keep]
    filtered_dataset.headers = filtered_headers

    # Copy rows with only valid columns
    for row in dataset:
        filtered_row = [row[i] for i in columns_to_keep]
        filtered_dataset.append(filtered_row)

    return filtered_dataset, removed_columns


def validate_dataset(
    dataset: Dataset, menu_type: str
) -> tuple[bool, str | None, Dataset]:
    """
    Validate menu import dataset for required columns and values.

    Checks that the dataset has the correct format, columns, and data
    for the specified menu type.

    Args:
        dataset: tablib Dataset to validate
        menu_type: Menu type code (School.Types.SIMPLE or School.Types.DETAILED)

    Returns:
        Tuple of (validates, message, filtered_dataset):
        - validates: True if dataset is valid, False otherwise
        - message: Error message if not valid, None if valid
        - filtered_dataset: Dataset with only allowed columns

    Validation checks:
        - Correct menu type based on headers
        - All required columns present
        - Week values are 1-4
        - Day values are valid Italian weekday names
    """
    validates = True
    message = None

    # Detect menu type from CSV headers before validation
    detected_type = detect_menu_type(dataset.headers)
    expected_type = "simple" if menu_type == School.Types.SIMPLE else "detailed"

    # Check if detected type matches expected type
    if detected_type and detected_type != expected_type:
        validates = False
        type_names = {
            "simple": "Menu Semplice",
            "detailed": "Menu Dettagliato",
            "annual": "Menu Annuale",
        }
        detected_name = type_names.get(detected_type, "formato sconosciuto")
        expected_name = type_names.get(expected_type, "formato sconosciuto")
        message = f"Il file caricato sembra essere un {detected_name}, ma hai selezionato {expected_name}. Verifica di aver caricato il file corretto."
        return validates, message, dataset

    # Define required and allowed columns based on menu type
    if menu_type == School.Types.SIMPLE:
        required_columns = [
            "giorno",
            "settimana",
            "pranzo",
            "spuntino",
            "merenda",
        ]
        allowed_columns = required_columns  # No optional columns for simple menu
    else:
        required_columns = [
            "giorno",
            "settimana",
            "primo",
            "secondo",
            "contorno",
            "frutta",
            "spuntino",
        ]
        allowed_columns = required_columns  # No optional columns for detailed menu

    # Filter out unnamed, whitespace-only, and extra columns
    filtered_dataset, removed_columns = filter_dataset_columns(dataset, allowed_columns)

    columns = filtered_dataset.headers

    # Handle case where dataset is completely invalid (no headers)
    if columns is None:
        validates = False
        message = "Formato non valido. Il file non contiene intestazioni valide."
        return validates, message, filtered_dataset

    # check required headers presence
    if not all(column in columns for column in required_columns):
        validates = False
        missing = [col for col in required_columns if col not in columns]
        message = f"Formato non valido. Il file non contiene tutte le colonne richieste. Colonne mancanti: {', '.join(missing)}"
        return validates, message, filtered_dataset

    # check if the day column contains only valid day names
    days = {"Lunedì", "Martedì", "Mercoledì", "Giovedì", "Venerdì"}
    day_values = filtered_dataset["giorno"]
    if not all(day in days for day in day_values):
        validates = False
        message = 'Formato non valido. La colonna "giorno" contiene valori diversi dai giorni della settimana.'

    # check if week values are 1 to 4
    weeks = filtered_dataset["settimana"]
    try:
        weeks = [int(week) for week in weeks]
    except ValueError:
        validates = False
        message = (
            'Formato non valido. La colonna "settimana" contiene valori non numerici.'
        )
        return validates, message, filtered_dataset
    if not all(MIN_WEEK_NUMBER <= week <= MAX_WEEK_NUMBER for week in weeks):
        validates = False
        message = f'Formato non valido. La colonna "settimana" contiene valori non compresi fra {MIN_WEEK_NUMBER} e {MAX_WEEK_NUMBER}.'

    # if everything ok return validates = True and no message
    return validates, message, filtered_dataset


def validate_annual_dataset(dataset: Dataset) -> tuple[bool, str | None, Dataset]:
    """
    Validate annual menu import dataset for required columns and values.

    Checks that the dataset has the correct format for annual menus,
    which use specific dates instead of week rotations.

    Args:
        dataset: tablib Dataset to validate

    Returns:
        Tuple of (validates, message, filtered_dataset):
        - validates: True if dataset is valid, False otherwise
        - message: Error message if not valid, None if valid
        - filtered_dataset: Dataset with only allowed columns

    Validation checks:
        - Not a weekly menu format (simple/detailed)
        - All required columns present
        - Date values are in DD/MM/YYYY format
    """
    from datetime import datetime

    validates = True
    message = None

    # Detect menu type from CSV headers before validation
    detected_type = detect_menu_type(dataset.headers)

    # Check if detected type is actually a weekly menu (simple or detailed) instead of annual
    if detected_type in ("simple", "detailed"):
        validates = False
        type_names = {
            "simple": "Menu Semplice",
            "detailed": "Menu Dettagliato",
        }
        detected_name = type_names.get(detected_type, "Menu Settimanale")
        message = f"Il file caricato sembra essere un {detected_name} (con settimane), ma hai selezionato Menu Annuale. Verifica di aver caricato il file corretto."
        return validates, message, dataset

    # Define required and allowed columns
    required_columns = ["data", "primo", "secondo", "contorno", "frutta", "altro"]
    # giorno is optional (auto-calculated from data) so we allow it but don't require it
    allowed_columns = required_columns + ["giorno"]

    # Filter out unnamed, whitespace-only, and extra columns
    filtered_dataset, removed_columns = filter_dataset_columns(dataset, allowed_columns)

    # check required headers presence
    columns = filtered_dataset.headers

    # Handle case where dataset is completely invalid (no headers)
    if columns is None:
        validates = False
        message = "Formato non valido. Il file non contiene intestazioni valide."
        return validates, message, filtered_dataset

    if not all(column in columns for column in required_columns):
        validates = False
        missing = [col for col in required_columns if col not in columns]
        message = f"Formato non valido. Il file non contiene tutte le colonne richieste. Colonne mancanti: {', '.join(missing)}"
        return validates, message, filtered_dataset

    # check if data column contain valid data values
    dates = filtered_dataset["data"]
    for date_str in dates:
        try:
            datetime.strptime(date_str, "%d/%m/%Y")
        except ValueError:
            validates = False
            message = 'Formato non valido. La colonna "data" contiene date in formato non valido. Usa il formato GG/MM/AAAA'
            return validates, message, filtered_dataset

    # if everything ok return validates = True and no message
    return validates, message, filtered_dataset


class ChoicesWidget(Widget):
    """
    Widget that uses choice display values in place of database values.

    This allows CSV imports to use human-readable values (e.g., "Chocolate")
    which are automatically converted to database codes (e.g., "CHOC").
    """

    def __init__(
        self, choices: Sequence[tuple[str | int, str]], *args: Any, **kwargs: Any
    ):
        """
        Initialize widget with Django model choices.

        Args:
            choices: List of (value, label) tuples from Django model choices
                    e.g., [('CHOC', 'Chocolate'), ('VAN', 'Vanilla')]
                    or [(1, 'Monday'), (2, 'Tuesday')] for IntegerChoices
            *args: Additional positional arguments
            **kwargs: Additional keyword arguments
        """
        self.choices = dict(choices)
        self.revert_choices = {v: k for k, v in self.choices.items()}

    def clean(self, value: Any, row: Any = None, *args: Any, **kwargs: Any) -> Any:
        """
        Convert display value to database value during import.

        Args:
            value: Display value from CSV (e.g., "Chocolate")
            row: Current row data (unused)
            *args: Additional positional arguments
            **kwargs: Additional keyword arguments

        Returns:
            Database value (e.g., "CHOC") or original value if not in choices
        """
        return self.revert_choices.get(value, value) if value else None

    def render(self, value: Any, obj: Any = None) -> str:
        """
        Convert database value to display value during export.

        Args:
            value: Database value (e.g., "CHOC")
            obj: Model instance (unused)

        Returns:
            Display value (e.g., "Chocolate") or empty string if not found
        """
        return self.choices.get(value, "")
