"""Tests for the school-handover notification emails (#291)."""

import pytest
from django.core import mail

from school_menu.tasks import send_handover_notice
from tests.school_menu.factories import SchoolFactory
from tests.users.factories import UserFactory

pytestmark = pytest.mark.django_db


class TestSendHandoverNotice:
    def test_sends_email_to_both_parties(self):
        old_user = UserFactory(email="old@test.com")
        new_user = UserFactory(email="new@test.com")
        school = SchoolFactory(user=new_user, name="Scuola Rossi")

        send_handover_notice(school, old_user, new_user)

        assert len(mail.outbox) == 2
        to_old = next(m for m in mail.outbox if m.to == ["old@test.com"])
        to_new = next(m for m in mail.outbox if m.to == ["new@test.com"])
        assert "trasferita" in to_old.subject.lower()
        assert "Scuola Rossi" in to_new.subject
