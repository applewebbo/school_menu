"""Tests for the deterministic clean-up applied to whatever the AI returns (#234)."""

import pytest

from school_menu.ai.errors import EmptyResult
from school_menu.ai.normalise import MENU_MAX_LENGTH, normalise_rows
from school_menu.models import MenuImportDraft

SIMPLE = MenuImportDraft.Kinds.SIMPLE
DETAILED = MenuImportDraft.Kinds.DETAILED
ANNUAL = MenuImportDraft.Kinds.ANNUAL


def simple_row(**overrides):
    row = {
        "giorno": "Lunedì",
        "settimana": 1,
        "pranzo": "Pasta",
        "spuntino": "Mela",
        "merenda": "Yogurt",
    }
    row.update(overrides)
    return row


class TestWeekdayNormalisation:
    @pytest.mark.parametrize(
        "value,expected",
        [
            ("lunedi", "Lunedì"),
            ("LUNEDÌ", "Lunedì"),
            ("  martedi  ", "Martedì"),
            ("mercoledi'", "Mercoledì"),
            ("Giovedi", "Giovedì"),
            ("VENERDI", "Venerdì"),
        ],
    )
    def test_accents_and_case_are_fixed(self, value, expected):
        rows, warnings = normalise_rows(SIMPLE, [simple_row(giorno=value)])

        assert rows[0]["giorno"] == expected
        assert warnings == []

    def test_weekend_rows_are_dropped_with_a_warning(self):
        rows, warnings = normalise_rows(
            SIMPLE, [simple_row(), simple_row(giorno="Sabato")]
        )

        assert len(rows) == 1
        assert any("Sabato" in w for w in warnings)

    def test_unrecognised_day_is_dropped(self):
        rows, warnings = normalise_rows(
            SIMPLE, [simple_row(), simple_row(giorno="qualsiasi")]
        )

        assert len(rows) == 1
        assert warnings


class TestWeekNormalisation:
    def test_numeric_string_is_coerced(self):
        rows, _ = normalise_rows(SIMPLE, [simple_row(settimana="3")])

        assert rows[0]["settimana"] == 3

    @pytest.mark.parametrize("value", [0, 5, 99, -1])
    def test_out_of_range_week_is_dropped(self, value):
        rows, warnings = normalise_rows(
            SIMPLE, [simple_row(), simple_row(giorno="Martedì", settimana=value)]
        )

        assert len(rows) == 1
        assert warnings

    def test_non_numeric_week_is_dropped(self):
        rows, warnings = normalise_rows(
            SIMPLE, [simple_row(), simple_row(giorno="Martedì", settimana="prima")]
        )

        assert len(rows) == 1
        assert warnings


class TestDeduplication:
    def test_same_day_and_week_keeps_the_first(self):
        rows, warnings = normalise_rows(
            SIMPLE,
            [simple_row(pranzo="Pasta"), simple_row(pranzo="Riso")],
        )

        assert len(rows) == 1
        assert rows[0]["pranzo"] == "Pasta"
        assert warnings

    def test_same_day_on_a_different_week_is_kept(self):
        rows, _ = normalise_rows(
            SIMPLE, [simple_row(settimana=1), simple_row(settimana=2)]
        )

        assert len(rows) == 2


class TestOrdering:
    def test_rows_are_sorted_by_week_then_day(self):
        rows, _ = normalise_rows(
            SIMPLE,
            [
                simple_row(giorno="Mercoledì", settimana=2),
                simple_row(giorno="Martedì", settimana=1),
                simple_row(giorno="Lunedì", settimana=2),
            ],
        )

        assert [(r["settimana"], r["giorno"]) for r in rows] == [
            (1, "Martedì"),
            (2, "Lunedì"),
            (2, "Mercoledì"),
        ]


class TestTruncation:
    def test_over_long_value_is_truncated_with_a_warning(self):
        rows, warnings = normalise_rows(
            SIMPLE, [simple_row(pranzo="a" * (MENU_MAX_LENGTH + 50))]
        )

        assert len(rows[0]["pranzo"]) == MENU_MAX_LENGTH
        assert any("pranzo" in w for w in warnings)

    def test_value_within_the_limit_is_untouched(self):
        rows, warnings = normalise_rows(
            SIMPLE, [simple_row(pranzo="a" * MENU_MAX_LENGTH)]
        )

        assert len(rows[0]["pranzo"]) == MENU_MAX_LENGTH
        assert warnings == []


