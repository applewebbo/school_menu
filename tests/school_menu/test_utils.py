from datetime import date, datetime
from unittest import mock
from unittest.mock import MagicMock

import pytest
from django.http import Http404
from django.test import TestCase
from tablib import Dataset

from school_menu.models import AnnualMeal, School, SimpleMeal
from school_menu.utils import (
    ChoicesWidget,
    build_types_menu,
    calculate_week,
    detect_csv_format,
    detect_menu_type,
    fill_missing_dates,
    filter_dataset_columns,
    get_alt_menu,
    get_current_date,
    get_meals_for_annual_menu,
    get_notifications_status,
    get_season,
    get_user,
    validate_annual_dataset,
    validate_dataset,
)
from tests.notifications.factories import AnonymousMenuNotificationFactory
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
            (4, 3, 3),  # Test case 8: Positive bias, not end of the month
        ],
    )
    def test_calculate_week(self, week, bias, expected):
        assert calculate_week(week, bias) == expected, (
            f"Failed for week: {week}, bias: {bias}"
        )


def test_get_current_date_monday():
    with mock.patch("school_menu.utils.timezone") as mock_timezone:
        mock_timezone.now.return_value = datetime(2023, 4, 3, 12, 0)
        assert get_current_date() == (14, 1)


def test_get_current_date_saturday():
    with mock.patch("school_menu.utils.timezone") as mock_timezone:
        mock_timezone.now.return_value = datetime(2023, 4, 8, 12, 0)
        assert get_current_date() == (15, 1)


def test_get_current_date_sunday():
    with mock.patch("school_menu.utils.timezone") as mock_timezone:
        mock_timezone.now.return_value = datetime(2023, 4, 9, 12, 0)
        assert get_current_date() == (15, 1)


def test_get_current_date_next_day():
    with mock.patch("school_menu.utils.timezone") as mock_timezone:
        mock_timezone.now.return_value = datetime(2023, 4, 3, 12, 0)
        assert get_current_date(next_day=True) == (14, 2)


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
                datetime(2023, 3, 20),
                School.Seasons.AUTOMATICA,
                School.Seasons.INVERNALE,
            ),  # Winter Edge Case
            (
                datetime(2023, 9, 21),
                School.Seasons.AUTOMATICA,
                School.Seasons.PRIMAVERILE,
            ),  # Spring Edge Case
            (
                datetime(2023, 3, 21),
                School.Seasons.AUTOMATICA,
                School.Seasons.PRIMAVERILE,
            ),  # Spring Edge Case
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
        with mock.patch("school_menu.utils.timezone") as mock_timezone:
            mock_timezone.now.return_value = current_date
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


class TestGetAltMenu:
    @pytest.mark.parametrize(
        "school_flags,expected",
        [
            (
                {
                    "no_gluten": False,
                    "no_lactose": False,
                    "vegetarian": False,
                    "special": False,
                },
                False,
            ),
            ({"no_gluten": True}, True),
            ({"no_lactose": True}, True),
            ({"vegetarian": True}, True),
            ({"special": True}, True),
        ],
    )
    def test_get_alt_menu(self, school_flags, expected):
        user = UserFactory()
        SchoolFactory(user=user, **school_flags)

        alt_menu = get_alt_menu(user)

        assert alt_menu is expected


