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


def test_a_hand_made_schedule_for_the_same_task_is_removed():
    """A pre-existing row firing one of our tasks under another name would double
    every send once our rows are added — the command deletes it."""
    task_path = SCHEDULES["Menu Notification - Same Day 9AM"][0]
    Schedule.objects.create(
        name="old hand-made 9am",
        func=task_path,
        schedule_type=Schedule.CRON,
        cron="0 9 * * *",
        repeats=-1,
    )

    call_command("setup_notification_schedules", verbosity=0)

    assert not Schedule.objects.filter(name="old hand-made 9am").exists()
    assert Schedule.objects.filter(name__in=SLOT_NAMES).count() == 4


def test_unrelated_schedules_are_left_alone():
    Schedule.objects.create(
        name="AI Menu Import Purge",
        func="school_menu.tasks.purge_menu_import_drafts",
        schedule_type=Schedule.CRON,
        cron="30 3 * * *",
        repeats=-1,
    )

    call_command("setup_notification_schedules", verbosity=0)

    assert Schedule.objects.filter(name="AI Menu Import Purge").exists()


def test_a_dry_run_does_not_remove_strays():
    task_path = SCHEDULES["Menu Notification - Same Day 9AM"][0]
    Schedule.objects.create(
        name="old hand-made 9am",
        func=task_path,
        schedule_type=Schedule.CRON,
        cron="0 9 * * *",
        repeats=-1,
    )

    call_command("setup_notification_schedules", "--dry-run")

    assert Schedule.objects.filter(name="old hand-made 9am").exists()
