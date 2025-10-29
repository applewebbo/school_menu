from datetime import date
from unittest.mock import patch

import pytest

from school_menu.models import Meal

pytestmark = pytest.mark.django_db


class TestDetailedMealModel:
    def test_factory(self, user_factory, school_factory, detailed_meal_factory):
        """Test detailed meal factory"""

        user = user_factory()
        school = school_factory(user=user)
        detailed_meal = detailed_meal_factory(
            school=school, day=1, week=1, season=Meal.Seasons.INVERNALE
        )

        assert detailed_meal.__str__() == "Lunedì - Settimana 1 [Invernale]"


class TestSimpleMealModel:
    def test_factory(self, user_factory, school_factory, simple_meal_factory):
        """Test detailed meal factory"""

        user = user_factory()
        school = school_factory(user=user)
        simple_meal = simple_meal_factory(
            school=school, day=1, week=1, season=Meal.Seasons.INVERNALE
        )

        assert simple_meal.__str__() == "Lunedì - Settimana 1 [Invernale]"


class TestSchoolModel:
    def test_factory(self, user_factory, school_factory):
        user = user_factory(email="test@email.com")
        school = school_factory(user=user, name="Test School", city="Test City")

        assert school.__str__() == "Test School - Test City (test@email.com)"

    def test_absolute_url(self, school_factory):
        school = school_factory()

        assert school.get_absolute_url() == f"/menu/{school.slug}/"


class TestAnnualMenuModel:
    def test_factory(self, user_factory, school_factory, annual_meal_factory):
        user = user_factory()
        school = school_factory(user=user, name="Test School")
        annual_meal = annual_meal_factory(school=school, date=date(2022, 1, 1))

        assert annual_meal.__str__() == "Test School [01/01]"


