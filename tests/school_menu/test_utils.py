from datetime import datetime
from unittest import mock
from unittest.mock import MagicMock

import pytest
from django.test import TestCase
from tablib import Dataset

from school_menu.models import School
from school_menu.utils import (
    ChoicesWidget,
    build_types_menu,
    calculate_week,
    get_alt_menu,
    get_alt_menu_from_school,
    get_current_date,
    get_season,
    get_user,
    validate_dataset,
)
from tests.school_menu.factories import SchoolFactory
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
        assert (
            calculate_week(week, bias) == expected
        ), f"Failed for week: {week}, bias: {bias}"


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
            assert (
                current_week == expected_week
            ), f"Expected week {expected_week}, got {current_week}"
            assert (
                current_day == expected_day
            ), f"Expected day {expected_day}, got {current_day}"


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
        SchoolFactory(user=user)

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
        SchoolFactory(user=user)

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


class TestGetAltMenuFromSchool(TestCase):
    def test_get_false(self):
        user = UserFactory()
        school = SchoolFactory(user=user)

        alt_menu = get_alt_menu_from_school(school)

        assert alt_menu is False

    def test_get_true(self):
        user = UserFactory()
        school = SchoolFactory(user=user, no_gluten=True)

        alt_menu = get_alt_menu_from_school(school)

        assert alt_menu is True


class TestBuildTypesMenu(TestCase):
    def test_with_standard_only(self):
        user = UserFactory()
        school = SchoolFactory(user=user)

        types_menu = build_types_menu(school)

        assert types_menu == {"Standard": "S"}

    def test_with_other_types(self):
        user = UserFactory()
        school = SchoolFactory(
            user=user, no_gluten=True, no_lactose=True, vegetarian=True, special=True
        )

        types_menu = build_types_menu(school)

        assert types_menu == {
            "Standard": "S",
            "No Glutine": "G",
            "No Lattosio": "L",
            "Vegetariano": "V",
            "Speciale": "P",
        }


class TestImportMenu:
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
