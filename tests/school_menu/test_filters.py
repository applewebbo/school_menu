from datetime import datetime, timedelta

from school_menu.templatetags import filters


class TestTruncateFilter:
    def testinputlongerthanmax(self):
        assert filters.truncate("hello", 3) == "hel"

    def testinputshorterthanmax(self):
        assert filters.truncate("hello", 10) == "hello"


class TestWeeksFilter:
    def testrandominput(self):
        assert filters.weeks(3) == range(1, 4)


class TestRemainingDaysFilter:
    def test_remaining_days_with_future_date(self):
        today = datetime.now()
        future_date = today + timedelta(days=10)

        result = filters.remaining_days(future_date)

        assert result == 40  # 30 days + 10 days from today

    def test_remaining_days_with_past_date(self):
        today = datetime.now()
        past_date = today - timedelta(days=40)

        result = filters.remaining_days(past_date)

        assert result == 0

    def test_remaining_days_with_string_date(self):
        date_string = datetime.now().strftime("%Y-%m-%d")

        result = filters.remaining_days(date_string)

        assert result == 30

    def test_remaining_days_with_invalid_string(self):
        invalid_date = "not-a-date"

        result = filters.remaining_days(invalid_date)

        assert result == 0

    def test_remaining_days_with_today(self):
        today = datetime.now()

        result = filters.remaining_days(today)

        assert result == 30
