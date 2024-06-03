import factory

from school_menu.models import School
from tests.users.factories import UserFactory


class SchoolFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = School

    name = factory.Faker("sentence", nb_words=3)
    city = factory.Faker("city")
    user = factory.SubFactory(UserFactory)
    season_choice = factory.Iterator(School.Seasons.choices, getter=lambda c: c[0])
    menu_type = factory.Iterator(School.Types.choices, getter=lambda c: c[0])
    week_bias = factory.Faker("random_int", min=0, max=3)