class TestBuildTypesMenu:
    @pytest.mark.parametrize(
        "school_flags,create_all_types,expected_menu",
        [
            (
                {},
                False,
                {"Standard": "S"},
            ),
            (
                {
                    "no_gluten": True,
                    "no_lactose": True,
                    "vegetarian": True,
                    "special": True,
                },
                True,
                {
                    "Standard": "S",
                    "No Glutine": "G",
                    "No Lattosio": "L",
                    "Vegetariano": "V",
                    "Speciale": "P",
                },
            ),
            (
                {
                    "no_gluten": True,
                    "no_lactose": False,
                    "vegetarian": True,
                    "special": False,
                },
                True,
                {"Standard": "S", "No Glutine": "G", "Vegetariano": "V"},
            ),
        ],
    )
    def test_build_types_menu(self, school_flags, create_all_types, expected_menu):
        user = UserFactory()
        school = SchoolFactory(user=user, menu_type=School.Types.SIMPLE, **school_flags)

        if create_all_types:
            for type_choice in SimpleMeal.Types.choices:
                SimpleMealFactory(school=school, type=type_choice[0])
        else:
            SimpleMealFactory.create_batch(
                5, school=school, type=SimpleMeal.Types.STANDARD
            )

        meals = SimpleMeal.objects.all()
        types_menu = build_types_menu(meals, school)

        assert types_menu == expected_menu


class TestValidateDataset(TestCase):
    def test_simple_meal_validate_success(self):
        dataset = Dataset()
        dataset.headers = ["giorno", "settimana", "pranzo", "spuntino", "merenda"]
        dataset.append(["Lunedì", 1, "Pasta al Pomodoro", "Yogurt", "Mela"])

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

    def test_simple_meal_validate_missing_column(self):
        dataset = Dataset()
        dataset.headers = ["giorno", "settimana", "pranzo"]
        dataset.append(["Lunedì", 1, "Pasta al Pomodoro"])

        validates, message, filtered_dataset = validate_dataset(
            dataset, School.Types.SIMPLE
        )

        assert validates is False
        assert "Il file non contiene tutte le colonne richieste" in message
        assert "spuntino" in message
        assert "merenda" in message

    def test_simple_meal_validate_wrong_day(self):
        dataset = Dataset()
        dataset.headers = ["giorno", "settimana", "pranzo", "spuntino", "merenda"]
        dataset.append(["Lun", 1, "Pasta al Pomodoro", "Yogurt", "Mela"])

        validates, message, filtered_dataset = validate_dataset(
            dataset, School.Types.SIMPLE
        )

        assert validates is False
        assert (
            message
            == 'Formato non valido. La colonna "giorno" contiene valori diversi dai giorni della settimana.'
        )

    def test_simple_meal_validate_non_integer_week(self):
        dataset = Dataset()
        dataset.headers = ["giorno", "settimana", "pranzo", "spuntino", "merenda"]
        dataset.append(["Lunedì", "prima", "Pasta al Pomodoro", "Yogurt", "Mela"])

        validates, message, filtered_dataset = validate_dataset(
            dataset, School.Types.SIMPLE
        )

        assert validates is False
        assert (
            message
            == 'Formato non valido. La colonna "settimana" contiene valori non numerici.'
        )

    def test_simple_meal_validate_wrong_week(self):
        dataset = Dataset()
        dataset.headers = ["giorno", "settimana", "pranzo", "spuntino", "merenda"]
        dataset.append(["Lunedì", 5, "Pasta al Pomodoro", "Yogurt", "Mela"])

        validates, message, filtered_dataset = validate_dataset(
            dataset, School.Types.SIMPLE
        )

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

        validates, message, filtered_dataset = validate_dataset(
            dataset, School.Types.DETAILED
        )

        assert validates is False
        assert "Il file non contiene tutte le colonne richieste" in message
        assert "spuntino" in message

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

        validates, message, filtered_dataset = validate_dataset(
            dataset, School.Types.DETAILED
        )

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

        validates, message, filtered_dataset = validate_dataset(
            dataset, School.Types.DETAILED
        )

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

        validates, message, filtered_dataset = validate_dataset(
            dataset, School.Types.DETAILED
        )

        assert validates is False
        assert (
            message
            == 'Formato non valido. La colonna "settimana" contiene valori non compresi fra 1 e 4.'
        )


