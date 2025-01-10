from datetime import date, datetime
from unittest import mock
from unittest.mock import MagicMock, patch

import pytest
from django.test import TestCase
from tablib import Dataset

from school_menu.models import AnnualMeal, School, SimpleMeal
from school_menu.utils import (
    ChoicesWidget,
    build_types_menu,
    calculate_week,
    fill_missing_dates,
    get_alt_menu,
    get_current_date,
    get_meals_for_annual_menu,
    get_season,
    get_user,
    validate_annual_dataset,
    validate_dataset,
)
from tests.school_menu.factories import (
    AnnualMealFactory,
    SchoolFactory,
    SimpleMealFactory,
)
from tests.users.factories import UserFactory

pytestmark = pytest.mark.django_db


class TestCalculateWeek:
    @pytest.mark.parametrize(
        "week, bias, expected",
        [
            (1, 0, 1),  # Test case 1: No bias, beginning of the month
            (4, 0, 4),  # Test case 2: No bias, end of the month
            (5, 0, 1),  # Test case 3: No bias, beginning of next month
            (8, 0, 4),  # Test case 4: No bias, end of next month
            (1, 3, 4),  # Test case 5: Positive bias, shifts to end of month
            (52, 0, 4),  # Test case 6: No bias, last week of the year
            (49, 3, 4),  # Test case 7: Positive bias, shifts to last week of the year
        ],
    )
    def test_calculate_week(self, week, bias, expected):
        assert calculate_week(week, bias) == expected, (
            f"Failed for week: {week}, bias: {bias}"
        )


class TestGetCurrentDate:
    # Test scenarios for different days of the week
    @pytest.mark.parametrize(
        "test_date, expected_week, expected_day",
        [
            ("2023-04-03", 14, 1),  # Monday
            ("2023-04-05", 14, 3),  # Wednesday
            ("2023-04-08", 15, 1),  # Saturday (should return next Monday)
            ("2023-04-09", 15, 1),  # Sunday (should return next Monday)
        ],
    )
    def test_get_current_date(self, test_date, expected_week, expected_day):
        # Mock datetime.now() to return a specific test date
        with mock.patch("school_menu.utils.datetime") as mock_datetime:
            mock_datetime.now.return_value = datetime.strptime(test_date, "%Y-%m-%d")
            mock_datetime.isocalendar = datetime.isocalendar
            current_week, current_day = get_current_date()
            assert current_week == expected_week, (
                f"Expected week {expected_week}, got {current_week}"
            )
            assert current_day == expected_day, (
                f"Expected day {expected_day}, got {current_day}"
            )


class TestGetSeason:
    @pytest.mark.parametrize(
        "current_date, season_choice, expected_season",
        [
            (
                datetime(2023, 1, 15),
                School.Seasons.AUTOMATICA,
                School.Seasons.INVERNALE,
            ),  # Winter case
            (
                datetime(2023, 6, 15),
                School.Seasons.AUTOMATICA,
                School.Seasons.PRIMAVERILE,
            ),  # Spring/Summer case
            (
                datetime(2023, 10, 1),
                School.Seasons.AUTOMATICA,
                School.Seasons.INVERNALE,
            ),  # Autumn, should be winter
            (
                datetime(2023, 9, 23),
                School.Seasons.AUTOMATICA,
                School.Seasons.INVERNALE,
            ),  # Winter Edge Case
            (
                datetime(2023, 6, 20),
                School.Seasons.AUTOMATICA,
                School.Seasons.PRIMAVERILE,
            ),  # Spring Edge Case
            (
                datetime(2023, 4, 1),
                School.Seasons.INVERNALE,
                School.Seasons.INVERNALE,
            ),  # Explicitly set to winter
            (
                datetime(2023, 1, 1),
                School.Seasons.PRIMAVERILE,
                School.Seasons.PRIMAVERILE,
            ),  # Explicitly set to spring
        ],
    )
    def test_get_season(
        self,
        current_date: datetime,
        season_choice: School.Seasons | School.Seasons | School.Seasons,
        expected_season: School.Seasons | School.Seasons,
    ):
        with mock.patch("school_menu.utils.datetime") as mock_datetime:
            mock_datetime.now.return_value = current_date
            school = School(season_choice=season_choice)
            assert get_season(school) == expected_season


