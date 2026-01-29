"""
School menu utilities package.

This package provides utilities for:
- CSV import and validation
- Calendar and date calculations
- Meal retrieval and menu building
- Notification status checks

All functions are re-exported from the root level for backwards compatibility.
"""

# Import calendar utilities from dedicated module
from school_menu.utils.calendar import (
    calculate_week,
    get_adjusted_year,
    get_current_date,
    get_season,
)

# Import CSV import and validation utilities from dedicated module
from school_menu.utils.csv_import import (
    ChoicesWidget,
    detect_csv_format,
    detect_menu_type,
    filter_dataset_columns,
    validate_annual_dataset,
    validate_dataset,
)

# Import meal utilities from dedicated module
from school_menu.utils.meals import (
    build_types_menu,
    fill_missing_dates,
    get_alt_menu,
    get_meals,
    get_meals_for_annual_menu,
    get_user,
)

# Import notification utilities from dedicated module
from school_menu.utils.notifications import get_notifications_status

__all__ = [
    # CSV import and validation
    "detect_csv_format",
    "detect_menu_type",
    "filter_dataset_columns",
    "validate_dataset",
    "validate_annual_dataset",
    "ChoicesWidget",
    # Calendar utilities
    "calculate_week",
    "get_current_date",
    "get_season",
    "get_adjusted_year",
    # Meal utilities
    "get_user",
    "get_alt_menu",
    "build_types_menu",
    "get_meals",
    "get_meals_for_annual_menu",
    "fill_missing_dates",
    # Notification utilities
    "get_notifications_status",
]
