import pytest

from school_menu.models import Meal

pytestmark = pytest.mark.django_db


class TestSchoolModel:
    def test_factory(self, user_factory, school_factory):
        """Test school factory"""

        user = user_factory(email="test@test.com")
        school = school_factory(user=user, name="Test School", city="Test City")

        assert school.__str__() == "Test School - Test City (test@test.com)"
        assert school.user == user


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
