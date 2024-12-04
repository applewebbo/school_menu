import factory

from contacts.models import MenuReport
from tests.users.factories import UserFactory


class MenuReportFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = MenuReport

    name = factory.Faker("name")
    message = factory.Faker("text")
    get_notified = factory.Faker("boolean")
    email = factory.Faker("email")
    receiver = factory.SubFactory(UserFactory)
    created_at = factory.Faker("date_time_this_year")
