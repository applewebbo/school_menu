from datetime import date

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from school_menu.forms import (
    DetailedMealForm,
    SchoolClosureForm,
    SchoolForm,
    SimpleMealForm,
    SpecialDetailedMealForm,
    SpecialSimpleMealForm,
    UploadAnnualMenuForm,
    UploadMenuForm,
    allowed_upload_accept,
)
from school_menu.models import MAX_SCHOOL_CLOSURES, MAX_SPECIAL_DAYS, Meal, School

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

    def test_form_accepts_seeking_maintainer(self):
        form = SchoolForm(
            data={
                "name": "Test School",
                "city": "Test City",
                "season_choice": School.Seasons.INVERNALE,
                "week_bias": 1,
                "menu_type": School.Types.SIMPLE,
                "start_date": date(2024, 9, 1),
                "end_date": date(2025, 6, 30),
                "seeking_maintainer": True,
            }
        )
        assert form.is_valid(), form.errors
        assert form.cleaned_data["seeking_maintainer"] is True

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

    def test_form_rejects_self_mirror(self, user_factory, school_factory):
        user = user_factory()
        school = school_factory(user=user)

        form = SchoolForm(
            instance=school,
            data={
                "name": school.name,
                "city": school.city,
                "season_choice": School.Seasons.INVERNALE,
                "week_bias": 0,
                "menu_type": School.Types.SIMPLE,
                "start_date": date(2024, 9, 1),
                "end_date": date(2025, 6, 30),
                "mirror_from": school.pk,
            },
        )

        assert form.is_valid() is False
        assert "mirror_from" in form.errors

    def test_form_rejects_mirroring_a_school_that_already_mirrors(
        self, user_factory, school_factory
    ):
        root = school_factory(is_published=True)
        middle = school_factory(mirror_from=root)
        leaf_user = user_factory()
        leaf = school_factory(user=leaf_user)

        form = SchoolForm(
            instance=leaf,
            data={
                "name": leaf.name,
                "city": leaf.city,
                "season_choice": School.Seasons.INVERNALE,
                "week_bias": 0,
                "menu_type": School.Types.SIMPLE,
                "start_date": date(2024, 9, 1),
                "end_date": date(2025, 6, 30),
                "mirror_from": middle.pk,
            },
        )

        assert form.is_valid() is False
        assert "mirror_from" in form.errors

    def test_form_accepts_valid_mirror(self, user_factory, school_factory):
        source = school_factory(is_published=True)
        user = user_factory()
        school = school_factory(user=user)

        form = SchoolForm(
            instance=school,
            data={
                "name": school.name,
                "city": school.city,
                "season_choice": School.Seasons.INVERNALE,
                "week_bias": 0,
                "menu_type": School.Types.SIMPLE,
                "start_date": date(2024, 9, 1),
                "end_date": date(2025, 6, 30),
                "mirror_from": source.pk,
            },
        )

        assert form.is_valid(), form.errors
        assert form.cleaned_data["mirror_from"] == source

    def test_mirror_from_queryset_excludes_ineligible_schools(
        self, user_factory, school_factory
    ):
        user = user_factory()
        school = school_factory(user=user)
        root = school_factory(is_published=True)
        mirroring_school = school_factory(is_published=True, mirror_from=root)
        unpublished = school_factory(is_published=False)

        form = SchoolForm(instance=school)

        queryset = form.fields["mirror_from"].queryset
        assert root in queryset
        assert school not in queryset
        assert mirroring_school not in queryset
        assert unpublished not in queryset

    def test_mirror_from_queryset_keeps_stale_current_value(
        self, user_factory, school_factory
    ):
        source = school_factory(is_published=True)
        user = user_factory()
        school = school_factory(user=user, mirror_from=source)
        source.is_published = False
        source.save()

        form = SchoolForm(instance=school)

        assert source in form.fields["mirror_from"].queryset

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

    def test_form_invalid_file_type(self, settings):
        settings.AI_MENU_IMPORT_ENABLED = False
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


