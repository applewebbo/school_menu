from pytest_factoryboy import register

from tests.school_menu.factories import (
    DetailedMealFactory,
    SchoolFactory,
    SimpleMealFactory,
)
from tests.users.factories import UserFactory

register(UserFactory)
register(SchoolFactory)
register(SimpleMealFactory)
register(DetailedMealFactory)