class TestCacheInvalidationOnModelSave:
    """Test cache invalidation when models are saved/deleted."""

    @patch("school_menu.models.invalidate_meal_cache")
    def test_detailed_meal_save_invalidates_cache(
        self, mock_invalidate, user_factory, school_factory, detailed_meal_factory
    ):
        """Test that saving a DetailedMeal invalidates the meal cache."""
        user = user_factory()
        school = school_factory(user=user)

        # Create a detailed meal (triggers save)
        _detailed_meal = detailed_meal_factory(school=school)  # noqa: F841

        # Verify invalidate_meal_cache was called with correct school_id
        mock_invalidate.assert_called_with(school.id)

    @patch("school_menu.models.invalidate_meal_cache")
    def test_detailed_meal_delete_invalidates_cache(
        self, mock_invalidate, user_factory, school_factory, detailed_meal_factory
    ):
        """Test that deleting a DetailedMeal invalidates the meal cache."""
        user = user_factory()
        school = school_factory(user=user)

        # Create a detailed meal
        detailed_meal = detailed_meal_factory(school=school)
        mock_invalidate.reset_mock()

        # Delete the meal
        detailed_meal.delete()

        # Verify invalidate_meal_cache was called with correct school_id
        mock_invalidate.assert_called_with(school.id)

    @patch("school_menu.models.invalidate_meal_cache")
    def test_simple_meal_save_invalidates_cache(
        self, mock_invalidate, user_factory, school_factory, simple_meal_factory
    ):
        """Test that saving a SimpleMeal invalidates the meal cache."""
        user = user_factory()
        school = school_factory(user=user)

        # Create a simple meal (triggers save)
        _simple_meal = simple_meal_factory(school=school)  # noqa: F841

        # Verify invalidate_meal_cache was called with correct school_id
        mock_invalidate.assert_called_with(school.id)

    @patch("school_menu.models.invalidate_meal_cache")
    def test_simple_meal_delete_invalidates_cache(
        self, mock_invalidate, user_factory, school_factory, simple_meal_factory
    ):
        """Test that deleting a SimpleMeal invalidates the meal cache."""
        user = user_factory()
        school = school_factory(user=user)

        # Create a simple meal
        simple_meal = simple_meal_factory(school=school)
        mock_invalidate.reset_mock()

        # Delete the meal
        simple_meal.delete()

        # Verify invalidate_meal_cache was called with correct school_id
        mock_invalidate.assert_called_with(school.id)

    @patch("school_menu.models.invalidate_meal_cache")
    def test_annual_meal_save_invalidates_cache(
        self, mock_invalidate, user_factory, school_factory, annual_meal_factory
    ):
        """Test that saving an AnnualMeal invalidates the meal cache."""
        user = user_factory()
        school = school_factory(user=user)

        # Create an annual meal (triggers save)
        _annual_meal = annual_meal_factory(school=school)  # noqa: F841

        # Verify invalidate_meal_cache was called with correct school_id
        mock_invalidate.assert_called_with(school.id)

    @patch("school_menu.models.invalidate_meal_cache")
    def test_annual_meal_delete_invalidates_cache(
        self, mock_invalidate, user_factory, school_factory, annual_meal_factory
    ):
        """Test that deleting an AnnualMeal invalidates the meal cache."""
        user = user_factory()
        school = school_factory(user=user)

        # Create an annual meal
        annual_meal = annual_meal_factory(school=school)
        mock_invalidate.reset_mock()

        # Delete the meal
        annual_meal.delete()

        # Verify invalidate_meal_cache was called with correct school_id
        mock_invalidate.assert_called_with(school.id)

    @patch("school_menu.models.invalidate_school_cache")
    def test_school_save_invalidates_cache(
        self, mock_invalidate, user_factory, school_factory
    ):
        """Test that saving a School invalidates all school caches."""
        user = user_factory()

        # Create a school (triggers save)
        school = school_factory(user=user)

        # Verify invalidate_school_cache was called with correct school_id and slug
        mock_invalidate.assert_called_with(school.id, school.slug)

    @patch("school_menu.models.invalidate_meal_cache")
    def test_detailed_meal_save_without_school_doesnt_invalidate(
        self, mock_invalidate, detailed_meal_factory
    ):
        """Test that saving a DetailedMeal without school doesn't call invalidate."""
        # Create a detailed meal without school
        _detailed_meal = detailed_meal_factory(school=None)  # noqa: F841

        # Verify invalidate_meal_cache was NOT called
        mock_invalidate.assert_not_called()

    @patch("school_menu.models.invalidate_meal_cache")
    def test_simple_meal_save_without_school_doesnt_invalidate(
        self, mock_invalidate, simple_meal_factory
    ):
        """Test that saving a SimpleMeal without school doesn't call invalidate."""
        # Create a simple meal without school
        _simple_meal = simple_meal_factory(school=None)  # noqa: F841

        # Verify invalidate_meal_cache was NOT called
        mock_invalidate.assert_not_called()

    @patch("school_menu.models.invalidate_meal_cache")
    def test_annual_meal_save_without_school_doesnt_invalidate(
        self, mock_invalidate, annual_meal_factory
    ):
        """Test that saving an AnnualMeal without school doesn't call invalidate."""
        # Create an annual meal without school
        _annual_meal = annual_meal_factory(school=None)  # noqa: F841

        # Verify invalidate_meal_cache was NOT called
        mock_invalidate.assert_not_called()

    @patch("school_menu.models.invalidate_meal_cache")
    def test_detailed_meal_delete_without_school_doesnt_invalidate(
        self, mock_invalidate, detailed_meal_factory
    ):
        """Test that deleting a DetailedMeal without school doesn't call invalidate."""
        # Create a detailed meal without school
        detailed_meal = detailed_meal_factory(school=None)
        mock_invalidate.reset_mock()

        # Delete the meal
        detailed_meal.delete()

        # Verify invalidate_meal_cache was NOT called
        mock_invalidate.assert_not_called()

    @patch("school_menu.models.invalidate_meal_cache")
    def test_simple_meal_delete_without_school_doesnt_invalidate(
        self, mock_invalidate, simple_meal_factory
    ):
        """Test that deleting a SimpleMeal without school doesn't call invalidate."""
        # Create a simple meal without school
        simple_meal = simple_meal_factory(school=None)
        mock_invalidate.reset_mock()

        # Delete the meal
        simple_meal.delete()

        # Verify invalidate_meal_cache was NOT called
        mock_invalidate.assert_not_called()

    @patch("school_menu.models.invalidate_meal_cache")
    def test_annual_meal_delete_without_school_doesnt_invalidate(
        self, mock_invalidate, annual_meal_factory
    ):
        """Test that deleting an AnnualMeal without school doesn't call invalidate."""
        # Create an annual meal without school
        annual_meal = annual_meal_factory(school=None)
        mock_invalidate.reset_mock()

        # Delete the meal
        annual_meal.delete()

        # Verify invalidate_meal_cache was NOT called
        mock_invalidate.assert_not_called()