@pytest.fixture
def mock_user_model():
    class MockUserModel:
        objects = MagicMock()

    return MockUserModel


class TestGetUser(TestCase):
    def test_get_user_with_standard_menu(self):
        user = UserFactory()
        SchoolFactory(
            user=user,
            no_gluten=False,
            no_lactose=False,
            vegetarian=False,
            special=False,
        )

        returned_user, alt_menu = get_user(user.pk)

        assert returned_user == user
        assert alt_menu is False

    def test_get_user_with_alternative_menu(self):
        user = UserFactory()
        SchoolFactory(
            user=user, no_gluten=True, no_lactose=False, vegetarian=False, special=False
        )

        returned_user, alt_menu = get_user(user.pk)

        assert returned_user == user
        assert alt_menu is True

    def test_get_user_without_school(self):
        user = UserFactory()

        returned_user, alt_menu = get_user(user.pk)

        assert returned_user == user
        assert alt_menu is False


class TestGetAltMenu(TestCase):
    def test_get_alt_menu_standard(self):
        user = UserFactory()
        SchoolFactory(
            user=user,
            no_gluten=False,
            no_lactose=False,
            vegetarian=False,
            special=False,
        )

        alt_menu = get_alt_menu(user)

        assert alt_menu is False

    def test_get_alt_menu_no_gluten(self):
        user = UserFactory()
        SchoolFactory(user=user, no_gluten=True)

        alt_menu = get_alt_menu(user)

        assert alt_menu is True

    def test_get_alt_menu_no_lactose(self):
        user = UserFactory()
        SchoolFactory(user=user, no_lactose=True)

        alt_menu = get_alt_menu(user)

        assert alt_menu is True

    def test_get_alt_menu_vegetarian(self):
        user = UserFactory()
        SchoolFactory(user=user, vegetarian=True)

        alt_menu = get_alt_menu(user)

        assert alt_menu is True

    def test_get_alt_menu_special(self):
        user = UserFactory()
        SchoolFactory(user=user, special=True)

        alt_menu = get_alt_menu(user)

        assert alt_menu is True


class TestBuildTypesMenu(TestCase):
    def test_with_standard_only(self):
        user = UserFactory()
        school = SchoolFactory(user=user, menu_type=School.Types.SIMPLE)
        SimpleMealFactory.create_batch(5, school=school, type=SimpleMeal.Types.STANDARD)

        meals = SimpleMeal.objects.all()

        types_menu = build_types_menu(meals, school)

        assert types_menu == {"Standard": "S"}

    def test_with_other_types(self):
        user = UserFactory()
        school = SchoolFactory(
            user=user, no_gluten=True, no_lactose=True, vegetarian=True, special=True
        )
        for type in SimpleMeal.Types.choices:
            SimpleMealFactory(school=school, type=type[0])
        meals = SimpleMeal.objects.all()

        types_menu = build_types_menu(meals, school)

        assert types_menu == {
            "Standard": "S",
            "No Glutine": "G",
            "No Lattosio": "L",
            "Vegetariano": "V",
            "Speciale": "P",
        }

    def test_with_some_inactive_types(self):
        user = UserFactory()
        school = SchoolFactory(
            user=user, no_gluten=True, no_lactose=False, vegetarian=True, special=False
        )
        for type in SimpleMeal.Types.choices:
            SimpleMealFactory(school=school, type=type[0])
        meals = SimpleMeal.objects.all()

        types_menu = build_types_menu(meals, school)

        assert types_menu == {
            "Standard": "S",
            "No Glutine": "G",
            "Vegetariano": "V",
        }