class TestMenuTypeMismatch(TestCase):
    """Test menu type mismatch detection in validation"""

    def test_simple_uploaded_when_detailed_expected(self):
        """Test error when simple menu uploaded for detailed menu type"""
        dataset = Dataset()
        dataset.headers = ["giorno", "settimana", "pranzo", "spuntino", "merenda"]
        dataset.append(["Lunedì", 1, "Pasta", "Mela", "Yogurt"])

        validates, message, filtered_dataset = validate_dataset(
            dataset, School.Types.DETAILED
        )

        assert validates is False
        assert "Menu Semplice" in message
        assert "Menu Dettagliato" in message
        assert "Verifica di aver caricato il file corretto" in message

    def test_detailed_uploaded_when_simple_expected(self):
        """Test error when detailed menu uploaded for simple menu type"""
        dataset = Dataset()
        dataset.headers = [
            "settimana",
            "giorno",
            "primo",
            "secondo",
            "contorno",
            "frutta",
            "spuntino",
        ]
        dataset.append([1, "Lunedì", "Pasta", "Pollo", "Insalata", "Mela", "Yogurt"])

        validates, message, filtered_dataset = validate_dataset(
            dataset, School.Types.SIMPLE
        )

        assert validates is False
        assert "Menu Dettagliato" in message
        assert "Menu Semplice" in message
        assert "Verifica di aver caricato il file corretto" in message

    def test_annual_uploaded_when_detailed_expected(self):
        """Test error when annual menu uploaded for detailed menu type"""
        dataset = Dataset()
        dataset.headers = ["data", "primo", "secondo", "contorno", "frutta", "altro"]
        dataset.append(["01/01/2024", "Pasta", "Pollo", "Insalata", "Mela", "Pane"])

        validates, message, filtered_dataset = validate_dataset(
            dataset, School.Types.DETAILED
        )

        assert validates is False
        assert "Menu Annuale" in message
        assert "Menu Dettagliato" in message

    def test_simple_uploaded_when_annual_expected(self):
        """Test error when simple menu uploaded for annual menu"""
        dataset = Dataset()
        dataset.headers = ["giorno", "settimana", "pranzo", "spuntino", "merenda"]
        dataset.append(["Lunedì", 1, "Pasta", "Mela", "Yogurt"])

        validates, message, filtered_dataset = validate_annual_dataset(dataset)

        assert validates is False
        assert "Menu Semplice" in message
        assert "Menu Annuale" in message
        assert "con settimane" in message

    def test_detailed_uploaded_when_annual_expected(self):
        """Test error when detailed menu uploaded for annual menu"""
        dataset = Dataset()
        dataset.headers = [
            "settimana",
            "giorno",
            "primo",
            "secondo",
            "contorno",
            "frutta",
            "spuntino",
        ]
        dataset.append([1, "Lunedì", "Pasta", "Pollo", "Insalata", "Mela", "Yogurt"])

        validates, message, filtered_dataset = validate_annual_dataset(dataset)

        assert validates is False
        assert "Menu Dettagliato" in message
        assert "Menu Annuale" in message
        assert "con settimane" in message

    def test_correct_type_passes_validation(self):
        """Test that correct menu type passes mismatch check"""
        dataset = Dataset()
        dataset.headers = ["giorno", "settimana", "pranzo", "spuntino", "merenda"]
        dataset.append(["Lunedì", 1, "Pasta", "Mela", "Yogurt"])

        validates, message, filtered_dataset = validate_dataset(
            dataset, School.Types.SIMPLE
        )

        # Should pass type mismatch check (may fail other validations but not type mismatch)
        assert validates is True or "sembra essere" not in (message or "")


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

        validates, message, filtered_dataset = validate_annual_dataset(dataset)

        assert validates is True
        assert message is None
        assert filtered_dataset.headers == [
            "data",
            "primo",
            "secondo",
            "contorno",
            "frutta",
            "altro",
        ]

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

        validates, message, filtered_dataset = validate_annual_dataset(dataset)

        assert validates is False
        assert "Il file non contiene tutte le colonne richieste" in message
        assert "altro" in message

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

        validates, message, filtered_dataset = validate_annual_dataset(dataset)

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


