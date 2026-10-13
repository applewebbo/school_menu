"""Tests for the weekly menu-publication health check (#316)."""

from datetime import datetime

import pytest
import time_machine
from django.core import mail
from django.utils import timezone

from school_menu.models import MenuHealthCheck, School
from school_menu.tasks import check_weekly_menu_publication
from tests.school_menu.factories import (
    AnnualMealFactory,
    DetailedMealFactory,
    SchoolFactory,
)

pytestmark = pytest.mark.django_db

# Monday, ISO week 37 (2026-09-07), inside the default academic year window.
MONDAY = datetime(2026, 9, 7, 6, 0)


def open_school(**extra):
    defaults = {
        "is_published": True,
        "annual_menu": False,
        "menu_type": School.Types.DETAILED,
        "week_bias": 0,
        "season_choice": School.Seasons.PRIMAVERILE,
        "start_day": 1,
        "start_month": 9,
        "end_day": 10,
        "end_month": 6,
    }
    defaults.update(extra)
    return SchoolFactory(**defaults)


class TestCheckWeeklyMenuPublication:
    def test_school_with_menu_is_not_flagged(self):
        school = open_school()
        DetailedMealFactory(school=school, week=1, season=School.Seasons.PRIMAVERILE)

        with time_machine.travel(MONDAY, tick=False):
            check_weekly_menu_publication()

        assert not MenuHealthCheck.objects.filter(school=school).exists()
        assert len(mail.outbox) == 0

    def test_school_without_menu_increments_counter(self):
        school = open_school()

        with time_machine.travel(MONDAY, tick=False):
            check_weekly_menu_publication()

        health_check = MenuHealthCheck.objects.get(school=school)
        assert health_check.consecutive_missing_weeks == 1
        assert health_check.warning_sent_at is None
        assert len(mail.outbox) == 0

    def test_two_consecutive_weeks_sends_one_warning_email(self):
        school = open_school()
        health_check = MenuHealthCheck.objects.create(
            school=school, consecutive_missing_weeks=1
        )

        with time_machine.travel(MONDAY, tick=False):
            check_weekly_menu_publication()

        health_check.refresh_from_db()
        assert health_check.consecutive_missing_weeks == 2
        assert health_check.warning_sent_at is not None
        assert len(mail.outbox) == 1
        assert mail.outbox[0].to == [school.user.email]

    def test_warning_is_not_sent_twice(self):
        school = open_school()
        with time_machine.travel(MONDAY, tick=False):
            MenuHealthCheck.objects.create(
                school=school,
                consecutive_missing_weeks=1,
                warning_sent_at=None,
            )
            check_weekly_menu_publication()
        assert len(mail.outbox) == 1

        next_monday = MONDAY.replace(day=14)
        with time_machine.travel(next_monday, tick=False):
            check_weekly_menu_publication()

        health_check = MenuHealthCheck.objects.get(school=school)
        assert health_check.consecutive_missing_weeks == 3
        assert len(mail.outbox) == 1

    def test_four_consecutive_weeks_unpublishes_school(self):
        school = open_school()
        MenuHealthCheck.objects.create(
            school=school,
            consecutive_missing_weeks=3,
            warning_sent_at=timezone.make_aware(MONDAY),
        )

        with time_machine.travel(MONDAY, tick=False):
            check_weekly_menu_publication()

        school.refresh_from_db()
        assert school.is_published is False

        health_check = MenuHealthCheck.objects.get(school=school)
        assert health_check.consecutive_missing_weeks == 0
        assert health_check.warning_sent_at is None

        assert len(mail.outbox) == 1
        assert "disattivat" in mail.outbox[0].subject.lower()

    def test_publishing_a_menu_resets_the_counter(self):
        school = open_school()
        MenuHealthCheck.objects.create(
            school=school,
            consecutive_missing_weeks=1,
            warning_sent_at=None,
        )
        DetailedMealFactory(school=school, week=1, season=School.Seasons.PRIMAVERILE)

        with time_machine.travel(MONDAY, tick=False):
            check_weekly_menu_publication()

        health_check = MenuHealthCheck.objects.get(school=school)
        assert health_check.consecutive_missing_weeks == 0
        assert health_check.warning_sent_at is None

    def test_unpublished_school_is_skipped(self):
        school = open_school(is_published=False)

        with time_machine.travel(MONDAY, tick=False):
            check_weekly_menu_publication()

        assert not MenuHealthCheck.objects.filter(school=school).exists()
        assert len(mail.outbox) == 0

    def test_annual_menu_school_without_menu_increments_counter(self):
        school = open_school(annual_menu=True)

        with time_machine.travel(MONDAY, tick=False):
            check_weekly_menu_publication()

        health_check = MenuHealthCheck.objects.get(school=school)
        assert health_check.consecutive_missing_weeks == 1

    def test_annual_menu_school_with_menu_is_not_flagged(self):
        school = open_school(annual_menu=True)
        AnnualMealFactory(school=school, date=MONDAY.date(), is_active=True)

        with time_machine.travel(MONDAY, tick=False):
            check_weekly_menu_publication()

        assert not MenuHealthCheck.objects.filter(school=school).exists()

    def test_school_out_of_session_is_skipped(self):
        school = open_school(start_month=1, start_day=10, end_month=2, end_day=10)

        with time_machine.travel(MONDAY, tick=False):
            check_weekly_menu_publication()

        assert not MenuHealthCheck.objects.filter(school=school).exists()
        assert len(mail.outbox) == 0
