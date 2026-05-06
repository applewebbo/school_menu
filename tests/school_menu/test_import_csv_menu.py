import io
from unittest.mock import patch

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from school_menu.models import DetailedMeal, School, SimpleMeal
from tests.school_menu.factories import (
    DetailedMealFactory,
    SchoolFactory,
    SimpleMealFactory,
)

pytestmark = pytest.mark.django_db

SIMPLE_CSV = """settimana,giorno,pranzo,spuntino,merenda
1,Lunedì,Pasta al pomodoro,,
1,Martedì,Risotto ai funghi,,
1,Mercoledì,Pasta e fagioli,,
1,Giovedì,Minestra di orzo,,
1,Venerdì,Pasta integrale,,
2,Lunedì,Pasta al pesto,,
2,Martedì,Farro con verdure,,
2,Mercoledì,Pasta e legumi,,
2,Giovedì,Risotto zafferano,,
2,Venerdì,Vellutata patate,,
3,Lunedì,Lasagna,,
3,Martedì,Orzo al pesto,,
3,Mercoledì,Pasta peperoni,,
3,Giovedì,Insalata di riso,,
3,Venerdì,Pasta ragù pesce,,
4,Lunedì,Pasta al pesto,,
4,Martedì,Farro con legumi,,
4,Mercoledì,Pasta pomodoro basilico,,
4,Giovedì,Risotto zafferano,,
4,Venerdì,Pasta ragù carne,,
"""

DETAILED_CSV = """settimana,giorno,primo,secondo,contorno,frutta,spuntino
1,Lunedì,Pasta al pomodoro,Pollo,Insalata,Mela,Crackers
1,Martedì,Risotto,Pesce,Carote,Pera,Crackers
1,Mercoledì,Pasta e fagioli,Uova,Spinaci,Banana,Crackers
1,Giovedì,Minestra,Tacchino,Zucchine,Kiwi,Crackers
1,Venerdì,Pasta integrale,Formaggio,Fagiolini,Arancia,Crackers
2,Lunedì,Pasta al pesto,Pollo,Insalata,Mela,Crackers
2,Martedì,Farro,Pesce,Carote,Pera,Crackers
2,Mercoledì,Pasta legumi,Uova,Spinaci,Banana,Crackers
2,Giovedì,Risotto,Tacchino,Zucchine,Kiwi,Crackers
2,Venerdì,Vellutata,Formaggio,Fagiolini,Arancia,Crackers
3,Lunedì,Lasagna,Pollo,Insalata,Mela,Crackers
3,Martedì,Orzo,Pesce,Carote,Pera,Crackers
3,Mercoledì,Pasta peperoni,Uova,Spinaci,Banana,Crackers
3,Giovedì,Insalata riso,Tacchino,Zucchine,Kiwi,Crackers
3,Venerdì,Pasta ragù,Formaggio,Fagiolini,Arancia,Crackers
4,Lunedì,Pasta pesto,Pollo,Insalata,Mela,Crackers
4,Martedì,Farro legumi,Pesce,Carote,Pera,Crackers
4,Mercoledì,Pasta basilico,Uova,Spinaci,Banana,Crackers
4,Giovedì,Risotto,Tacchino,Zucchine,Kiwi,Crackers
4,Venerdì,Pasta ragù carne,Formaggio,Fagiolini,Arancia,Crackers
"""


def _run(inputs, tmp_path, csv_content, csv_filename="menu.csv"):
    """Write CSV to tmp file, patch input(), run command, return stdout."""
    csv_file = tmp_path / csv_filename
    csv_file.write_text(csv_content, encoding="utf-8")
    resolved = [str(csv_file) if i == "__CSV__" else i for i in inputs]
    it = iter(resolved)
    output = io.StringIO()
    with patch("builtins.input", side_effect=lambda _: next(it)):
        try:
            call_command("import_csv_menu", stdout=output)
        except CommandError, StopIteration:
            pass
    return output.getvalue()