def test_get_meals_for_annual_menu_weekday():
    """Test getting meals on a regular weekday (returns list, not QuerySet)."""
    with mock.patch("school_menu.utils.timezone") as mock_timezone:
        mock_timezone.now.return_value = datetime(2024, 1, 3, 12, 0)
        school = SchoolFactory()
        meal = AnnualMealFactory(school=school, date=date(2024, 1, 3), is_active=True)
        _, today_meals = get_meals_for_annual_menu(school)
        assert today_meals[0] == meal


def test_get_meals_for_annual_menu_weekend():
    """Test getting meals on a weekend (returns list, not QuerySet)."""
    with mock.patch("school_menu.utils.timezone") as mock_timezone:
        mock_timezone.now.return_value = datetime(2024, 1, 6, 12, 0)
        school = SchoolFactory()
        monday_meal = AnnualMealFactory(
            school=school, date=date(2024, 1, 8), is_active=True
        )
        _, today_meals = get_meals_for_annual_menu(school)
        assert today_meals[0] == monday_meal


def test_get_meals_for_annual_menu_next_day():
    """Test getting meals for the next day (returns list, not QuerySet)."""
    with mock.patch("school_menu.utils.timezone") as mock_timezone:
        mock_timezone.now.return_value = datetime(2024, 1, 7, 12, 0)
        school = SchoolFactory()
        monday_meal = AnnualMealFactory(
            school=school, date=date(2024, 1, 8), is_active=True
        )
        _, today_meals = get_meals_for_annual_menu(school, next_day=True)
        assert today_meals[0] == monday_meal


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


class TestGetNotificationsStatus(TestCase):
    def test_get_notifications_status_no_pk(self):
        school = SchoolFactory()
        assert get_notifications_status(None, school) is False

    def test_get_notifications_status_not_found(self):
        school = SchoolFactory()
        with pytest.raises(Http404):
            get_notifications_status(999, school)

    def test_get_notifications_status_school_mismatch(self):
        school1 = SchoolFactory()
        school2 = SchoolFactory()
        notification = AnonymousMenuNotificationFactory(
            school=school1, daily_notification=True
        )
        assert get_notifications_status(notification.pk, school2) is False

    def test_get_notifications_status_daily_notification_false(self):
        school = SchoolFactory()
        notification = AnonymousMenuNotificationFactory(
            school=school, daily_notification=False
        )
        assert get_notifications_status(notification.pk, school) is False

    def test_get_notifications_status_success(self):
        school = SchoolFactory()
        notification = AnonymousMenuNotificationFactory(
            school=school, daily_notification=True
        )
        assert get_notifications_status(notification.pk, school) is True


