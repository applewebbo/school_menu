"""
Tests for CSV column filtering functionality.
These tests cover the new filter_dataset_columns function and column filtering
in validate_dataset and validate_annual_dataset.
"""

import pytest
from django.test import TestCase
from tablib import Dataset

from school_menu.models import School
from school_menu.utils import (
    filter_dataset_columns,
    validate_annual_dataset,
    validate_dataset,
)

pytestmark = pytest.mark.django_db


class TestFilterDatasetColumns:
    def test_filter_no_extra_columns(self):
        """Test filtering when all columns are allowed"""
        dataset = Dataset()
        dataset.headers = ["giorno", "settimana", "pranzo"]
        dataset.append(["Lunedì", 1, "Pasta"])

        allowed_columns = ["giorno", "settimana", "pranzo"]
        filtered_dataset, removed_columns = filter_dataset_columns(
            dataset, allowed_columns
        )

        assert filtered_dataset.headers == ["giorno", "settimana", "pranzo"]
        assert removed_columns == []
        assert len(filtered_dataset) == 1

    def test_filter_unnamed_column(self):
        """Test filtering removes unnamed columns (empty string)"""
        dataset = Dataset()
        dataset.headers = ["giorno", "settimana", "", "pranzo"]
        dataset.append(["Lunedì", 1, "extra", "Pasta"])

        allowed_columns = ["giorno", "settimana", "pranzo"]
        filtered_dataset, removed_columns = filter_dataset_columns(
            dataset, allowed_columns
        )

        assert filtered_dataset.headers == ["giorno", "settimana", "pranzo"]
        assert "(unnamed)" in removed_columns
        assert len(filtered_dataset) == 1
        assert list(filtered_dataset[0]) == ["Lunedì", 1, "Pasta"]

    def test_filter_whitespace_only_column(self):
        """Test filtering removes whitespace-only column names"""
        dataset = Dataset()
        dataset.headers = ["giorno", "   ", "settimana", "pranzo"]
        dataset.append(["Lunedì", "extra", 1, "Pasta"])

        allowed_columns = ["giorno", "settimana", "pranzo"]
        filtered_dataset, removed_columns = filter_dataset_columns(
            dataset, allowed_columns
        )

        assert filtered_dataset.headers == ["giorno", "settimana", "pranzo"]
        assert "   " in removed_columns
        assert list(filtered_dataset[0]) == ["Lunedì", 1, "Pasta"]

    def test_filter_extra_named_column(self):
        """Test filtering removes extra columns not in allowed list"""
        dataset = Dataset()
        dataset.headers = ["giorno", "settimana", "pranzo", "extra_column"]
        dataset.append(["Lunedì", 1, "Pasta", "Extra Value"])

        allowed_columns = ["giorno", "settimana", "pranzo"]
        filtered_dataset, removed_columns = filter_dataset_columns(
            dataset, allowed_columns
        )

        assert filtered_dataset.headers == ["giorno", "settimana", "pranzo"]
        assert "extra_column" in removed_columns
        assert list(filtered_dataset[0]) == ["Lunedì", 1, "Pasta"]

    def test_filter_multiple_extra_columns(self):
        """Test filtering removes multiple extra columns at once"""
        dataset = Dataset()
        dataset.headers = ["giorno", "", "settimana", "extra1", "pranzo", "extra2"]
        dataset.append(["Lunedì", "a", 1, "b", "Pasta", "c"])

        allowed_columns = ["giorno", "settimana", "pranzo"]
        filtered_dataset, removed_columns = filter_dataset_columns(
            dataset, allowed_columns
        )

        assert filtered_dataset.headers == ["giorno", "settimana", "pranzo"]
        assert len(removed_columns) == 3
        assert "(unnamed)" in removed_columns
        assert "extra1" in removed_columns
        assert "extra2" in removed_columns
        assert list(filtered_dataset[0]) == ["Lunedì", 1, "Pasta"]

    def test_filter_preserves_multiple_rows(self):
        """Test filtering works correctly with multiple data rows"""
        dataset = Dataset()
        dataset.headers = ["giorno", "settimana", "pranzo", "extra"]
        dataset.append(["Lunedì", 1, "Pasta", "X"])
        dataset.append(["Martedì", 2, "Riso", "Y"])
        dataset.append(["Mercoledì", 3, "Pizza", "Z"])

        allowed_columns = ["giorno", "settimana", "pranzo"]
        filtered_dataset, removed_columns = filter_dataset_columns(
            dataset, allowed_columns
        )

        assert len(filtered_dataset) == 3
        assert list(filtered_dataset[0]) == ["Lunedì", 1, "Pasta"]
        assert list(filtered_dataset[1]) == ["Martedì", 2, "Riso"]
        assert list(filtered_dataset[2]) == ["Mercoledì", 3, "Pizza"]


