from pytest_factoryboy import register

from tests.contacts.factories import MenuReportFactory
from tests.school_menu.factories import (
    AnnualMealFactory,
    DetailedMealFactory,
    SchoolFactory,
    SimpleMealFactory,
)
from tests.users.factories import UserFactory

register(UserFactory)
register(SchoolFactory)
register(SimpleMealFactory)
register(DetailedMealFactory)
register(AnnualMealFactory)
register(MenuReportFactory)
