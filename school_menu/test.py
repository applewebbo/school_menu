from test_plus.test import TestCase as PlusTestCase

from tests.users.factories import UserFactory


class TestCase(PlusTestCase):
    user_factory = UserFactory
