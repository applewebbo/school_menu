"""
Management command to clear cache.

This command allows clearing all caches or specific school caches.
Useful for debugging, testing, or manual cache maintenance.
"""

from django.core.cache import cache
from django.core.management.base import BaseCommand, CommandError

from school_menu.cache import invalidate_school_cache
from school_menu.models import School


class Command(BaseCommand):
    help = "Clear cache (all or for specific school)"

    def add_arguments(self, parser):
        """Add command arguments."""
        parser.add_argument(
            "--all",
            action="store_true",
            help="Clear all cache",
        )
        parser.add_argument(
            "--school",
            type=int,
            help="School ID to clear cache for",
        )
        parser.add_argument(
            "--slug",
            type=str,
            help="School slug to clear cache for",
        )

    def handle(self, *args, **options):
        """Clear cache based on options."""
        clear_all = options.get("all")
        school_id = options.get("school")
        school_slug = options.get("slug")

        # Validate arguments
        if not (clear_all or school_id or school_slug):
            raise CommandError(
                "You must specify either --all, --school <id>, or --slug <slug>"
            )

        if clear_all and (school_id or school_slug):
            raise CommandError("Cannot use --all with --school or --slug")

        # Clear all cache
        if clear_all:
            self.stdout.write("Clearing all cache...")
            cache.clear()
            self.stdout.write(self.style.SUCCESS("✓ All cache cleared successfully"))
            return

        # Clear cache for specific school
        if school_slug:
            try:
                school = School.objects.get(slug=school_slug)
                school_id = school.id
            except School.DoesNotExist:
                raise CommandError(
                    f"School with slug '{school_slug}' not found"
                ) from None

        if school_id:
            try:
                school = School.objects.get(id=school_id)
            except School.DoesNotExist:
                raise CommandError(f"School with ID {school_id} not found") from None

            self.stdout.write(
                f"Clearing cache for school: {school.name} (ID: {school.id}, Slug: {school.slug})"
            )

            # Invalidate school cache
            deleted_count = invalidate_school_cache(school.id, school.slug)

            self.stdout.write(
                self.style.SUCCESS(
                    f"✓ Cache cleared for school {school.name} ({deleted_count} keys deleted)"
                )
            )