class TestMissingFields:
    def test_absent_optional_columns_become_empty_strings(self):
        rows, _ = normalise_rows(SIMPLE, [{"giorno": "Lunedì", "settimana": 1}])

        assert rows[0]["pranzo"] == ""
        assert rows[0]["merenda"] == ""

    def test_none_is_treated_as_empty(self):
        rows, _ = normalise_rows(SIMPLE, [simple_row(spuntino=None)])

        assert rows[0]["spuntino"] == ""

    def test_whitespace_is_stripped(self):
        rows, _ = normalise_rows(SIMPLE, [simple_row(pranzo="  Pasta  ")])

        assert rows[0]["pranzo"] == "Pasta"


class TestDetailedKind:
    def test_detailed_columns_are_kept(self):
        rows, _ = normalise_rows(
            DETAILED,
            [
                {
                    "giorno": "lunedi",
                    "settimana": "1",
                    "primo": "Pasta",
                    "secondo": "Pollo",
                    "contorno": "Insalata",
                    "frutta": "Mela",
                    "spuntino": "Yogurt",
                }
            ],
        )

        assert rows[0] == {
            "giorno": "Lunedì",
            "settimana": 1,
            "primo": "Pasta",
            "secondo": "Pollo",
            "contorno": "Insalata",
            "frutta": "Mela",
            "spuntino": "Yogurt",
        }


class TestAnnualKind:
    def test_valid_date_is_kept(self):
        rows, warnings = normalise_rows(
            ANNUAL, [{"data": "01/09/2026", "primo": "Pasta"}]
        )

        assert rows[0]["data"] == "01/09/2026"
        assert warnings == []

    @pytest.mark.parametrize("value", ["2026-09-01", "1/9/26", "banana", "32/13/2026"])
    def test_unparseable_date_is_dropped(self, value):
        rows, warnings = normalise_rows(
            ANNUAL,
            [
                {"data": "01/09/2026", "primo": "Pasta"},
                {"data": value, "primo": "Riso"},
            ],
        )

        assert len(rows) == 1
        assert warnings

    def test_iso_like_date_is_not_silently_reinterpreted(self):
        """01/09 must never be read as September 1st in one row and January 9th in another."""
        rows, _ = normalise_rows(
            ANNUAL,
            [
                {"data": "01/09/2026", "primo": "A"},
                {"data": "09/01/2026", "primo": "B"},
            ],
        )

        assert [r["data"] for r in rows] == ["09/01/2026", "01/09/2026"]

    def test_rows_are_sorted_by_date(self):
        rows, _ = normalise_rows(
            ANNUAL,
            [
                {"data": "03/09/2026", "primo": "C"},
                {"data": "01/09/2026", "primo": "A"},
                {"data": "02/09/2026", "primo": "B"},
            ],
        )

        assert [r["primo"] for r in rows] == ["A", "B", "C"]

    def test_duplicate_dates_keep_the_first(self):
        rows, warnings = normalise_rows(
            ANNUAL,
            [
                {"data": "01/09/2026", "primo": "A"},
                {"data": "01/09/2026", "primo": "B"},
            ],
        )

        assert len(rows) == 1
        assert rows[0]["primo"] == "A"
        assert warnings

    def test_joined_menu_over_the_limit_is_truncated(self):
        """The annual columns end up in a single 600 char field, so the sum is capped."""
        long_value = "a" * 400
        rows, warnings = normalise_rows(
            ANNUAL,
            [
                {
                    "data": "01/09/2026",
                    "primo": long_value,
                    "secondo": long_value,
                    "contorno": "",
                    "frutta": "",
                    "altro": "",
                }
            ],
        )

        # AnnualMenuResource drops the empty values before joining, so mirror that here
        joined = "\n".join(
            rows[0][c]
            for c in ("primo", "secondo", "contorno", "frutta", "altro")
            if rows[0][c]
        )
        assert len(joined) <= MENU_MAX_LENGTH
        assert warnings

    def test_columns_past_the_budget_are_emptied(self):
        """A first course that fills the whole field leaves no room for the rest."""
        rows, warnings = normalise_rows(
            ANNUAL,
            [
                {
                    "data": "01/09/2026",
                    "primo": "a" * MENU_MAX_LENGTH,
                    "secondo": "Pollo",
                    "contorno": "Insalata",
                    "frutta": "",
                    "altro": "",
                }
            ],
        )

        assert rows[0]["primo"] == "a" * MENU_MAX_LENGTH
        assert rows[0]["secondo"] == ""
        assert rows[0]["contorno"] == ""
        assert warnings


class TestEmptyResult:
    def test_no_usable_row_raises(self):
        with pytest.raises(EmptyResult):
            normalise_rows(SIMPLE, [simple_row(giorno="Domenica")])

    def test_empty_input_raises(self):
        with pytest.raises(EmptyResult):
            normalise_rows(SIMPLE, [])