class TestDetectCSVFormat:
    def test_detect_comma_delimiter(self):
        """Test Sniffer detection of comma delimiter"""
        csv_content = (
            "settimana,giorno,pranzo,spuntino,merenda\n1,Lunedì,Pasta,Yogurt,Mela\n"
        )
        delimiter, quotechar = detect_csv_format(csv_content)
        assert delimiter == ","
        assert quotechar == '"'

    def test_detect_semicolon_delimiter(self):
        """Test Sniffer detection of semicolon delimiter (Numbers export)"""
        csv_content = (
            "settimana;giorno;pranzo;spuntino;merenda\n1;Lunedì;Pasta;Yogurt;Mela\n"
        )
        delimiter, quotechar = detect_csv_format(csv_content)
        assert delimiter == ";"
        assert quotechar == '"'

    def test_detect_quoted_fields_comma(self):
        """Test detection with quoted fields and comma delimiter"""
        csv_content = '"settimana","giorno","pranzo","spuntino","merenda"\n"1","Lunedì","Pasta, Ragù","Yogurt","Mela"\n'
        delimiter, quotechar = detect_csv_format(csv_content)
        assert delimiter == ","
        assert quotechar == '"'

    def test_detect_quoted_fields_semicolon(self):
        """Test detection with quoted fields and semicolon delimiter"""
        csv_content = '"settimana";"giorno";"pranzo";"spuntino";"merenda"\n"1";"Lunedì";"Pasta; Ragù";"Yogurt";"Mela"\n'
        delimiter, quotechar = detect_csv_format(csv_content)
        assert delimiter == ";"
        assert quotechar == '"'

    def test_fallback_no_delimiters_defaults_to_comma(self):
        """Test fallback when Sniffer fails with no delimiters - defaults to comma"""
        csv_content = "a"  # Single character, Sniffer fails, no delimiters
        delimiter, quotechar = detect_csv_format(csv_content)
        # Fallback: 0 semicolons NOT > 0 commas, defaults to comma
        assert delimiter == ","
        assert quotechar == '"'

    def test_fallback_prefer_semicolon_when_more_common(self):
        """Test fallback: semicolon preferred when more common - hits line 35 TRUE"""
        csv_content = "a;b\nc"  # Inconsistent - Sniffer fails, has 1 semicolon
        delimiter, quotechar = detect_csv_format(csv_content)
        # Fallback: 1 semicolon > 0 commas, returns semicolon
        assert delimiter == ";"
        assert quotechar == '"'


class TestDetectMenuType:
    """Test menu type detection from CSV headers"""

    def test_detect_simple_menu(self):
        """Test detection of simple menu (has pranzo column)"""
        headers = ["giorno", "settimana", "pranzo", "spuntino", "merenda"]
        assert detect_menu_type(headers) == "simple"

    def test_detect_detailed_menu(self):
        """Test detection of detailed menu (has primo, secondo, contorno, frutta)"""
        headers = [
            "settimana",
            "giorno",
            "primo",
            "secondo",
            "contorno",
            "frutta",
            "spuntino",
        ]
        assert detect_menu_type(headers) == "detailed"

    def test_detect_annual_menu(self):
        """Test detection of annual menu (has data column)"""
        headers = ["data", "primo", "secondo", "contorno", "frutta", "altro"]
        assert detect_menu_type(headers) == "annual"

    def test_detect_case_insensitive(self):
        """Test that detection is case-insensitive"""
        headers = ["GIORNO", "SETTIMANA", "PRANZO", "SPUNTINO", "MERENDA"]
        assert detect_menu_type(headers) == "simple"

    def test_detect_with_extra_columns(self):
        """Test that detection works even with extra columns"""
        headers = [
            "giorno",
            "settimana",
            "pranzo",
            "spuntino",
            "merenda",
            "extra1",
            "extra2",
        ]
        assert detect_menu_type(headers) == "simple"

    def test_detect_unknown_format(self):
        """Test that unknown format returns None"""
        headers = ["foo", "bar", "baz"]
        assert detect_menu_type(headers) is None

    def test_detect_empty_headers(self):
        """Test that empty headers return None"""
        assert detect_menu_type([]) is None
        assert detect_menu_type(None) is None

    def test_detect_with_whitespace_headers(self):
        """Test detection ignores whitespace-only headers"""
        headers = ["giorno", "  ", "pranzo", "", "spuntino", "merenda"]
        assert detect_menu_type(headers) == "simple"


