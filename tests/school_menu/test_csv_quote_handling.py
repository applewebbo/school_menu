"""
Tests for CSV quote handling in upload functionality.
These tests verify that various quoting scenarios work correctly.
"""

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from test_plus import TestCase as TestPlusTestCase

from school_menu.models import DetailedMeal, Meal, School, SimpleMeal
from tests.school_menu.factories import SchoolFactory

pytestmark = pytest.mark.django_db


class TestCSVQuoteHandling(TestPlusTestCase):
    """Test various CSV quoting scenarios"""

    def test_upload_csv_with_double_quoted_fields(self):
        """Test CSV with standard double-quoted fields"""
        user = self.make_user()
        school = SchoolFactory(user=user, menu_type=School.Types.SIMPLE)

        csv_content = """"giorno","settimana","pranzo","spuntino","merenda"
"Lunedì","1","Pasta al pomodoro","Yogurt","Mela"
"Martedì","1","Riso con verdure","Crackers","Banana"
"""

        with self.login(user):
            url = reverse(
                "school_menu:upload_menu",
                kwargs={"school_id": school.id, "meal_type": Meal.Types.STANDARD},
            )
            data = {
                "file": SimpleUploadedFile(
                    "menu.csv", csv_content.encode("utf-8"), content_type="text/csv"
                ),
                "season": School.Seasons.INVERNALE,
            }
            response = self.post(url, data=data)

        assert response.status_code == 204
        assert SimpleMeal.objects.filter(school=school).count() == 2

    def test_upload_csv_with_quoted_fields_containing_commas(self):
        """Test CSV with quoted fields that contain commas"""
        user = self.make_user()
        school = SchoolFactory(user=user, menu_type=School.Types.SIMPLE)

        csv_content = """"giorno","settimana","pranzo","spuntino","merenda"
"Lunedì","1","Pasta al pomodoro, con basilico","Yogurt, alla frutta","Mela"
"Martedì","1","Riso con zucchine, carote e piselli","Crackers","Banana"
"""

        with self.login(user):
            url = reverse(
                "school_menu:upload_menu",
                kwargs={"school_id": school.id, "meal_type": Meal.Types.STANDARD},
            )
            data = {
                "file": SimpleUploadedFile(
                    "menu.csv", csv_content.encode("utf-8"), content_type="text/csv"
                ),
                "season": School.Seasons.INVERNALE,
            }
            response = self.post(url, data=data)

        assert response.status_code == 204
        meals = SimpleMeal.objects.filter(school=school).order_by("day")
        assert meals.count() == 2
        assert "basilico" in meals[0].menu
        assert "zucchine, carote" in meals[1].menu

    def test_upload_csv_with_escaped_quotes(self):
        """Test CSV with escaped quotes (double quotes within quoted fields)"""
        user = self.make_user()
        school = SchoolFactory(user=user, menu_type=School.Types.SIMPLE)

        # In CSV, quotes are escaped by doubling them: "" becomes "
        csv_content = """"giorno","settimana","pranzo","spuntino","merenda"
"Lunedì","1","Pasta ""al dente"" con sugo","Yogurt","Mela"
"Martedì","1","Riso con verdure","Crackers","Banana"
"""

        with self.login(user):
            url = reverse(
                "school_menu:upload_menu",
                kwargs={"school_id": school.id, "meal_type": Meal.Types.STANDARD},
            )
            data = {
                "file": SimpleUploadedFile(
                    "menu.csv", csv_content.encode("utf-8"), content_type="text/csv"
                ),
                "season": School.Seasons.INVERNALE,
            }
            response = self.post(url, data=data)

        assert response.status_code == 204
        meals = SimpleMeal.objects.filter(school=school).order_by("day")
        assert meals.count() == 2
        # The escaped quotes should be unescaped in the data
        assert '"al dente"' in meals[0].menu

    def test_upload_csv_with_newlines_in_quoted_fields(self):
        """Test CSV with multi-line values in quoted fields"""
        user = self.make_user()
        school = SchoolFactory(user=user, menu_type=School.Types.SIMPLE)

        # Newlines within quoted fields should be preserved
        csv_content = """"giorno","settimana","pranzo","spuntino","merenda"
"Lunedì","1","Pasta al pomodoro
con basilico fresco","Yogurt","Mela"
"Martedì","1","Riso con verdure","Crackers","Banana"
"""

        with self.login(user):
            url = reverse(
                "school_menu:upload_menu",
                kwargs={"school_id": school.id, "meal_type": Meal.Types.STANDARD},
            )
            data = {
                "file": SimpleUploadedFile(
                    "menu.csv", csv_content.encode("utf-8"), content_type="text/csv"
                ),
                "season": School.Seasons.INVERNALE,
            }
            response = self.post(url, data=data)

        assert response.status_code == 204
        meals = SimpleMeal.objects.filter(school=school).order_by("day")
        assert meals.count() == 2
        # Newline should be preserved in the data
        assert "\n" in meals[0].menu or "basilico" in meals[0].menu

    def test_upload_csv_with_mixed_quoted_unquoted_fields(self):
        """Test CSV with mix of quoted and unquoted fields"""
        user = self.make_user()
        school = SchoolFactory(user=user, menu_type=School.Types.SIMPLE)

        # Mix of quoted and unquoted fields (valid CSV)
        csv_content = """giorno,settimana,"pranzo","spuntino",merenda
Lunedì,1,"Pasta al pomodoro","Yogurt",Mela
"Martedì","1",Riso con verdure,Crackers,"Banana"
"""

        with self.login(user):
            url = reverse(
                "school_menu:upload_menu",
                kwargs={"school_id": school.id, "meal_type": Meal.Types.STANDARD},
            )
            data = {
                "file": SimpleUploadedFile(
                    "menu.csv", csv_content.encode("utf-8"), content_type="text/csv"
                ),
                "season": School.Seasons.INVERNALE,
            }
            response = self.post(url, data=data)

        assert response.status_code == 204
        assert SimpleMeal.objects.filter(school=school).count() == 2

    def test_upload_csv_with_semicolon_and_quotes(self):
        """Test CSV with semicolon delimiter and quoted fields"""
        user = self.make_user()
        school = SchoolFactory(user=user, menu_type=School.Types.SIMPLE)

        # Semicolon delimiter with quoted fields containing commas
        csv_content = """"giorno";"settimana";"pranzo";"spuntino";"merenda"
"Lunedì";"1";"Pasta al pomodoro, con basilico";"Yogurt";"Mela"
"Martedì";"1";"Riso con verdure";"Crackers";"Banana"
"""

        with self.login(user):
            url = reverse(
                "school_menu:upload_menu",
                kwargs={"school_id": school.id, "meal_type": Meal.Types.STANDARD},
            )
            data = {
                "file": SimpleUploadedFile(
                    "menu.csv", csv_content.encode("utf-8"), content_type="text/csv"
                ),
                "season": School.Seasons.INVERNALE,
            }
            response = self.post(url, data=data)

        assert response.status_code == 204
        meals = SimpleMeal.objects.filter(school=school).order_by("day")
        assert meals.count() == 2
        # Comma within the quoted field should be preserved
        assert "," in meals[0].menu

    def test_upload_detailed_menu_with_quotes(self):
        """Test detailed menu CSV with quoted fields"""
        user = self.make_user()
        school = SchoolFactory(user=user, menu_type=School.Types.DETAILED)

        csv_content = """"giorno","settimana","primo","secondo","contorno","frutta","spuntino"
"Lunedì","1","Pasta al pomodoro","Pollo arrosto","Insalata verde","Mela","Yogurt"
"Martedì","1","Risotto, ai funghi","Pesce al forno","Carote, julienne","Banana","Crackers"
"""

        with self.login(user):
            url = reverse(
                "school_menu:upload_menu",
                kwargs={"school_id": school.id, "meal_type": Meal.Types.STANDARD},
            )
            data = {
                "file": SimpleUploadedFile(
                    "menu.csv", csv_content.encode("utf-8"), content_type="text/csv"
                ),
                "season": School.Seasons.INVERNALE,
            }
            response = self.post(url, data=data)

        assert response.status_code == 204
        meals = DetailedMeal.objects.filter(school=school).order_by("day")
        assert meals.count() == 2
        assert "funghi" in meals[1].first_course
        assert "," in meals[1].side_dish

    def test_upload_csv_empty_quoted_fields(self):
        """Test CSV with empty quoted fields"""
        user = self.make_user()
        school = SchoolFactory(user=user, menu_type=School.Types.SIMPLE)

        csv_content = """"giorno","settimana","pranzo","spuntino","merenda"
"Lunedì","1","Pasta al pomodoro","","Mela"
"Martedì","1","Riso con verdure","Crackers",""
"""

        with self.login(user):
            url = reverse(
                "school_menu:upload_menu",
                kwargs={"school_id": school.id, "meal_type": Meal.Types.STANDARD},
            )
            data = {
                "file": SimpleUploadedFile(
                    "menu.csv", csv_content.encode("utf-8"), content_type="text/csv"
                ),
                "season": School.Seasons.INVERNALE,
            }
            response = self.post(url, data=data)

        assert response.status_code == 204
        meals = SimpleMeal.objects.filter(school=school).order_by("day")
        assert meals.count() == 2
        assert meals[0].morning_snack == ""
        assert meals[1].afternoon_snack == ""


