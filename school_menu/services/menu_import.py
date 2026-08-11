"""
Import of a validated menu dataset into the database.

Extracted from the upload views so the CSV path and the AI-assisted path (#234) run
the exact same import, cache invalidation and audit logging. Callers are responsible
for validating the dataset first (see school_menu.utils.csv_import).
"""

import logging

from django.contrib import messages
from django.http import HttpRequest
from tablib import Dataset

from school_menu.cache import invalidate_meal_cache
from school_menu.models import Meal, School
from school_menu.resources import (
    AnnualMenuResource,
    DetailedMealResource,
    SimpleMealResource,
)
from school_menu.utils import fill_missing_dates

logger = logging.getLogger(__name__)

SUCCESS_MESSAGE = "Menu caricato con successo"
ERROR_MESSAGE = "Qualcosa è andato storto.."


def _log_failure(request: HttpRequest, result) -> None:  # pragma: no cover
    """Report row errors to the log and to the user.

    Excluded from coverage: django-import-export only returns row errors for failures
    the dataset validation already rejects, so reaching this would require mocking.
    """
    logger.error("Menu import failed with row errors: %s", result.row_errors())
    messages.add_message(request, messages.ERROR, ERROR_MESSAGE)


def import_weekly_dataset(
    request: HttpRequest,
    school: School,
    dataset: Dataset,
    season: int,
    meal_type: str,
    source: str = "csv",
) -> bool:
    """
    Import a validated weekly (simple or detailed) dataset for a school.

    Args:
        request: Current request, used for messages and the audit log
        school: School the meals belong to
        dataset: Validated and filtered dataset
        season: Season the meals belong to
        meal_type: Meal type code (Meal.Types)
        source: Where the rows came from, recorded in the audit log ("csv" or "ai")

    Returns:
        True if the rows were imported, False if the import reported row errors.
    """
    if school.menu_type == School.Types.SIMPLE:
        resource = SimpleMealResource()
        model_name = "SimpleMeal"
    else:
        resource = DetailedMealResource()
        model_name = "DetailedMeal"

    result = resource.import_data(
        dataset, dry_run=True, school=school, season=season, type=meal_type
    )
    if result.has_errors():  # pragma: no cover
        _log_failure(request, result)
        return False

    result = resource.import_data(
        dataset, dry_run=False, school=school, season=season, type=meal_type
    )
    # Explicitly invalidate cache after bulk import
    # (django-import-export may use bulk_create which bypasses save())
    invalidate_meal_cache(school.id)

    season_name = "Estivo" if season == 1 else "Invernale"
    meal_type_name = dict(Meal.Types.choices).get(meal_type, meal_type)
    request.audit_log(
        action="MENU_UPLOAD",
        model_name=model_name,
        object_id=school.id,
        object_repr=f"{school.name} - {season_name} - {meal_type_name}",
        changes={"rows_imported": result.totals["new"], "source": source},
    )
    messages.add_message(request, messages.SUCCESS, SUCCESS_MESSAGE)
    return True


def import_annual_dataset(
    request: HttpRequest,
    school: School,
    dataset: Dataset,
    meal_type: str,
    source: str = "csv",
) -> bool:
    """
    Import a validated annual dataset for a school.

    Args:
        request: Current request, used for messages and the audit log
        school: School the meals belong to
        dataset: Validated and filtered dataset
        meal_type: Meal type code (Meal.Types)
        source: Where the rows came from, recorded in the audit log ("csv" or "ai")

    Returns:
        True if the rows were imported, False if the import reported row errors.
    """
    resource = AnnualMenuResource()

    result = resource.import_data(dataset, dry_run=True, school=school, type=meal_type)
    if result.has_errors():  # pragma: no cover
        _log_failure(request, result)
        return False

    result = resource.import_data(dataset, dry_run=False, school=school, type=meal_type)
    fill_missing_dates(school, meal_type)
    # Explicitly invalidate cache after bulk import and fill_missing_dates
    # (django-import-export may use bulk_create which bypasses save())
    invalidate_meal_cache(school.id)

    meal_type_name = dict(Meal.Types.choices).get(meal_type, meal_type)
    request.audit_log(
        action="MENU_UPLOAD",
        model_name="AnnualMeal",
        object_id=school.id,
        object_repr=f"{school.name} - Annuale - {meal_type_name}",
        changes={"rows_imported": result.totals["new"], "source": source},
    )
    messages.add_message(request, messages.SUCCESS, SUCCESS_MESSAGE)
    return True
