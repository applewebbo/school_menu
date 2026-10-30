from pytest_factoryboy import register

from tests.contacts.factories import MenuReportFactory
from tests.school_menu.factories import (
    AnnualMealFactory,
    DetailedMealFactory,
    SchoolClosureFactory,
    SchoolFactory,
    SimpleMealFactory,
    SpecialDetailedMealFactory,
    SpecialSimpleMealFactory,
)
from tests.users.factories import UserFactory

register(UserFactory)
register(SchoolFactory)
register(SimpleMealFactory)
register(DetailedMealFactory)
register(AnnualMealFactory)
register(SpecialSimpleMealFactory)
register(SpecialDetailedMealFactory)
register(SchoolClosureFactory)
register(MenuReportFactory)
