from datetime import date
from unittest.mock import patch

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from school_menu.models import (
    Meal,
    MirrorFallbackCheck,
    SchoolTransfer,
    SiteSettings,
)
from tests.school_menu.factories import MenuHealthCheckFactory, SchoolTransferFactory
from tests.users.factories import UserFactory

pytestmark = pytest.mark.django_db


class TestDetailedMealModel:
    def test_factory(self, user_factory, school_factory, detailed_meal_factory):
        """Test detailed meal factory"""

        user = user_factory()
        school = school_factory(user=user)
        detailed_meal = detailed_meal_factory(
            school=school, day=1, week=1, season=Meal.Seasons.INVERNALE
        )

        assert detailed_meal.__str__() == "Lunedì - Settimana 1 [Invernale]"


class TestSimpleMealModel:
    def test_factory(self, user_factory, school_factory, simple_meal_factory):
        """Test detailed meal factory"""

        user = user_factory()
        school = school_factory(user=user)
        simple_meal = simple_meal_factory(
            school=school, day=1, week=1, season=Meal.Seasons.INVERNALE
        )

        assert simple_meal.__str__() == "Lunedì - Settimana 1 [Invernale]"


class TestSpecialSimpleMealModel:
    def test_factory(self, school_factory, special_simple_meal_factory):
        school = school_factory()
        meal = special_simple_meal_factory(school=school, date=date(2026, 12, 8))

        assert str(meal) == f"{school.name} [speciale 08/12/2026]"

    def test_unique_constraint_on_school_date_type(
        self, school_factory, special_simple_meal_factory
    ):
        school = school_factory()
        special_simple_meal_factory(
            school=school, date=date(2026, 12, 8), type=Meal.Types.STANDARD
        )

        with pytest.raises(IntegrityError):
            special_simple_meal_factory(
                school=school, date=date(2026, 12, 8), type=Meal.Types.STANDARD
            )

    def test_save_sets_school_has_special_days(
        self, school_factory, special_simple_meal_factory
    ):
        school = school_factory(has_special_days=False)

        special_simple_meal_factory(school=school)

        school.refresh_from_db()
        assert school.has_special_days is True

    def test_delete_last_special_day_resets_has_special_days(
        self, school_factory, special_simple_meal_factory
    ):
        school = school_factory()
        meal = special_simple_meal_factory(school=school)
        school.refresh_from_db()
        assert school.has_special_days is True

        meal.delete()

        school.refresh_from_db()
        assert school.has_special_days is False

    def test_delete_one_of_many_keeps_has_special_days_true(
        self, school_factory, special_simple_meal_factory
    ):
        school = school_factory()
        meal_1 = special_simple_meal_factory(school=school, date=date(2026, 12, 8))
        special_simple_meal_factory(school=school, date=date(2026, 12, 25))

        meal_1.delete()

        school.refresh_from_db()
        assert school.has_special_days is True


class TestSpecialDetailedMealModel:
    def test_factory(self, school_factory, special_detailed_meal_factory):
        school = school_factory()
        meal = special_detailed_meal_factory(school=school, date=date(2026, 12, 8))

        assert str(meal) == f"{school.name} [speciale 08/12/2026]"

    def test_unique_constraint_on_school_date_type(
        self, school_factory, special_detailed_meal_factory
    ):
        school = school_factory()
        special_detailed_meal_factory(
            school=school, date=date(2026, 12, 8), type=Meal.Types.STANDARD
        )

        with pytest.raises(IntegrityError):
            special_detailed_meal_factory(
                school=school, date=date(2026, 12, 8), type=Meal.Types.STANDARD
            )

    def test_save_sets_school_has_special_days(
        self, school_factory, special_detailed_meal_factory
    ):
        school = school_factory(has_special_days=False)

        special_detailed_meal_factory(school=school)

        school.refresh_from_db()
        assert school.has_special_days is True

    def test_delete_last_special_day_resets_has_special_days(
        self, school_factory, special_detailed_meal_factory
    ):
        school = school_factory()
        meal = special_detailed_meal_factory(school=school)
        school.refresh_from_db()
        assert school.has_special_days is True

        meal.delete()

        school.refresh_from_db()
        assert school.has_special_days is False


