"""Tests for the mirror-fallback notification check (#318)."""

import pytest
from django.core import mail

from school_menu.models import MirrorFallbackCheck
from school_menu.tasks import check_mirror_fallbacks
from tests.school_menu.factories import SchoolFactory

pytestmark = pytest.mark.django_db


class TestCheckMirrorFallbacks:
    def test_schools_without_mirror_are_ignored(self):
        SchoolFactory()

        check_mirror_fallbacks()

        assert MirrorFallbackCheck.objects.count() == 0
        assert len(mail.outbox) == 0

    def test_published_source_sends_no_email(self):
        source = SchoolFactory(is_published=True)
        SchoolFactory(mirror_from=source)

        check_mirror_fallbacks()

        assert len(mail.outbox) == 0

    def test_unpublished_source_sends_email_once(self):
        source = SchoolFactory(is_published=False)
        mirroring = SchoolFactory(mirror_from=source)

        check_mirror_fallbacks()

        assert len(mail.outbox) == 1
        assert mail.outbox[0].to == [mirroring.user.email]
        check = MirrorFallbackCheck.objects.get(school=mirroring)
        assert check.notified_at is not None

    def test_not_resent_on_subsequent_runs(self):
        source = SchoolFactory(is_published=False)
        SchoolFactory(mirror_from=source)

        check_mirror_fallbacks()
        check_mirror_fallbacks()

        assert len(mail.outbox) == 1

    def test_resent_after_republish_then_unpublish_again(self):
        source = SchoolFactory(is_published=False)
        SchoolFactory(mirror_from=source)

        check_mirror_fallbacks()
        assert len(mail.outbox) == 1

        source.is_published = True
        source.save()
        check_mirror_fallbacks()

        check = MirrorFallbackCheck.objects.get(school__mirror_from=source)
        assert check.notified_at is None

        source.is_published = False
        source.save()
        check_mirror_fallbacks()

        assert len(mail.outbox) == 2
