from datetime import datetime
from unittest import mock

import pytest

from school_menu.utils import calculate_week, get_current_date

pytestmark = pytest.mark.django_db


class TestUtils:
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