class TestValidateDataset(TestCase):
    def test_simple_meal_validate_success(self):
        dataset = Dataset()
        dataset.headers = ["giorno", "settimana", "pranzo", "spuntino", "merenda"]
        dataset.append(["Lunedì", 1, "Pasta al Pomodoro", "Yogurt", "Mela"])

        validates, message = validate_dataset(dataset, School.Types.SIMPLE)

        assert validates is True
        assert message is None

    def test_simple_meal_validate_missing_column(self):
        dataset = Dataset()
        dataset.headers = ["giorno", "settimana", "pranzo"]
        dataset.append(["Lunedì", 1, "Pasta al Pomodoro"])

        validates, message = validate_dataset(dataset, School.Types.SIMPLE)

        assert validates is False
        assert (
            message
            == "Formato non valido. Il file non contiene tutte le colonne richieste."
        )

    def test_simple_meal_validate_wrong_day(self):
        dataset = Dataset()
        dataset.headers = ["giorno", "settimana", "pranzo", "spuntino", "merenda"]
        dataset.append(["Lun", 1, "Pasta al Pomodoro", "Yogurt", "Mela"])

        validates, message = validate_dataset(dataset, School.Types.SIMPLE)

        assert validates is False
        assert (
            message
            == 'Formato non valido. La colonna "giorno" contiene valori diversi dai giorni della settimana.'
        )

    def test_simple_meal_validate_non_integer_week(self):
        dataset = Dataset()
        dataset.headers = ["giorno", "settimana", "pranzo", "spuntino", "merenda"]
        dataset.append(["Lunedì", "prima", "Pasta al Pomodoro", "Yogurt", "Mela"])

        validates, message = validate_dataset(dataset, School.Types.SIMPLE)

        assert validates is False
        assert (
            message
            == 'Formato non valido. La colonna "settimana" contiene valori non numerici.'
        )

    def test_simple_meal_validate_wrong_week(self):
        dataset = Dataset()
        dataset.headers = ["giorno", "settimana", "pranzo", "spuntino", "merenda"]
        dataset.append(["Lunedì", 5, "Pasta al Pomodoro", "Yogurt", "Mela"])

        validates, message = validate_dataset(dataset, School.Types.SIMPLE)

        assert validates is False
        assert (
            message
            == 'Formato non valido. La colonna "settimana" contiene valori non compresi fra 1 e 4.'
        )

    def test_detailed_meal_validate_success(self):
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
        dataset.append(
            [
                "Lunedì",
                1,
                "Pasta al Pomodoro",
                "Pollo Arrosto",
                "Fagiolini",
                "Mela",
                "Yogurt",
            ]
        )

        validates, message = validate_dataset(dataset, School.Types.DETAILED)

        assert validates is True
        assert message is None

    def test_detailed_meal_validate_missing_column(self):
        dataset = Dataset()
        dataset.headers = [
            "giorno",
            "settimana",
            "primo",
            "secondo",
            "contorno",
            "frutta",
        ]
        dataset.append(
            [
                "Lunedì",
                1,
                "Pasta al Pomodoro",
                "Pollo Arrosto",
                "Fagiolini",
                "Mela",
            ]
        )

        validates, message = validate_dataset(dataset, School.Types.DETAILED)

        assert validates is False
        assert (
            message
            == "Formato non valido. Il file non contiene tutte le colonne richieste."
        )

    def test_detailed_meal_validate_wrong_day(self):
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
        dataset.append(
            [
                "Lun",
                1,
                "Pasta al Pomodoro",
                "Pollo Arrosto",
                "Fagiolini",
                "Mela",
                "Yogurt",
            ]
        )

        validates, message = validate_dataset(dataset, School.Types.DETAILED)

        assert validates is False
        assert (
            message
            == 'Formato non valido. La colonna "giorno" contiene valori diversi dai giorni della settimana.'
        )

    def test_detailed_meal_validate_non_integer_week(self):
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
        dataset.append(
            [
                "Lunedì",
                "prima",
                "Pasta al Pomodoro",
                "Pollo Arrosto",
                "Fagiolini",
                "Mela",
                "Yogurt",
            ]
        )

        validates, message = validate_dataset(dataset, School.Types.DETAILED)

        assert validates is False
        assert (
            message
            == 'Formato non valido. La colonna "settimana" contiene valori non numerici.'
        )

    def test_detailed_meal_validate_wrong_week(self):
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
        dataset.append(
            [
                "Lunedì",
                5,
                "Pasta al Pomodoro",
                "Pollo Arrosto",
                "Fagiolini",
                "Mela",
                "Yogurt",
            ]
        )

        validates, message = validate_dataset(dataset, School.Types.DETAILED)

        assert validates is False
        assert (
            message
            == 'Formato non valido. La colonna "settimana" contiene valori non compresi fra 1 e 4.'
        )