class TestImportCsvMenuSimple:
    def test_imports_simple_menu(self, tmp_path):
        school = SchoolFactory(
            menu_type=School.Types.SIMPLE,
            no_gluten=False,
            no_lactose=False,
            vegetarian=False,
            special=False,
        )
        # school=1, stagione=estivo(1), tipo=standard(1), csv, conferma=s
        _run(["1", "1", "1", "__CSV__", "s"], tmp_path, SIMPLE_CSV)
        assert (
            SimpleMeal.objects.filter(
                school=school, season=SimpleMeal.Seasons.ESTIVO
            ).count()
            == 20
        )

    def test_imports_simple_menu_invernale(self, tmp_path):
        school = SchoolFactory(
            menu_type=School.Types.SIMPLE,
            no_gluten=False,
            no_lactose=False,
            vegetarian=False,
            special=False,
        )
        _run(["1", "2", "1", "__CSV__", "s"], tmp_path, SIMPLE_CSV)
        assert (
            SimpleMeal.objects.filter(
                school=school, season=SimpleMeal.Seasons.INVERNALE
            ).count()
            == 20
        )

    def test_overwrites_existing_simple_menu(self, tmp_path):
        school = SchoolFactory(
            menu_type=School.Types.SIMPLE,
            no_gluten=False,
            no_lactose=False,
            vegetarian=False,
            special=False,
        )
        SimpleMealFactory.create_batch(
            5,
            school=school,
            season=SimpleMeal.Seasons.ESTIVO,
            type=SimpleMeal.Types.STANDARD,
        )
        # sovrascrittura=s, poi conferma=s
        _run(["1", "1", "1", "__CSV__", "s", "s"], tmp_path, SIMPLE_CSV)
        assert (
            SimpleMeal.objects.filter(
                school=school, season=SimpleMeal.Seasons.ESTIVO
            ).count()
            == 20
        )

    def test_aborts_if_overwrite_refused(self, tmp_path):
        school = SchoolFactory(
            menu_type=School.Types.SIMPLE,
            no_gluten=False,
            no_lactose=False,
            vegetarian=False,
            special=False,
        )
        SimpleMealFactory.create_batch(
            5,
            school=school,
            season=SimpleMeal.Seasons.ESTIVO,
            type=SimpleMeal.Types.STANDARD,
        )
        _run(["1", "1", "1", "__CSV__", "n"], tmp_path, SIMPLE_CSV)
        assert (
            SimpleMeal.objects.filter(
                school=school, season=SimpleMeal.Seasons.ESTIVO
            ).count()
            == 5
        )

    def test_aborts_on_final_confirm_no(self, tmp_path):
        school = SchoolFactory(
            menu_type=School.Types.SIMPLE,
            no_gluten=False,
            no_lactose=False,
            vegetarian=False,
            special=False,
        )
        _run(["1", "1", "1", "__CSV__", "n"], tmp_path, SIMPLE_CSV)
        assert SimpleMeal.objects.filter(school=school).count() == 0

    def test_no_schools_raises_error(self):
        with pytest.raises(CommandError, match="Nessuna scuola"):
            call_command("import_csv_menu")

    def test_invalid_csv_path_reprompts(self, tmp_path):
        school = SchoolFactory(
            menu_type=School.Types.SIMPLE,
            no_gluten=False,
            no_lactose=False,
            vegetarian=False,
            special=False,
        )
        csv_file = tmp_path / "menu.csv"
        csv_file.write_text(SIMPLE_CSV, encoding="utf-8")
        inputs_resolved = [
            "1",
            "1",
            "1",
            "/percorso/inesistente.csv",
            str(csv_file),
            "s",
        ]
        it = iter(inputs_resolved)
        output = io.StringIO()
        with patch("builtins.input", side_effect=lambda _: next(it)):
            call_command("import_csv_menu", stdout=output)
        assert SimpleMeal.objects.filter(school=school).count() == 20

    def test_wrong_csv_format_raises_no_import(self, tmp_path):
        school = SchoolFactory(
            menu_type=School.Types.SIMPLE,
            no_gluten=False,
            no_lactose=False,
            vegetarian=False,
            special=False,
        )
        # Pass detailed CSV to a simple-menu school → validation fails
        _run(["1", "1", "1", "__CSV__", "s"], tmp_path, DETAILED_CSV)
        assert SimpleMeal.objects.filter(school=school).count() == 0


class TestImportCsvMenuDetailed:
    def test_imports_detailed_menu(self, tmp_path):
        school = SchoolFactory(
            menu_type=School.Types.DETAILED,
            no_gluten=False,
            no_lactose=False,
            vegetarian=False,
            special=False,
        )
        _run(["1", "1", "1", "__CSV__", "s"], tmp_path, DETAILED_CSV)
        assert (
            DetailedMeal.objects.filter(
                school=school, season=DetailedMeal.Seasons.ESTIVO
            ).count()
            == 20
        )

    def test_overwrites_existing_detailed_menu(self, tmp_path):
        school = SchoolFactory(
            menu_type=School.Types.DETAILED,
            no_gluten=False,
            no_lactose=False,
            vegetarian=False,
            special=False,
        )
        DetailedMealFactory.create_batch(
            3,
            school=school,
            season=DetailedMeal.Seasons.ESTIVO,
            type=DetailedMeal.Types.STANDARD,
        )
        _run(["1", "1", "1", "__CSV__", "s", "s"], tmp_path, DETAILED_CSV)
        assert (
            DetailedMeal.objects.filter(
                school=school, season=DetailedMeal.Seasons.ESTIVO
            ).count()
            == 20
        )

    def test_multiple_schools_selects_correct_one(self, tmp_path):
        SchoolFactory(
            menu_type=School.Types.SIMPLE,
            no_gluten=False,
            no_lactose=False,
            vegetarian=False,
            special=False,
        )
        SchoolFactory(
            menu_type=School.Types.SIMPLE,
            no_gluten=False,
            no_lactose=False,
            vegetarian=False,
            special=False,
        )
        # Le scuole sono ordinate per nome; selezioniamo la seconda
        schools_ordered = list(School.objects.order_by("name"))
        target = schools_ordered[1]
        other = schools_ordered[0]
        _run(["2", "1", "1", "__CSV__", "s"], tmp_path, SIMPLE_CSV)
        assert SimpleMeal.objects.filter(school=other).count() == 0
        assert SimpleMeal.objects.filter(school=target).count() == 20