class TestSchoolHasSpecialDaysAcrossMealTypes:
    """A school's has_special_days reflects both Special*Meal models combined."""

    def test_simple_and_detailed_special_meals_both_set_flag(
        self,
        school_factory,
        special_simple_meal_factory,
        special_detailed_meal_factory,
    ):
        school = school_factory(has_special_days=False)
        simple_meal = special_simple_meal_factory(school=school, date=date(2026, 12, 8))
        special_detailed_meal_factory(school=school, date=date(2026, 12, 25))

        simple_meal.delete()

        school.refresh_from_db()
        assert school.has_special_days is True


class TestSiteSettingsModel:
    """Singleton site settings (#327): always one row, cached between saves."""

    def test_save_forces_pk_to_1(self):
        settings_a = SiteSettings(enable_ads=True)
        settings_a.save()
        settings_b = SiteSettings(enable_kofi=True)
        settings_b.save()

        assert settings_a.pk == 1
        assert settings_b.pk == 1
        assert SiteSettings.objects.count() == 1
        assert SiteSettings.objects.get().enable_kofi is True

    def test_str(self):
        assert str(SiteSettings()) == "Impostazioni del sito"

    def test_get_solo_creates_row_with_defaults_when_missing(self):
        assert not SiteSettings.objects.exists()

        settings = SiteSettings.get_solo()

        assert settings.pk == 1
        assert settings.enable_ads is False
        assert settings.enable_kofi is False

    def test_get_solo_returns_cached_value_without_querying(self):
        """DummyCache in tests never really stores anything, so cache.get is mocked
        to simulate a hit, matching the pattern in tests/school_menu/test_cache.py."""
        cached = SiteSettings(pk=1, enable_kofi=True)
        with patch("school_menu.cache.cache") as mock_cache:
            mock_cache.get.return_value = cached
            with patch(
                "school_menu.models.SiteSettings.objects.get_or_create"
            ) as mock_get_or_create:
                result = SiteSettings.get_solo()

        assert result is cached
        mock_get_or_create.assert_not_called()

    @patch("school_menu.models.invalidate_site_settings_cache")
    def test_save_invalidates_cache(self, mock_invalidate):
        SiteSettings().save()

        mock_invalidate.assert_called_once()

    def test_clean_rejects_enabled_ads_without_client_id(self):
        settings = SiteSettings(enable_ads=True, adsense_client_id="")

        with pytest.raises(ValidationError) as exc_info:
            settings.clean()

        assert "adsense_client_id" in exc_info.value.message_dict

    def test_clean_rejects_enabled_kofi_without_url(self):
        settings = SiteSettings(enable_kofi=True, kofi_url="")

        with pytest.raises(ValidationError) as exc_info:
            settings.clean()

        assert "kofi_url" in exc_info.value.message_dict

    def test_clean_accepts_enabled_integrations_with_values(self):
        settings = SiteSettings(
            enable_ads=True,
            adsense_client_id="ca-pub-test",
            enable_kofi=True,
            kofi_url="https://ko-fi.com/test",
        )

        settings.clean()

    def test_clean_accepts_disabled_integrations_without_values(self):
        settings = SiteSettings()

        settings.clean()


class TestSchoolModel:
    def test_factory(self, user_factory, school_factory):
        user = user_factory(email="test@email.com")
        school = school_factory(user=user, name="Test School", city="Test City")

        assert school.__str__() == "Test School - Test City (test@email.com)"

    def test_absolute_url(self, school_factory):
        school = school_factory()

        assert school.get_absolute_url() == f"/menu/{school.slug}/"

    def test_slug_generated_on_creation(self, user_factory):
        """Test that slug is automatically generated when creating a school."""
        from school_menu.models import School

        user = user_factory()
        school = School.objects.create(user=user, name="Scuola Elementare", city="Roma")

        assert school.slug == "scuola-elementare-roma"

    def test_slug_stable_on_update(self, user_factory, school_factory):
        """Test that slug doesn't change when updating other fields."""
        user = user_factory()
        school = school_factory(user=user, name="Scuola Elementare", city="Roma")
        original_slug = school.slug

        # Update various fields
        school.menu_type = "D"
        school.week_bias = 2
        school.season_choice = 1
        school.save()

        # Slug should remain unchanged
        assert school.slug == original_slug

    def test_slug_stable_when_updating_name_and_city(
        self, user_factory, school_factory
    ):
        """Test that slug doesn't change even if name/city are updated."""
        user = user_factory()
        school = school_factory(user=user, name="Scuola Elementare", city="Roma")
        original_slug = school.slug

        # Try to change name and city
        school.name = "Scuola Media"
        school.city = "Milano"
        school.save()

        # Slug should remain unchanged (this prevents breaking URLs)
        assert school.slug == original_slug
        # But the actual fields should be updated
        assert school.name == "Scuola Media"
        assert school.city == "Milano"