class TestValidateAnnualDataset:
    def test_validate_annual_dataset_success(self):
        dataset = Dataset()
        dataset.headers = [
            "data",
            "primo",
            "secondo",
            "contorno",
            "frutta",
            "altro",
        ]
        dataset.append(["28/12/2024", "Pasta", "Bistecca", "Fagiolini", "Mela", "Pane"])

        validates, message = validate_annual_dataset(dataset)

        assert validates is True
        assert message is None

    def test_detailed_meal_validate_missing_column(self):
        dataset = Dataset()
        dataset.headers = [
            "data",
            "primo",
            "secondo",
            "contorno",
            "frutta",
        ]
        dataset.append(["28/12/2024", "Pasta", "Bistecca", "Fagiolini", "Mela"])

        validates, message = validate_annual_dataset(dataset)

        assert validates is False
        assert (
            message
            == "Formato non valido. Il file non contiene tutte le colonne richieste."
        )

    def test_detailed_meal_validate_wrong_daye(self):
        dataset = Dataset()
        dataset.headers = [
            "data",
            "primo",
            "secondo",
            "contorno",
            "frutta",
            "altro",
        ]
        dataset.append(["28/12", "Pasta", "Bistecca", "Fagiolini", "Mela", "Pane"])

        validates, message = validate_annual_dataset(dataset)

        assert validates is False
        assert (
            message
            == 'Formato non valido. La colonna "data" contiene date in formato non valido. Usa il formato GG/MM/AAAA'
        )


class TestChoicesWidget:
    @pytest.fixture
    def choices_widget(self):
        choices = [("CHOC", "Chocolate"), ("VAN", "Vanilla"), ("STRAW", "Strawberry")]
        return ChoicesWidget(choices)

    def test_initialization(self, choices_widget):
        expected_choices = {
            "CHOC": "Chocolate",
            "VAN": "Vanilla",
            "STRAW": "Strawberry",
        }
        expected_revert_choices = {
            "Chocolate": "CHOC",
            "Vanilla": "VAN",
            "Strawberry": "STRAW",
        }
        assert choices_widget.choices == expected_choices
        assert choices_widget.revert_choices == expected_revert_choices

    def test_clean(self, choices_widget):
        assert choices_widget.clean("Chocolate") == "CHOC"
        assert choices_widget.clean("Vanilla") == "VAN"
        assert choices_widget.clean("Strawberry") == "STRAW"
        assert choices_widget.clean("Nonexistent") == "Nonexistent"
        assert choices_widget.clean(None) is None

    def test_render(self, choices_widget):
        assert choices_widget.render("CHOC") == "Chocolate"
        assert choices_widget.render("VAN") == "Vanilla"
        assert choices_widget.render("STRAW") == "Strawberry"
        assert choices_widget.render("Nonexistent") == ""


