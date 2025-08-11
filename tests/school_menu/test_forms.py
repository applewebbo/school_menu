from datetime import date

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from school_menu.forms import (
    DetailedMealForm,
    SchoolForm,
    SimpleMealForm,
    UploadAnnualMenuForm,
    UploadMenuForm,
)
from school_menu.models import Meal, School

pytestmark = pytest.mark.django_db


class TestSchoolForm:
    def test_form(self):
        form = SchoolForm(
            data={
                "name": "Test School",
                "city": "Test City",
                "season_choice": School.Seasons.INVERNALE,
                "week_bias": 1,
                "menu_type": School.Types.SIMPLE,
                "start_date": date(2024, 9, 1),
                "end_date": date(2025, 6, 30),
            }
        )
        assert form.is_valid(), form.errors

    def test_form_no_data(self):
        form = SchoolForm(data={})
        assert form.is_valid() is False
        assert form.errors == {
            "name": ["Campo obbligatorio."],
            "city": ["Campo obbligatorio."],
            "season_choice": ["Campo obbligatorio."],
            "week_bias": ["Campo obbligatorio."],
            "menu_type": ["Campo obbligatorio."],
            "start_date": ["Campo obbligatorio."],
            "end_date": ["Campo obbligatorio."],
        }


class TestUploadMenuForm:
    def test_form_with_csv_file(self):
        # Create a mock file object
        mock_file = SimpleUploadedFile(
            "test.csv", b"file_content", content_type="text/csv"
        )

        # Initialize the form with mock data and file
        form = UploadMenuForm(
            data={"season": Meal.Seasons.INVERNALE}, files={"file": mock_file}
        )

        # Assert the form is valid
        assert form.is_valid() is True

    def test_form_invalid_file_type(self):
        # Create a mock file object
        mock_file = SimpleUploadedFile(
            "test.txt", b"file_content", content_type="text/plain"
        )

        # Initialize the form with mock data and file
        form = UploadMenuForm(
            data={"season": Meal.Seasons.INVERNALE}, files={"file": mock_file}
        )

        # Assert the form is invalid
        assert form.is_valid() is False
        assert form.errors == {"file": ["Il file deve essere in formato csv"]}

    def def_form_no_file(self):
        # Initialize the form with mock data and file
        form = UploadMenuForm(data={"season": Meal.Seasons.INVERNALE}, files={})

        # Assert the form is invalid
        assert form.is_valid() is False
        assert form.errors == {"file": ["Questo campo è obbligatorio."]}


class TestSimpleMealForm:
    def test_form(self, school_factory):
        school = school_factory()
        form = SimpleMealForm(
            data={
                "day": Meal.Days.LUNEDÌ,
                "week": Meal.Weeks.SETTIMANA_1,
                "season": Meal.Seasons.INVERNALE,
                "type": Meal.Types.STANDARD,
                "school": school.id,
                "menu": "Test Menu",
                "snack": "Test Snack",
            }
        )

        assert form.is_valid() is True


class TestDetailedMealForm:
    def test_form(self, school_factory):
        school = school_factory()
        form = DetailedMealForm(
            data={
                "day": Meal.Days.LUNEDÌ,
                "week": Meal.Weeks.SETTIMANA_1,
                "season": Meal.Seasons.INVERNALE,
                "type": Meal.Types.STANDARD,
                "school": school.id,
                "first_course": "Test First Course",
                "second_course": "Test Second Course",
                "side_dish": "Test Side Dish",
                "fruit": "Test Fruit",
                "snack": "Test Snack",
            }
        )

        assert form.is_valid() is True


class TestAnnualMenuForm:
    def test_form_with_csv_file(self):
        # Create a mock file object
        mock_file = SimpleUploadedFile(
            "test.csv", b"file_content", content_type="text/csv"
        )

        # Initialize the form with mock data and file
        form = UploadAnnualMenuForm(files={"file": mock_file})

        # Assert the form is valid
        assert form.is_valid() is True

    def test_form_invalid_file_type(self):
        # Create a mock file object
        mock_file = SimpleUploadedFile(
            "test.txt", b"file_content", content_type="text/plain"
        )

        # Initialize the form with mock data and file
        form = UploadAnnualMenuForm(files={"file": mock_file})

        # Assert the form is invalid
        assert form.is_valid() is False
        assert form.errors == {"file": ["Il file deve essere in formato csv"]}

    def def_form_no_file(self):
        # Initialize the form with mock data and file
        form = UploadMenuForm(files={})

        # Assert the form is invalid
        assert form.is_valid() is False
        assert form.errors == {"file": ["Questo campo è obbligatorio."]}