class TestSchoolModelMirrorFrom:
    def test_mirror_from_defaults_to_none(self, school_factory):
        school = school_factory()

        assert school.mirror_from is None

    def test_get_display_school_returns_self_when_no_mirror(self, school_factory):
        school = school_factory()

        assert school.get_display_school() == school

    def test_get_display_school_returns_source_when_valid(self, school_factory):
        source = school_factory(is_published=True)
        mirroring = school_factory(mirror_from=source)

        assert mirroring.get_display_school() == source

    def test_get_display_school_falls_back_when_source_unpublished(
        self, school_factory
    ):
        source = school_factory(is_published=False)
        mirroring = school_factory(mirror_from=source)

        assert mirroring.get_display_school() == mirroring

    def test_get_display_school_falls_back_when_source_itself_mirrors(
        self, school_factory
    ):
        root = school_factory(is_published=True)
        middle = school_factory(is_published=True)
        middle.mirror_from_id = root.id
        middle.save(update_fields=["mirror_from"])
        mirroring = school_factory(mirror_from=middle)

        assert mirroring.get_display_school() == mirroring

    def test_clean_rejects_self_mirror(self, school_factory):
        school = school_factory()
        school.mirror_from_id = school.id

        with pytest.raises(ValidationError):
            school.clean()

    def test_clean_rejects_mirroring_a_school_that_already_mirrors(
        self, school_factory
    ):
        root = school_factory(is_published=True)
        middle = school_factory(mirror_from=root)
        leaf = school_factory()
        leaf.mirror_from = middle

        with pytest.raises(ValidationError):
            leaf.clean()

    def test_clean_allows_valid_mirror(self, school_factory):
        source = school_factory(is_published=True)
        mirroring = school_factory()
        mirroring.mirror_from = source

        mirroring.clean()


class TestMirrorFallbackCheckModel:
    def test_str(self, school_factory):
        school = school_factory(name="Scuola A")
        check = MirrorFallbackCheck.objects.create(school=school)

        assert str(check) == f"{school.name}: fallback non attivo"

    def test_str_when_notified(self, school_factory):
        from django.utils import timezone

        school = school_factory(name="Scuola A")
        check = MirrorFallbackCheck.objects.create(
            school=school, notified_at=timezone.now()
        )

        assert str(check) == f"{school.name}: fallback attivo"


class TestAnnualMenuModel:
    def test_factory(self, user_factory, school_factory, annual_meal_factory):
        user = user_factory()
        school = school_factory(user=user, name="Test School")
        annual_meal = annual_meal_factory(school=school, date=date(2022, 1, 1))

        assert annual_meal.__str__() == "Test School [01/01]"