class TestAllowedUploadAccept:
    """iOS Safari mishandles <input accept> once it mixes more than one extension,
    silently leaving the field empty on submit even though the picker shows a filename.
    Pairing each extension with its MIME type is the documented workaround (#273)."""

    def test_pairs_every_extension_with_its_mime_type(self, settings):
        settings.AI_MENU_IMPORT_ENABLED = True

        accept = allowed_upload_accept()

        assert accept == (
            ".csv,.pdf,.xlsx,text/csv,application/pdf,"
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    def test_csv_only_when_ai_import_disabled(self, settings):
        settings.AI_MENU_IMPORT_ENABLED = False

        assert allowed_upload_accept() == ".csv,text/csv"


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

    def test_form_invalid_file_type(self, settings):
        settings.AI_MENU_IMPORT_ENABLED = False
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


class TestSpecialSimpleMealForm:
    def test_form(self, school_factory):
        school = school_factory()
        form = SpecialSimpleMealForm(
            data={
                "date": date(2026, 12, 8),
                "menu": "Test Menu",
                "morning_snack": "Frutta",
                "afternoon_snack": "Yogurt",
            },
            school=school,
        )

        assert form.is_valid() is True
        meal = form.save()
        assert meal.school == school
        assert meal.type == Meal.Types.STANDARD

    def test_rejects_weekend_date(self, school_factory):
        school = school_factory()
        form = SpecialSimpleMealForm(
            data={
                "date": date(2026, 12, 12),  # Saturday
                "menu": "Test Menu",
                "morning_snack": "Frutta",
                "afternoon_snack": "Yogurt",
            },
            school=school,
        )

        assert form.is_valid() is False
        assert "date" in form.errors

    def test_rejects_duplicate_date_for_same_school(
        self, school_factory, special_simple_meal_factory
    ):
        school = school_factory()
        special_simple_meal_factory(school=school, date=date(2026, 12, 8))
        form = SpecialSimpleMealForm(
            data={
                "date": date(2026, 12, 8),
                "menu": "Test Menu",
                "morning_snack": "Frutta",
                "afternoon_snack": "Yogurt",
            },
            school=school,
        )

        assert form.is_valid() is False
        assert "date" in form.errors

    def test_allows_keeping_same_date_on_update(
        self, school_factory, special_simple_meal_factory
    ):
        school = school_factory()
        meal = special_simple_meal_factory(school=school, date=date(2026, 12, 8))
        form = SpecialSimpleMealForm(
            data={
                "date": date(2026, 12, 8),
                "menu": "Updated Menu",
                "morning_snack": "Frutta",
                "afternoon_snack": "Yogurt",
            },
            school=school,
            instance=meal,
        )

        assert form.is_valid() is True, form.errors

    def test_rejects_beyond_max_special_days(
        self, school_factory, special_simple_meal_factory
    ):
        school = school_factory()
        for day in range(MAX_SPECIAL_DAYS):
            special_simple_meal_factory(school=school, date=date(2026, 12, 1 + day))
        form = SpecialSimpleMealForm(
            data={
                "date": date(2026, 12, 20),
                "menu": "Test Menu",
                "morning_snack": "Frutta",
                "afternoon_snack": "Yogurt",
            },
            school=school,
        )

        assert form.is_valid() is False


class TestSpecialDetailedMealForm:
    def test_form(self, school_factory):
        school = school_factory()
        form = SpecialDetailedMealForm(
            data={
                "date": date(2026, 12, 8),
                "first_course": "Test First Course",
                "second_course": "Test Second Course",
                "side_dish": "Test Side Dish",
                "fruit": "Test Fruit",
                "snack": "Test Snack",
            },
            school=school,
        )

        assert form.is_valid() is True
        meal = form.save()
        assert meal.school == school
        assert meal.type == Meal.Types.STANDARD

    def test_rejects_beyond_max_special_days(
        self, school_factory, special_detailed_meal_factory
    ):
        school = school_factory()
        for day in range(MAX_SPECIAL_DAYS):
            special_detailed_meal_factory(school=school, date=date(2026, 12, 1 + day))
        form = SpecialDetailedMealForm(
            data={
                "date": date(2026, 12, 20),
                "first_course": "Test First Course",
                "second_course": "Test Second Course",
                "side_dish": "Test Side Dish",
                "fruit": "Test Fruit",
                "snack": "Test Snack",
            },
            school=school,
        )

        assert form.is_valid() is False


class TestSchoolClosureForm:
    def test_form(self, school_factory):
        school = school_factory()
        form = SchoolClosureForm(data={"date": date(2026, 12, 8)}, school=school)

        assert form.is_valid() is True
        closure = form.save()
        assert closure.school == school

    def test_rejects_weekend_date(self, school_factory):
        school = school_factory()
        form = SchoolClosureForm(
            data={"date": date(2026, 12, 12)},  # Saturday
            school=school,
        )

        assert form.is_valid() is False
        assert "date" in form.errors

    def test_rejects_duplicate_date_for_same_school(
        self, school_factory, school_closure_factory
    ):
        school = school_factory()
        school_closure_factory(school=school, date=date(2026, 12, 8))
        form = SchoolClosureForm(data={"date": date(2026, 12, 8)}, school=school)

        assert form.is_valid() is False
        assert "date" in form.errors

    def test_allows_keeping_same_date_on_update(
        self, school_factory, school_closure_factory
    ):
        school = school_factory()
        closure = school_closure_factory(school=school, date=date(2026, 12, 8))
        form = SchoolClosureForm(
            data={"date": date(2026, 12, 8)}, school=school, instance=closure
        )

        assert form.is_valid() is True, form.errors

    def test_rejects_beyond_max_closures(self, school_factory, school_closure_factory):
        school = school_factory()
        for day in range(MAX_SCHOOL_CLOSURES):
            school_closure_factory(school=school, date=date(2026, 12, 1 + day))
        form = SchoolClosureForm(data={"date": date(2026, 12, 20)}, school=school)

        assert form.is_valid() is False