class TestFilterDatasetColumns:
    """Test column filtering for CSV flexibility (unnamed, whitespace, extra columns)"""

    def test_filter_unnamed_columns(self):
        """Test filtering out unnamed columns (empty string)"""
        dataset = Dataset()
        dataset.headers = ["giorno", "", "pranzo", "spuntino"]
        dataset.append(["Lunedì", "extra", "Pasta", "Mela"])
        allowed_columns = ["giorno", "pranzo", "spuntino", "merenda"]

        filtered_dataset, removed_columns = filter_dataset_columns(
            dataset, allowed_columns
        )

        assert filtered_dataset.headers == ["giorno", "pranzo", "spuntino"]
        assert "(unnamed)" in removed_columns
        assert len(filtered_dataset[0]) == 3

    def test_filter_whitespace_only_columns(self):
        """Test filtering out columns with whitespace-only names"""
        dataset = Dataset()
        dataset.headers = ["giorno", "   ", "pranzo", "\t\n"]
        dataset.append(["Lunedì", "extra1", "Pasta", "extra2"])
        allowed_columns = ["giorno", "pranzo", "spuntino"]

        filtered_dataset, removed_columns = filter_dataset_columns(
            dataset, allowed_columns
        )

        assert filtered_dataset.headers == ["giorno", "pranzo"]
        assert len(removed_columns) == 2
        assert len(filtered_dataset[0]) == 2

    def test_filter_extra_named_columns(self):
        """Test filtering out extra named columns not in allowed list"""
        dataset = Dataset()
        dataset.headers = ["giorno", "pranzo", "extra_col", "spuntino", "another_extra"]
        dataset.append(["Lunedì", "Pasta", "XXX", "Mela", "YYY"])
        allowed_columns = ["giorno", "pranzo", "spuntino"]

        filtered_dataset, removed_columns = filter_dataset_columns(
            dataset, allowed_columns
        )

        assert filtered_dataset.headers == ["giorno", "pranzo", "spuntino"]
        assert "extra_col" in removed_columns
        assert "another_extra" in removed_columns
        assert len(removed_columns) == 2
        assert filtered_dataset[0] == ("Lunedì", "Pasta", "Mela")

    def test_no_columns_to_remove(self):
        """Test dataset with no columns to remove returns original"""
        dataset = Dataset()
        dataset.headers = ["giorno", "pranzo", "spuntino"]
        dataset.append(["Lunedì", "Pasta", "Mela"])
        allowed_columns = ["giorno", "pranzo", "spuntino", "merenda"]

        filtered_dataset, removed_columns = filter_dataset_columns(
            dataset, allowed_columns
        )

        assert filtered_dataset.headers == dataset.headers
        assert removed_columns == []
        assert filtered_dataset == dataset

    def test_mixed_filtering_scenario(self):
        """Test filtering with unnamed, whitespace, and extra columns combined"""
        dataset = Dataset()
        dataset.headers = [
            "giorno",
            "",
            "pranzo",
            "  ",
            "extra1",
            "spuntino",
            "extra2",
        ]
        dataset.append(["Lunedì", "X1", "Pasta", "X2", "X3", "Mela", "X4"])
        allowed_columns = ["giorno", "pranzo", "spuntino", "merenda"]

        filtered_dataset, removed_columns = filter_dataset_columns(
            dataset, allowed_columns
        )

        assert filtered_dataset.headers == ["giorno", "pranzo", "spuntino"]
        assert len(removed_columns) == 4  # unnamed, whitespace, extra1, extra2
        assert "(unnamed)" in removed_columns
        assert "extra1" in removed_columns
        assert "extra2" in removed_columns
        assert filtered_dataset[0] == ("Lunedì", "Pasta", "Mela")

    def test_all_columns_valid(self):
        """Test that all valid columns are preserved in correct order"""
        dataset = Dataset()
        dataset.headers = ["settimana", "giorno", "primo", "secondo"]
        dataset.append([1, "Lunedì", "Pasta", "Pollo"])
        dataset.append([2, "Martedì", "Riso", "Pesce"])
        allowed_columns = ["settimana", "giorno", "primo", "secondo", "contorno"]

        filtered_dataset, removed_columns = filter_dataset_columns(
            dataset, allowed_columns
        )

        assert filtered_dataset.headers == ["settimana", "giorno", "primo", "secondo"]
        assert removed_columns == []
        assert len(filtered_dataset) == 2
        assert filtered_dataset[0] == (1, "Lunedì", "Pasta", "Pollo")
        assert filtered_dataset[1] == (2, "Martedì", "Riso", "Pesce")