class TestCacheInvalidationOnModelSave:
    """Test cache invalidation when models are saved/deleted."""

    @patch("school_menu.models.invalidate_meal_cache")
    def test_detailed_meal_save_invalidates_cache(
        self, mock_invalidate, user_factory, school_factory, detailed_meal_factory
    ):
        """Test that saving a DetailedMeal invalidates the meal cache."""
        user = user_factory()
        school = school_factory(user=user)

        # Create a detailed meal (triggers save)
        _detailed_meal = detailed_meal_factory(school=school)  # noqa: F841

        # Verify invalidate_meal_cache was called with correct school_id
        mock_invalidate.assert_called_with(school.id)

    @patch("school_menu.models.invalidate_meal_cache")
    def test_detailed_meal_delete_invalidates_cache(
        self, mock_invalidate, user_factory, school_factory, detailed_meal_factory
    ):
        """Test that deleting a DetailedMeal invalidates the meal cache."""
        user = user_factory()
        school = school_factory(user=user)

        # Create a detailed meal
        detailed_meal = detailed_meal_factory(school=school)
        mock_invalidate.reset_mock()

        # Delete the meal
        detailed_meal.delete()

        # Verify invalidate_meal_cache was called with correct school_id
        mock_invalidate.assert_called_with(school.id)

    @patch("school_menu.models.invalidate_meal_cache")
    def test_simple_meal_save_invalidates_cache(
        self, mock_invalidate, user_factory, school_factory, simple_meal_factory
    ):
        """Test that saving a SimpleMeal invalidates the meal cache."""
        user = user_factory()
        school = school_factory(user=user)

        # Create a simple meal (triggers save)
        _simple_meal = simple_meal_factory(school=school)  # noqa: F841

        # Verify invalidate_meal_cache was called with correct school_id
        mock_invalidate.assert_called_with(school.id)

    @patch("school_menu.models.invalidate_meal_cache")
    def test_simple_meal_delete_invalidates_cache(
        self, mock_invalidate, user_factory, school_factory, simple_meal_factory
    ):
        """Test that deleting a SimpleMeal invalidates the meal cache."""
        user = user_factory()
        school = school_factory(user=user)

        # Create a simple meal
        simple_meal = simple_meal_factory(school=school)
        mock_invalidate.reset_mock()

        # Delete the meal
        simple_meal.delete()

        # Verify invalidate_meal_cache was called with correct school_id
        mock_invalidate.assert_called_with(school.id)

    @patch("school_menu.models.invalidate_meal_cache")
    def test_annual_meal_save_invalidates_cache(
        self, mock_invalidate, user_factory, school_factory, annual_meal_factory
    ):
        """Test that saving an AnnualMeal invalidates the meal cache."""
        user = user_factory()
        school = school_factory(user=user)

        # Create an annual meal (triggers save)
        _annual_meal = annual_meal_factory(school=school)  # noqa: F841

        # Verify invalidate_meal_cache was called with correct school_id
        mock_invalidate.assert_called_with(school.id)

    @patch("school_menu.models.invalidate_meal_cache")
    def test_annual_meal_delete_invalidates_cache(
        self, mock_invalidate, user_factory, school_factory, annual_meal_factory
    ):
        """Test that deleting an AnnualMeal invalidates the meal cache."""
        user = user_factory()
        school = school_factory(user=user)

        # Create an annual meal
        annual_meal = annual_meal_factory(school=school)
        mock_invalidate.reset_mock()

        # Delete the meal
        annual_meal.delete()

        # Verify invalidate_meal_cache was called with correct school_id
        mock_invalidate.assert_called_with(school.id)

    @patch("school_menu.models.invalidate_meal_cache")
    def test_special_simple_meal_save_invalidates_cache(
        self, mock_invalidate, user_factory, school_factory, special_simple_meal_factory
    ):
        """Test that saving a SpecialSimpleMeal invalidates the meal cache."""
        user = user_factory()
        school = school_factory(user=user)

        _special_meal = special_simple_meal_factory(school=school)  # noqa: F841

        mock_invalidate.assert_called_with(school.id)

    @patch("school_menu.models.invalidate_meal_cache")
    def test_special_simple_meal_delete_invalidates_cache(
        self, mock_invalidate, user_factory, school_factory, special_simple_meal_factory
    ):
        """Test that deleting a SpecialSimpleMeal invalidates the meal cache."""
        user = user_factory()
        school = school_factory(user=user)
        special_meal = special_simple_meal_factory(school=school)
        mock_invalidate.reset_mock()

        special_meal.delete()

        mock_invalidate.assert_called_with(school.id)

    @patch("school_menu.models.invalidate_meal_cache")
    def test_special_detailed_meal_save_invalidates_cache(
        self,
        mock_invalidate,
        user_factory,
        school_factory,
        special_detailed_meal_factory,
    ):
        """Test that saving a SpecialDetailedMeal invalidates the meal cache."""
        user = user_factory()
        school = school_factory(user=user)

        _special_meal = special_detailed_meal_factory(school=school)  # noqa: F841

        mock_invalidate.assert_called_with(school.id)

    @patch("school_menu.models.invalidate_meal_cache")
    def test_special_detailed_meal_delete_invalidates_cache(
        self,
        mock_invalidate,
        user_factory,
        school_factory,
        special_detailed_meal_factory,
    ):
        """Test that deleting a SpecialDetailedMeal invalidates the meal cache."""
        user = user_factory()
        school = school_factory(user=user)
        special_meal = special_detailed_meal_factory(school=school)
        mock_invalidate.reset_mock()

        special_meal.delete()

        mock_invalidate.assert_called_with(school.id)

    @patch("school_menu.models.invalidate_school_cache")
    def test_school_save_invalidates_cache(
        self, mock_invalidate, user_factory, school_factory
    ):
        """Test that saving a School invalidates all school caches."""
        user = user_factory()

        # Create a school (triggers save)
        school = school_factory(user=user)

        # Verify invalidate_school_cache was called with correct school_id and slug
        mock_invalidate.assert_called_with(school.id, school.slug)

    @patch("school_menu.models.invalidate_meal_cache")
    def test_detailed_meal_save_without_school_doesnt_invalidate(
        self, mock_invalidate, detailed_meal_factory
    ):
        """Test that saving a DetailedMeal without school doesn't call invalidate."""
        # Create a detailed meal without school
        _detailed_meal = detailed_meal_factory(school=None)  # noqa: F841

        # Verify invalidate_meal_cache was NOT called
        mock_invalidate.assert_not_called()

    @patch("school_menu.models.invalidate_meal_cache")
    def test_simple_meal_save_without_school_doesnt_invalidate(
        self, mock_invalidate, simple_meal_factory
    ):
        """Test that saving a SimpleMeal without school doesn't call invalidate."""
        # Create a simple meal without school
        _simple_meal = simple_meal_factory(school=None)  # noqa: F841

        # Verify invalidate_meal_cache was NOT called
        mock_invalidate.assert_not_called()

    @patch("school_menu.models.invalidate_meal_cache")
    def test_annual_meal_save_without_school_doesnt_invalidate(
        self, mock_invalidate, annual_meal_factory
    ):
        """Test that saving an AnnualMeal without school doesn't call invalidate."""
        # Create an annual meal without school
        _annual_meal = annual_meal_factory(school=None)  # noqa: F841

        # Verify invalidate_meal_cache was NOT called
        mock_invalidate.assert_not_called()

    @patch("school_menu.models.invalidate_meal_cache")
    def test_detailed_meal_delete_without_school_doesnt_invalidate(
        self, mock_invalidate, detailed_meal_factory
    ):
        """Test that deleting a DetailedMeal without school doesn't call invalidate."""
        # Create a detailed meal without school
        detailed_meal = detailed_meal_factory(school=None)
        mock_invalidate.reset_mock()

        # Delete the meal
        detailed_meal.delete()

        # Verify invalidate_meal_cache was NOT called
        mock_invalidate.assert_not_called()

    @patch("school_menu.models.invalidate_meal_cache")
    def test_simple_meal_delete_without_school_doesnt_invalidate(
        self, mock_invalidate, simple_meal_factory
    ):
        """Test that deleting a SimpleMeal without school doesn't call invalidate."""
        # Create a simple meal without school
        simple_meal = simple_meal_factory(school=None)
        mock_invalidate.reset_mock()

        # Delete the meal
        simple_meal.delete()

        # Verify invalidate_meal_cache was NOT called
        mock_invalidate.assert_not_called()

    @patch("school_menu.models.invalidate_meal_cache")
    def test_annual_meal_delete_without_school_doesnt_invalidate(
        self, mock_invalidate, annual_meal_factory
    ):
        """Test that deleting an AnnualMeal without school doesn't call invalidate."""
        # Create an annual meal without school
        annual_meal = annual_meal_factory(school=None)
        mock_invalidate.reset_mock()

        # Delete the meal
        annual_meal.delete()

        # Verify invalidate_meal_cache was NOT called
        mock_invalidate.assert_not_called()


class TestMenuHealthCheckModel:
    def test_str(self):
        health_check = MenuHealthCheckFactory(consecutive_missing_weeks=2)

        assert health_check.__str__() == (
            f"{health_check.school.name}: 2 settimane senza menu"
        )


class TestSchoolModelSeekingMaintainer:
    def test_seeking_maintainer_defaults_to_false(self, school_factory):
        school = school_factory()

        assert school.seeking_maintainer is False


class TestSchoolTransferModel:
    def test_str(self):
        to_user = UserFactory(email="candidate@email.com")
        transfer = SchoolTransferFactory(to_user=to_user)

        assert transfer.__str__() == (
            f"{transfer.school.name}: {transfer.from_user} -> {to_user} (Richiesto)"
        )

    def test_default_status_is_requested(self):
        transfer = SchoolTransferFactory()

        assert transfer.status == SchoolTransfer.Status.REQUESTED
        assert transfer.resolved_at is None
