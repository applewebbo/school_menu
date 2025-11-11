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

    def test_form_duplicate_slug_rejected_on_creation(
        self, user_factory, school_factory
    ):
        """Test that creating a school with duplicate name+city is rejected."""
        user1 = user_factory()

        # Create first school
        school_factory(user=user1, name="Scuola Elementare", city="Roma")

        # Try to create second school with same name and city
        form = SchoolForm(
            data={
                "name": "Scuola Elementare",
                "city": "Roma",
                "season_choice": School.Seasons.INVERNALE,
                "week_bias": 0,
                "menu_type": School.Types.SIMPLE,
                "start_date": date(2024, 9, 1),
                "end_date": date(2025, 6, 30),
            }
        )

        assert form.is_valid() is False
        assert "__all__" in form.errors
        error_message = form.errors["__all__"][0]
        assert (
            "Esiste già una scuola con nome 'Scuola Elementare' nella città 'Roma'"
            in error_message
        )

    def test_form_duplicate_slug_rejected_on_update(self, user_factory, school_factory):
        """Test that updating a school's city to create duplicate slug is rejected."""
        user1 = user_factory()
        user2 = user_factory()

        # Create two schools with same name, different cities
        school_factory(user=user1, name="Scuola Elementare", city="Roma")
        school2 = school_factory(user=user2, name="Scuola Elementare", city="Milano")

        original_slug = school2.slug
        assert original_slug == "scuola-elementare-milano"

        # Try to update school2's city to match school1 (Milano → Roma)
        form = SchoolForm(
            instance=school2,
            data={
                "name": "Scuola Elementare",
                "city": "Roma",  # Changing to same city as school1
                "season_choice": School.Seasons.INVERNALE,
                "week_bias": 0,
                "menu_type": School.Types.SIMPLE,
                "start_date": date(2024, 9, 1),
                "end_date": date(2025, 6, 30),
            },
        )

        # Form should be invalid due to duplicate slug
        assert form.is_valid() is False
        assert "__all__" in form.errors

        # Verify slug hasn't changed
        school2.refresh_from_db()
        assert school2.slug == original_slug

    def test_form_allows_update_without_name_city_change(
        self, user_factory, school_factory
    ):
        """Test that updating other fields without changing name/city works fine."""
        user = user_factory()
        school = school_factory(user=user, name="Scuola Elementare", city="Roma")
        original_slug = school.slug

        # Update only menu settings, not name or city
        form = SchoolForm(
            instance=school,
            data={
                "name": "Scuola Elementare",
                "city": "Roma",
                "season_choice": School.Seasons.PRIMAVERILE,
                "week_bias": 2,
                "menu_type": School.Types.DETAILED,
                "start_date": date(2024, 9, 1),
                "end_date": date(2025, 6, 30),
            },
        )

        assert form.is_valid() is True

        # Save and verify slug hasn't changed
        school = form.save(commit=False)
        school.save()
        assert school.slug == original_slug


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
