import pytest
from django.core.exceptions import ValidationError

from tests.school_menu.factories import SchoolFactory
from tests.users.factories import UserFactory

pytestmark = pytest.mark.django_db


class TestFavoriteSchool:
    def test_default_is_none(self):
        user = UserFactory()
        assert user.favorite_school is None

    def test_can_be_assigned_another_school(self):
        user = UserFactory()
        school = SchoolFactory()
        user.favorite_school = school
        user.save()
        user.refresh_from_db()
        assert user.favorite_school == school

    def test_clean_rejects_own_school_as_favorite(self):
        user = UserFactory()
        own_school = SchoolFactory(user=user)
        user.favorite_school = own_school
        with pytest.raises(ValidationError):
            user.full_clean()

    def test_favorite_cleared_when_school_is_deleted(self):
        user = UserFactory()
        school = SchoolFactory()
        user.favorite_school = school
        user.save()
        school.delete()
        user.refresh_from_db()
        assert user.favorite_school is None
