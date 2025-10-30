"""
Management command to warm up the cache.

This command pre-populates the cache with meal data for published schools.
Useful after deployments or cache clears to improve initial response times.
"""

from django.core.management.base import BaseCommand

from school_menu.models import School
from school_menu.utils import (
    calculate_week,
    get_current_date,
    get_meals,
    get_meals_for_annual_menu,
    get_season,
)


class Command(BaseCommand):
    help = "Warm up cache by pre-loading meal data for published schools"

    def add_arguments(self, parser):
        """Add command arguments."""
        parser.add_argument(
            "--school",
            type=int,
            help="Warm cache for specific school ID only",
        )

    def handle(self, *args, **options):
        """Warm up the cache."""
        school_id = options.get("school")

        if school_id:
            try:
                schools = [School.objects.get(id=school_id)]
                self.stdout.write(f"Warming cache for school ID {school_id}...")
            except School.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f"School with ID {school_id} not found")
                )
                return
        else:
            schools = School.objects.filter(is_published=True)
            self.stdout.write(
                f"Warming cache for {schools.count()} published schools..."
            )

        current_week, adjusted_day = get_current_date()
        success_count = 0
        error_count = 0

        for school in schools:
            try:
                bias = school.week_bias
                calculate_week(current_week, bias)
                get_season(school)

                if school.annual_menu:
                    # Warm cache for annual menu
                    weekly_meals, meals_for_today = get_meals_for_annual_menu(school)
                else:
                    # Warm cache for weekly menu (all weeks and seasons)
                    for week in range(1, 5):  # Weeks 1-4
                        for season_choice in [1, 2]:  # Summer and Winter
                            get_meals(school, season_choice, week, adjusted_day)

                success_count += 1
                self.stdout.write(f"  ✓ {school.name} ({school.slug})")

            except Exception as e:
                error_count += 1
                self.stdout.write(
                    self.style.WARNING(f"  ✗ {school.name} ({school.slug}): {str(e)}")
                )

        self.stdout.write("\n" + "=" * 50)
        self.stdout.write(
            self.style.SUCCESS(
                f"✓ Cache warming complete: {success_count} succeeded, {error_count} failed"
            )
        )