class TestCSVErrorHandling(TestPlusTestCase):
    """Test CSV error handling for various exception types"""

    def test_upload_csv_with_invalid_dimensions(self):
        """Test that InvalidDimensions exception is handled gracefully"""
        user = self.make_user()
        school = SchoolFactory(user=user, menu_type=School.Types.SIMPLE)

        from unittest import mock

        from tablib.exceptions import InvalidDimensions

        with self.login(user):
            url = reverse(
                "school_menu:upload_menu",
                kwargs={"school_id": school.id, "meal_type": Meal.Types.STANDARD},
            )
            csv_content = b"""giorno,settimana,pranzo,spuntino,merenda
Lunedi,1,Pasta,Yogurt,Mela
"""
            data = {
                "file": SimpleUploadedFile(
                    "menu.csv", csv_content, content_type="text/csv"
                ),
                "season": School.Seasons.INVERNALE,
            }

            # Mock to raise InvalidDimensions
            with mock.patch("school_menu.views.Dataset.load") as mock_load:
                mock_load.side_effect = InvalidDimensions("CSV structure is invalid")
                response = self.post(url, data=data)

        assert response.status_code == 204
        from django.contrib.messages import get_messages

        messages = list(get_messages(response.wsgi_request))
        assert len(messages) > 0
        assert "Impossibile riconoscere il formato" in messages[0].message

    def test_upload_csv_with_value_error(self):
        """Test that ValueError during CSV parsing is handled gracefully"""
        user = self.make_user()
        school = SchoolFactory(user=user, menu_type=School.Types.SIMPLE)

        # Create a CSV that will trigger a ValueError during parsing
        # Using a mock to force a ValueError with "quote" in the message
        from unittest import mock

        with self.login(user):
            url = reverse(
                "school_menu:upload_menu",
                kwargs={"school_id": school.id, "meal_type": Meal.Types.STANDARD},
            )
            csv_content = b"""giorno,settimana,pranzo,spuntino,merenda
Lunedi,1,Pasta,Yogurt,Mela
"""
            data = {
                "file": SimpleUploadedFile(
                    "menu.csv", csv_content, content_type="text/csv"
                ),
                "season": School.Seasons.INVERNALE,
            }

            # Mock the dataset.load to raise ValueError with "quote" in message
            with mock.patch("school_menu.views.Dataset.load") as mock_load:
                mock_load.side_effect = ValueError("Invalid quote character in CSV")
                response = self.post(url, data=data)

        assert response.status_code == 204
        from django.contrib.messages import get_messages

        messages = list(get_messages(response.wsgi_request))
        assert len(messages) > 0
        assert (
            "virgolette" in messages[0].message
            or "quote" in messages[0].message.lower()
        )

    def test_upload_csv_with_generic_value_error(self):
        """Test that generic ValueError is handled gracefully"""
        user = self.make_user()
        school = SchoolFactory(user=user, menu_type=School.Types.SIMPLE)

        from unittest import mock

        with self.login(user):
            url = reverse(
                "school_menu:upload_menu",
                kwargs={"school_id": school.id, "meal_type": Meal.Types.STANDARD},
            )
            csv_content = b"""giorno,settimana,pranzo,spuntino,merenda
Lunedi,1,Pasta,Yogurt,Mela
"""
            data = {
                "file": SimpleUploadedFile(
                    "menu.csv", csv_content, content_type="text/csv"
                ),
                "season": School.Seasons.INVERNALE,
            }

            # Mock to raise ValueError without "quote" or "delimiter"
            with mock.patch("school_menu.views.Dataset.load") as mock_load:
                mock_load.side_effect = ValueError("Some other parsing error")
                response = self.post(url, data=data)

        assert response.status_code == 204
        from django.contrib.messages import get_messages

        messages = list(get_messages(response.wsgi_request))
        assert len(messages) > 0
        assert "Il file CSV non è valido" in messages[0].message

    def test_upload_csv_with_generic_exception(self):
        """Test that generic exceptions are handled gracefully"""
        user = self.make_user()
        school = SchoolFactory(user=user, menu_type=School.Types.SIMPLE)

        from unittest import mock

        with self.login(user):
            url = reverse(
                "school_menu:upload_menu",
                kwargs={"school_id": school.id, "meal_type": Meal.Types.STANDARD},
            )
            csv_content = b"""giorno,settimana,pranzo,spuntino,merenda
Lunedi,1,Pasta,Yogurt,Mela
"""
            data = {
                "file": SimpleUploadedFile(
                    "menu.csv", csv_content, content_type="text/csv"
                ),
                "season": School.Seasons.INVERNALE,
            }

            # Mock to raise a generic exception
            with mock.patch("school_menu.views.Dataset.load") as mock_load:
                mock_load.side_effect = RuntimeError("Unexpected error")
                response = self.post(url, data=data)

        assert response.status_code == 204
        from django.contrib.messages import get_messages

        messages = list(get_messages(response.wsgi_request))
        assert len(messages) > 0
        assert "Errore durante la lettura" in messages[0].message

    def test_upload_annual_csv_with_invalid_dimensions(self):
        """Test InvalidDimensions handling for annual menu upload"""
        user = self.make_user()
        school = SchoolFactory(user=user, annual_menu=True)

        from unittest import mock

        from tablib.exceptions import InvalidDimensions

        with self.login(user):
            url = reverse(
                "school_menu:upload_annual_menu",
                kwargs={"school_id": school.id, "meal_type": Meal.Types.STANDARD},
            )
            csv_content = b"""data,primo,secondo,contorno,frutta,altro
15/01/2025,Pasta,Pollo,Insalata,Mela,Pane
"""
            data = {
                "file": SimpleUploadedFile(
                    "annual_menu.csv", csv_content, content_type="text/csv"
                ),
            }

            # Mock to raise InvalidDimensions
            with mock.patch("school_menu.views.Dataset.load") as mock_load:
                mock_load.side_effect = InvalidDimensions("CSV structure is invalid")
                response = self.post(url, data=data)

        assert response.status_code == 204
        from django.contrib.messages import get_messages

        messages = list(get_messages(response.wsgi_request))
        assert len(messages) > 0
        assert "Impossibile riconoscere il formato" in messages[0].message

    def test_upload_annual_csv_with_value_error(self):
        """Test ValueError handling for annual menu upload"""
        user = self.make_user()
        school = SchoolFactory(user=user, annual_menu=True)

        from unittest import mock

        with self.login(user):
            url = reverse(
                "school_menu:upload_annual_menu",
                kwargs={"school_id": school.id, "meal_type": Meal.Types.STANDARD},
            )
            csv_content = b"""data,primo,secondo,contorno,frutta,altro
15/01/2025,Pasta,Pollo,Insalata,Mela,Pane
"""
            data = {
                "file": SimpleUploadedFile(
                    "annual_menu.csv", csv_content, content_type="text/csv"
                ),
            }

            # Mock to raise ValueError with "delimiter"
            with mock.patch("school_menu.views.Dataset.load") as mock_load:
                mock_load.side_effect = ValueError("Invalid delimiter in CSV")
                response = self.post(url, data=data)

        assert response.status_code == 204
        from django.contrib.messages import get_messages

        messages = list(get_messages(response.wsgi_request))
        assert len(messages) > 0
        assert (
            "virgolette" in messages[0].message or "delimitatori" in messages[0].message
        )

    def test_upload_annual_csv_with_generic_value_error(self):
        """Test generic ValueError handling for annual menu upload"""
        user = self.make_user()
        school = SchoolFactory(user=user, annual_menu=True)

        from unittest import mock

        with self.login(user):
            url = reverse(
                "school_menu:upload_annual_menu",
                kwargs={"school_id": school.id, "meal_type": Meal.Types.STANDARD},
            )
            csv_content = b"""data,primo,secondo,contorno,frutta,altro
15/01/2025,Pasta,Pollo,Insalata,Mela,Pane
"""
            data = {
                "file": SimpleUploadedFile(
                    "annual_menu.csv", csv_content, content_type="text/csv"
                ),
            }

            # Mock to raise ValueError without "quote" or "delimiter"
            with mock.patch("school_menu.views.Dataset.load") as mock_load:
                mock_load.side_effect = ValueError("Some other parsing error")
                response = self.post(url, data=data)

        assert response.status_code == 204
        from django.contrib.messages import get_messages

        messages = list(get_messages(response.wsgi_request))
        assert len(messages) > 0
        assert "Il file CSV non è valido" in messages[0].message

    def test_upload_annual_csv_with_generic_exception(self):
        """Test generic exception handling for annual menu upload"""
        user = self.make_user()
        school = SchoolFactory(user=user, annual_menu=True)

        from unittest import mock

        with self.login(user):
            url = reverse(
                "school_menu:upload_annual_menu",
                kwargs={"school_id": school.id, "meal_type": Meal.Types.STANDARD},
            )
            csv_content = b"""data,primo,secondo,contorno,frutta,altro
15/01/2025,Pasta,Pollo,Insalata,Mela,Pane
"""
            data = {
                "file": SimpleUploadedFile(
                    "annual_menu.csv", csv_content, content_type="text/csv"
                ),
            }

            # Mock to raise a generic exception
            with mock.patch("school_menu.views.Dataset.load") as mock_load:
                mock_load.side_effect = RuntimeError("Unexpected error")
                response = self.post(url, data=data)

        assert response.status_code == 204
        from django.contrib.messages import get_messages

        messages = list(get_messages(response.wsgi_request))
        assert len(messages) > 0
        assert "Errore durante la lettura" in messages[0].message


