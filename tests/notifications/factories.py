import factory
from factory.django import DjangoModelFactory

from notifications.models import AnonymousMenuNotification, BroadcastNotification


class AnonymousMenuNotificationFactory(DjangoModelFactory):
    class Meta:
        model = AnonymousMenuNotification

    school = factory.SubFactory("tests.school_menu.factories.SchoolFactory")
    subscription_info = factory.LazyFunction(dict)


class BroadcastNotificationFactory(DjangoModelFactory):
    class Meta:
        model = BroadcastNotification

    title = factory.Sequence(lambda n: f"Broadcast {n}")
    message = factory.Faker("text", max_nb_chars=200)
    url = factory.Faker("url")
    created_by = factory.SubFactory("tests.users.factories.UserFactory")
