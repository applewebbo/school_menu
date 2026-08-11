"""
Tests for max_length enforcement during CSV import.

Neither SQLite nor PostgreSQL enforces max_length on a TextField, and
django-import-export never calls full_clean(), so over-long cells have to be
rejected while validating the dataset, before anything is written.
"""

import pytest
from django.test import TestCase
from tablib import Dataset

from school_menu.models import DetailedMeal, School, SimpleMeal
from school_menu.utils import validate_annual_dataset, validate_dataset

pytestmark = pytest.mark.django_db

MENU_MAX_LENGTH = SimpleMeal._meta.get_field("menu").max_length
SNACK_MAX_LENGTH = SimpleMeal._meta.get_field("morning_snack").max_length
COURSE_MAX_LENGTH = DetailedMeal._meta.get_field("first_course").max_length


def simple_dataset(pranzo="Pasta", spuntino="Yogurt", merenda="Mela"):
    dataset = Dataset()
    dataset.headers = ["giorno", "settimana", "pranzo", "spuntino", "merenda"]
    dataset.append(["Lunedì", 1, pranzo, spuntino, merenda])
    return dataset


def detailed_dataset(primo="Pasta"):
    dataset = Dataset()
    dataset.headers = [
        "giorno",
        "settimana",
        "primo",
        "secondo",
        "contorno",
        "frutta",
        "spuntino",
    ]
    dataset.append(["Lunedì", 1, primo, "Pollo", "Insalata", "Mela", "Yogurt"])
    return dataset


def annual_dataset(primo="Pasta", altro=""):
    dataset = Dataset()
    dataset.headers = ["data", "primo", "secondo", "contorno", "frutta", "altro"]
    dataset.append(["01/09/2025", primo, "Pollo", "Insalata", "Mela", altro])
    return dataset


class TestSimpleDatasetMaxLength(TestCase):
    def test_menu_over_max_length_is_rejected(self):
        dataset = simple_dataset(pranzo="a" * (MENU_MAX_LENGTH + 1))

        validates, message, _ = validate_dataset(dataset, School.Types.SIMPLE)

        assert validates is False
        assert "pranzo" in message
        assert str(MENU_MAX_LENGTH) in message
        assert "riga 2" in message

    def test_snack_over_max_length_is_rejected(self):
        dataset = simple_dataset(spuntino="a" * (SNACK_MAX_LENGTH + 1))

        validates, message, _ = validate_dataset(dataset, School.Types.SIMPLE)

        assert validates is False
        assert "spuntino" in message
        assert str(SNACK_MAX_LENGTH) in message

    def test_value_at_max_length_is_accepted(self):
        dataset = simple_dataset(
            pranzo="a" * MENU_MAX_LENGTH,
            spuntino="b" * SNACK_MAX_LENGTH,
            merenda="c" * SNACK_MAX_LENGTH,
        )

        validates, message, _ = validate_dataset(dataset, School.Types.SIMPLE)

        assert validates is True
        assert message is None

    def test_offending_row_number_matches_the_file(self):
        dataset = simple_dataset()
        dataset.append(["Martedì", 1, "a" * (MENU_MAX_LENGTH + 1), "Yogurt", "Mela"])

        validates, message, _ = validate_dataset(dataset, School.Types.SIMPLE)

        assert validates is False
        # header is row 1, so the second data row is row 3 of the file
        assert "riga 3" in message


class TestDetailedDatasetMaxLength(TestCase):
    def test_course_over_max_length_is_rejected(self):
        dataset = detailed_dataset(primo="a" * (COURSE_MAX_LENGTH + 1))

        validates, message, _ = validate_dataset(dataset, School.Types.DETAILED)

        assert validates is False
        assert "primo" in message
        assert str(COURSE_MAX_LENGTH) in message

    def test_course_at_max_length_is_accepted(self):
        dataset = detailed_dataset(primo="a" * COURSE_MAX_LENGTH)

        validates, message, _ = validate_dataset(dataset, School.Types.DETAILED)

        assert validates is True
        assert message is None


class TestAnnualDatasetMaxLength(TestCase):
    def test_joined_menu_over_max_length_is_rejected(self):
        """The annual columns are joined into AnnualMeal.menu, so the sum is what counts."""
        dataset = annual_dataset(
            primo="a" * (MENU_MAX_LENGTH - 10), altro="b" * (MENU_MAX_LENGTH - 10)
        )

        validates, message, _ = validate_annual_dataset(dataset)

        assert validates is False
        assert str(MENU_MAX_LENGTH) in message
        assert "riga 2" in message

    def test_single_long_column_over_max_length_is_rejected(self):
        dataset = annual_dataset(primo="a" * (MENU_MAX_LENGTH + 1))

        validates, message, _ = validate_annual_dataset(dataset)

        assert validates is False

    def test_menu_within_max_length_is_accepted(self):
        dataset = annual_dataset(primo="a" * 100)

        validates, message, _ = validate_annual_dataset(dataset)

        assert validates is True
        assert message is None