class GetMealsForAnnualMenuTests(TestCase):
    @patch("school_menu.utils.datetime")
    def test_get_meals_weekday(self, mock_datetime):
        """Test getting meals on a regular weekday (Wednesday)"""
        test_date = date(2024, 1, 3)  # A Wednesday
        mock_datetime.now.return_value = datetime(2024, 1, 3)
        school = SchoolFactory()
        meal = AnnualMealFactory(school=school, date=test_date, type="S")

        weekly_meals, today_meals = get_meals_for_annual_menu(school)

        assert today_meals.first() == meal
        assert meal in weekly_meals

    @patch("school_menu.utils.datetime")
    def test_get_meals_weekend_saturday(self, mock_datetime):
        """Test getting meals when current day is Saturday"""
        date(2024, 1, 6)
        next_monday = date(2024, 1, 8)
        mock_datetime.now.return_value = datetime(2024, 1, 6)
        school = SchoolFactory()
        monday_meal = AnnualMealFactory(school=school, date=next_monday, type="S")

        weekly_meals, today_meals = get_meals_for_annual_menu(school)

        assert today_meals.first() == monday_meal
        assert monday_meal in weekly_meals

    @patch("school_menu.utils.datetime")
    def test_get_meals_weekend_sunday(self, mock_datetime):
        """Test getting meals when current day is Sunday"""
        date(2024, 1, 7)
        next_monday = date(2024, 1, 8)
        mock_datetime.now.return_value = datetime(2024, 1, 7)
        school = SchoolFactory()
        monday_meal = AnnualMealFactory(school=school, date=next_monday, type="S")

        weekly_meals, today_meals = get_meals_for_annual_menu(school)

        assert today_meals.first() == monday_meal
        assert monday_meal in weekly_meals

    @patch("school_menu.utils.datetime")
    def test_get_meals_week_transition(self, mock_datetime):
        """Test getting meals during week transition"""
        friday = date(2024, 1, 5)
        next_monday = date(2024, 1, 8)
        mock_datetime.now.return_value = datetime(2024, 1, 7)  # Sunday
        school = SchoolFactory()
        friday_meal = AnnualMealFactory(school=school, date=friday, type="S")
        monday_meal = AnnualMealFactory(school=school, date=next_monday, type="S")

        weekly_meals, today_meals = get_meals_for_annual_menu(school)

        assert today_meals.first() == monday_meal
        assert monday_meal in weekly_meals
        assert friday_meal not in weekly_meals


class TestFillMissingDates(TestCase):
    def setUp(self):
        self.school = SchoolFactory()
        self.meal_type = "S"  # Standard meal type

        # Create some initial dates with gaps
        self.start_date = date(2023, 9, 1)  # Friday
        self.end_date = date(2023, 9, 8)  # Friday

        # Create only start and end date meals
        AnnualMeal.objects.create(
            school=self.school,
            type=self.meal_type,
            date=self.start_date,
            day=5,
            is_active=True,
        )
        AnnualMeal.objects.create(
            school=self.school,
            type=self.meal_type,
            date=self.end_date,
            day=5,
            is_active=True,
        )

    def test_fill_missing_dates(self):
        fill_missing_dates(self.school, self.meal_type)

        # Should create meals for Mon-Thu (4 days) between the dates
        # Plus our 2 existing Friday meals
        total_meals = AnnualMeal.objects.filter(
            school=self.school, type=self.meal_type
        ).count()
        self.assertEqual(total_meals, 6)

    def test_missing_dates_are_inactive(self):
        fill_missing_dates(self.school, self.meal_type)

        # Check that newly created dates are marked as inactive
        new_meals = AnnualMeal.objects.filter(
            school=self.school, type=self.meal_type, is_active=False
        )
        self.assertEqual(new_meals.count(), 4)

    def test_existing_dates_unchanged(self):
        fill_missing_dates(self.school, self.meal_type)

        # Verify original meals still exist and are active
        original_meals = AnnualMeal.objects.filter(
            school=self.school, type=self.meal_type, is_active=True
        )
        self.assertEqual(original_meals.count(), 2)

    def test_weekends_skipped(self):
        fill_missing_dates(self.school, self.meal_type)

        # Check no meals created for weekend dates
        weekend_meals = AnnualMeal.objects.filter(
            school=self.school,
            type=self.meal_type,
            date__week_day__in=[1, 7],  # Sunday=1, Saturday=7 in Django
        )
        self.assertEqual(weekend_meals.count(), 0)
