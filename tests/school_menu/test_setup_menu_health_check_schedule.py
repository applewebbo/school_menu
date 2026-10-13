import pytest
from django.core.management import call_command
from django.test import override_settings
from django_q.models import Schedule

from school_menu.management.commands.setup_menu_health_check_schedule import (
    SCHEDULE_NAME,
    TASK_PATH,
)

pytestmark = pytest.mark.django_db


def test_creates_the_cron_schedule():
    call_command("setup_menu_health_check_schedule", verbosity=0)

    schedule = Schedule.objects.get(name=SCHEDULE_NAME)
    assert schedule.func == TASK_PATH
    assert schedule.schedule_type == Schedule.CRON
    assert schedule.repeats == -1


def test_running_it_twice_updates_instead_of_duplicating():
    call_command("setup_menu_health_check_schedule", verbosity=0)
    call_command("setup_menu_health_check_schedule", verbosity=0)

    assert Schedule.objects.filter(name=SCHEDULE_NAME).count() == 1


@override_settings(MENU_HEALTH_CHECK_SCHEDULE="0 7 * * 1")
def test_cron_comes_from_settings():
    call_command("setup_menu_health_check_schedule", verbosity=0)

    assert Schedule.objects.get(name=SCHEDULE_NAME).cron == "0 7 * * 1"


def test_remove_deletes_the_schedule():
    call_command("setup_menu_health_check_schedule", verbosity=0)

    call_command("setup_menu_health_check_schedule", "--remove", verbosity=0)

    assert not Schedule.objects.filter(name=SCHEDULE_NAME).exists()


def test_a_dry_run_changes_nothing():
    call_command("setup_menu_health_check_schedule", "--dry-run")

    assert not Schedule.objects.filter(name=SCHEDULE_NAME).exists()
