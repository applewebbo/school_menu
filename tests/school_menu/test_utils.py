from datetime import datetime
from unittest import mock
from unittest.mock import MagicMock, patch

import pytest
from django.http import Http404
from tablib import Dataset

from school_menu.models import School
from school_menu.utils import (
    ChoicesWidget,
    calculate_week,
    get_current_date,
    get_season,
    get_user,
    validate_dataset,
)

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


class TestGetUser:
    def test_get_user_success(self, mock_user_model):
        with (
            patch("school_menu.utils.get_user_model", return_value=mock_user_model),
            patch("school_menu.utils.get_object_or_404", return_value="mock_user"),
        ):
            user = get_user(pk=1)
            assert user == "mock_user"

    def test_get_user_not_found(self, mock_user_model):
        with (
            patch("school_menu.utils.get_user_model", return_value=mock_user_model),
            patch("school_menu.utils.get_object_or_404", side_effect=Http404),
        ):
            with pytest.raises(Http404):
                get_user(pk=999)


class TestImportMenu:
    def test_simple_meal_validate_success(self):
        dataset = Dataset()
        dataset.headers = ["giorno", "settimana", "pranzo", "spuntino"]
        dataset.append(["Lunedì", 1, "Pasta al Pomodoro", "Yogurt"])

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
        dataset.headers = ["giorno", "settimana", "pranzo", "spuntino"]
        dataset.append(["Lun", 1, "Pasta al Pomodoro", "Yogurt"])

        validates, message = validate_dataset(dataset, School.Types.SIMPLE)

        assert validates is False
        assert (
            message
            == 'Formato non valido. La colonna "giorno" contiene valori diversi dai giorni della settimana.'
        )

    def test_simple_meal_validate_non_integer_week(self):
        dataset = Dataset()
        dataset.headers = ["giorno", "settimana", "pranzo", "spuntino"]
        dataset.append(["Lunedì", "prima", "Pasta al Pomodoro", "Yogurt"])

        validates, message = validate_dataset(dataset, School.Types.SIMPLE)

        assert validates is False
        assert (
            message
            == 'Formato non valido. La colonna "settimana" contiene valori non numerici.'
        )

    def test_simple_meal_validate_wrong_week(self):
        dataset = Dataset()
        dataset.headers = ["giorno", "settimana", "pranzo", "spuntino"]
        dataset.append(["Lunedì", 5, "Pasta al Pomodoro", "Yogurt"])

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
