"""Tests for the daily AI import quota service (#234)."""

import pytest
from django.test import TestCase, override_settings
from django.utils import timezone

from school_menu.models import MenuImportQuota
from school_menu.services.ai_quota import QuotaExceeded, consume, refund, remaining
from tests.users.factories import UserFactory

pytestmark = pytest.mark.django_db


def counts(user):
    today = timezone.localdate()
    user_row = MenuImportQuota.objects.get(user=user, date=today)
    global_row = MenuImportQuota.objects.get(user=None, date=today)
    return user_row.count, global_row.count


@override_settings(
    AI_MENU_IMPORT_USER_DAILY_LIMIT=2, AI_MENU_IMPORT_GLOBAL_DAILY_LIMIT=3
)
class TestConsume(TestCase):
    def test_first_call_creates_both_buckets(self):
        user = UserFactory()

        consume(user)

        assert counts(user) == (1, 1)

    def test_repeated_calls_increment(self):
        user = UserFactory()

        consume(user)
        consume(user)

        assert counts(user) == (2, 2)

    def test_user_limit_is_enforced(self):
        user = UserFactory()
        consume(user)
        consume(user)

        with pytest.raises(QuotaExceeded) as exc:
            consume(user)

        assert exc.value.scope == "user"
        assert counts(user) == (2, 2)

    def test_global_limit_is_enforced_across_users(self):
        first, second = UserFactory(), UserFactory()
        consume(first)
        consume(first)
        consume(second)

        with pytest.raises(QuotaExceeded) as exc:
            consume(second)

        assert exc.value.scope == "global"

    def test_global_failure_rolls_back_the_user_increment(self):
        """Otherwise a user would silently lose a slot to a cap they never hit."""
        first, second = UserFactory(), UserFactory()
        consume(first)
        consume(first)
        consume(second)

        with pytest.raises(QuotaExceeded):
            consume(second)

        assert counts(second) == (1, 3)

    def test_message_is_italian_and_mentions_the_scope(self):
        user = UserFactory()
        consume(user)
        consume(user)

        with pytest.raises(QuotaExceeded) as exc:
            consume(user)

        assert "limite" in str(exc.value).lower()

    def test_a_full_bucket_never_goes_over_the_limit(self):
        """The conditional UPDATE is what makes two concurrent calls safe."""
        user = UserFactory()
        consume(user)
        consume(user)

        for _ in range(3):
            with pytest.raises(QuotaExceeded):
                consume(user)

        assert counts(user) == (2, 2)

    def test_yesterday_does_not_count(self):
        user = UserFactory()
        MenuImportQuota.objects.create(
            user=user, date=timezone.localdate() - timezone.timedelta(days=1), count=99
        )

        consume(user)

        assert counts(user) == (1, 1)


@override_settings(
    AI_MENU_IMPORT_USER_DAILY_LIMIT=2, AI_MENU_IMPORT_GLOBAL_DAILY_LIMIT=3
)
class TestRefund(TestCase):
    def test_refund_gives_the_slot_back(self):
        user = UserFactory()
        consume(user)

        refund(user)

        assert counts(user) == (0, 0)

    def test_refund_allows_consuming_again(self):
        user = UserFactory()
        consume(user)
        consume(user)
        refund(user)

        consume(user)

        assert counts(user) == (2, 2)

    def test_refund_never_goes_below_zero(self):
        user = UserFactory()
        consume(user)

        refund(user)
        refund(user)

        assert counts(user) == (0, 0)

    def test_refund_without_any_row_is_harmless(self):
        user = UserFactory()

        refund(user)

        assert not MenuImportQuota.objects.exists()


@override_settings(
    AI_MENU_IMPORT_USER_DAILY_LIMIT=2, AI_MENU_IMPORT_GLOBAL_DAILY_LIMIT=3
)
class TestRemaining(TestCase):
    def test_full_allowance_when_nothing_was_used(self):
        assert remaining(UserFactory()) == 2

    def test_decreases_as_the_user_consumes(self):
        user = UserFactory()
        consume(user)

        assert remaining(user) == 1

    def test_is_capped_by_the_global_bucket(self):
        """A user with slots left still cannot import once the site cap is reached."""
        first, second = UserFactory(), UserFactory()
        consume(first)
        consume(first)
        consume(second)

        assert remaining(second) == 0

    def test_never_negative(self):
        user = UserFactory()
        MenuImportQuota.objects.create(user=user, date=timezone.localdate(), count=99)

        assert remaining(user) == 0