class TestValidateDatasetWithColumnFiltering(TestCase):
    def test_simple_meal_with_extra_unnamed_column(self):
        """Test CSV with trailing comma (unnamed column) is accepted"""
        dataset = Dataset()
        dataset.headers = ["giorno", "settimana", "pranzo", "spuntino", "merenda", ""]
        dataset.append(["Lunedì", 1, "Pasta", "Yogurt", "Mela", ""])

        validates, message, filtered_dataset = validate_dataset(
            dataset, School.Types.SIMPLE
        )

        assert validates is True
        assert message is None
        assert filtered_dataset.headers == [
            "giorno",
            "settimana",
            "pranzo",
            "spuntino",
            "merenda",
        ]
        assert len(filtered_dataset) == 1

    def test_simple_meal_with_extra_named_column(self):
        """Test CSV with extra named column not in schema"""
        dataset = Dataset()
        dataset.headers = [
            "giorno",
            "settimana",
            "pranzo",
            "spuntino",
            "merenda",
            "extra",
        ]
        dataset.append(["Lunedì", 1, "Pasta", "Yogurt", "Mela", "Extra Value"])

        validates, message, filtered_dataset = validate_dataset(
            dataset, School.Types.SIMPLE
        )

        assert validates is True
        assert message is None
        assert filtered_dataset.headers == [
            "giorno",
            "settimana",
            "pranzo",
            "spuntino",
            "merenda",
        ]

    def test_detailed_meal_with_whitespace_column(self):
        """Test CSV with whitespace-only column names"""
        dataset = Dataset()
        dataset.headers = [
            "giorno",
            "settimana",
            "primo",
            "   ",
            "secondo",
            "contorno",
            "frutta",
            "spuntino",
        ]
        dataset.append(
            ["Lunedì", 1, "Pasta", "X", "Pollo", "Fagiolini", "Mela", "Yogurt"]
        )

        validates, message, filtered_dataset = validate_dataset(
            dataset, School.Types.DETAILED
        )

        assert validates is True
        assert message is None
        assert filtered_dataset.headers == [
            "giorno",
            "settimana",
            "primo",
            "secondo",
            "contorno",
            "frutta",
            "spuntino",
        ]

    def test_detailed_meal_with_multiple_extra_columns(self):
        """Test CSV with multiple types of extra columns"""
        dataset = Dataset()
        dataset.headers = [
            "giorno",
            "",
            "settimana",
            "primo",
            "extra1",
            "secondo",
            "contorno",
            "frutta",
            "spuntino",
            "  ",
            "extra2",
        ]
        dataset.append(
            [
                "Lunedì",
                "a",
                1,
                "Pasta",
                "b",
                "Pollo",
                "Fagiolini",
                "Mela",
                "Yogurt",
                "c",
                "d",
            ]
        )

        validates, message, filtered_dataset = validate_dataset(
            dataset, School.Types.DETAILED
        )

        assert validates is True
        assert message is None
        assert filtered_dataset.headers == [
            "giorno",
            "settimana",
            "primo",
            "secondo",
            "contorno",
            "frutta",
            "spuntino",
        ]
        assert len(filtered_dataset) == 1

    def test_annual_menu_with_extra_columns(self):
        """Test annual menu with extra columns"""
        dataset = Dataset()
        dataset.headers = [
            "data",
            "giorno",
            "primo",
            "secondo",
            "contorno",
            "frutta",
            "altro",
            "extra1",
            "",
        ]
        dataset.append(
            [
                "28/12/2024",
                "Sabato",
                "Pasta",
                "Bistecca",
                "Fagiolini",
                "Mela",
                "Pane",
                "X",
                "",
            ]
        )

        validates, message, filtered_dataset = validate_annual_dataset(dataset)

        assert validates is True
        assert message is None
        # giorno is optional but allowed
        assert "data" in filtered_dataset.headers
        assert "primo" in filtered_dataset.headers
        assert "giorno" in filtered_dataset.headers  # giorno is allowed
        assert "extra1" not in filtered_dataset.headers

    def test_annual_menu_without_optional_giorno(self):
        """Test annual menu without the optional giorno column"""
        dataset = Dataset()
        dataset.headers = ["data", "primo", "secondo", "contorno", "frutta", "altro"]
        dataset.append(["28/12/2024", "Pasta", "Bistecca", "Fagiolini", "Mela", "Pane"])

        validates, message, filtered_dataset = validate_annual_dataset(dataset)

        assert validates is True
        assert message is None
        assert "giorno" not in filtered_dataset.headers

    def test_validates_after_filtering(self):
        """Test that validation happens on filtered dataset"""
        dataset = Dataset()
        dataset.headers = [
            "giorno",
            "settimana",
            "pranzo",
            "spuntino",
            "merenda",
            "extra",
            "",
        ]
        dataset.append(["InvalidDay", 1, "Pasta", "Yogurt", "Mela", "X", ""])

        validates, message, filtered_dataset = validate_dataset(
            dataset, School.Types.SIMPLE
        )

        # Should fail validation because of invalid day, even though columns were filtered
        assert validates is False
        assert "giorno" in message

    def test_required_columns_still_validated_after_filtering(self):
        """Test that missing required columns are detected after filtering"""
        dataset = Dataset()
        dataset.headers = ["giorno", "settimana", "extra1", "", "extra2"]
        dataset.append(["Lunedì", 1, "a", "b", "c"])

        validates, message, filtered_dataset = validate_dataset(
            dataset, School.Types.SIMPLE
        )

        # Should fail because pranzo, spuntino, merenda are missing
        assert validates is False
        assert "colonne richieste" in message.lower()

    def test_completely_invalid_column_names(self):
        """Test CSV with completely invalid column names (all filtered out)"""
        dataset = Dataset()
        dataset.headers = ["invalid", "csv", "content"]
        dataset.append(["foo", "bar", "baz"])

        validates, message, filtered_dataset = validate_dataset(
            dataset, School.Types.SIMPLE
        )

        # Should fail - all columns were filtered out, none remain
        assert validates is False
        # The message should indicate missing columns
        assert (
            "colonne richieste" in message.lower() or "intestazioni" in message.lower()
        )

    def test_annual_dataset_completely_invalid_column_names(self):
        """Test annual dataset CSV with completely invalid column names (all filtered out)"""
        dataset = Dataset()
        dataset.headers = ["invalid", "csv", "content"]
        dataset.append(["foo", "bar", "baz"])

        validates, message, filtered_dataset = validate_annual_dataset(dataset)

        # Should fail - all columns were filtered out, none remain
        assert validates is False
        # The message should indicate invalid headers or missing columns
        assert (
            "colonne richieste" in message.lower() or "intestazioni" in message.lower()
        )
