import pytest
from django.core.management import call_command
from django.test import override_settings
from django_q.models import Schedule

from notifications.management.commands.setup_notification_schedules import SCHEDULES

pytestmark = pytest.mark.django_db

SLOT_NAMES = list(SCHEDULES)


def test_creates_one_cron_schedule_per_slot():
    call_command("setup_notification_schedules", verbosity=0)

    assert Schedule.objects.filter(name__in=SLOT_NAMES).count() == 4
    for name, (task_path, _) in SCHEDULES.items():
        schedule = Schedule.objects.get(name=name)
        assert schedule.func == task_path
        assert schedule.schedule_type == Schedule.CRON
        assert schedule.repeats == -1


def test_running_it_twice_updates_instead_of_duplicating():
    call_command("setup_notification_schedules", verbosity=0)
    call_command("setup_notification_schedules", verbosity=0)

    assert Schedule.objects.filter(name__in=SLOT_NAMES).count() == 4


@override_settings(
    NOTIFICATION_SCHEDULE_CRONS={
        "previous_day_6pm": "0 17 * * *",
        "same_day_9am": "30 8 * * *",
        "same_day_12pm": "0 12 * * *",
        "same_day_6pm": "0 18 * * *",
    }
)
def test_cron_comes_from_settings():
    call_command("setup_notification_schedules", verbosity=0)

    assert (
        Schedule.objects.get(name="Menu Notification - Same Day 9AM").cron
        == "30 8 * * *"
    )


def test_remove_deletes_every_slot():
    call_command("setup_notification_schedules", verbosity=0)

    call_command("setup_notification_schedules", "--remove", verbosity=0)

    assert not Schedule.objects.filter(name__in=SLOT_NAMES).exists()


def test_a_dry_run_changes_nothing():
    call_command("setup_notification_schedules", "--dry-run")

    assert not Schedule.objects.exists()


def test_a_dry_run_removal_changes_nothing():
    call_command("setup_notification_schedules", verbosity=0)

    call_command("setup_notification_schedules", "--remove", "--dry-run")

    assert Schedule.objects.filter(name__in=SLOT_NAMES).count() == 4