class TestCSVAnnualMenuQuoteHandling(TestPlusTestCase):
    """Test annual menu CSV quote handling"""

    def test_upload_annual_menu_with_quotes(self):
        """Test annual menu CSV with quoted fields containing special characters"""
        user = self.make_user()
        school = SchoolFactory(user=user, annual_menu=True)

        csv_content = """"data","primo","secondo","contorno","frutta","altro"
"15/01/2025","Pasta al pomodoro, fresco","Pollo arrosto","Insalata verde","Mela, rossa","Pane"
"16/01/2025","Risotto ai funghi","Pesce al forno","Carote","Banana","Crackers"
"""

        with self.login(user):
            url = reverse(
                "school_menu:upload_annual_menu",
                kwargs={"school_id": school.id, "meal_type": Meal.Types.STANDARD},
            )
            data = {
                "file": SimpleUploadedFile(
                    "annual_menu.csv",
                    csv_content.encode("utf-8"),
                    content_type="text/csv",
                ),
            }
            response = self.post(url, data=data)

        assert response.status_code == 204
        from school_menu.models import AnnualMeal

        meals = AnnualMeal.objects.filter(school=school).order_by("date")
        assert meals.count() == 2
        # Commas within quoted fields should be preserved
        assert "," in meals[0].menu
