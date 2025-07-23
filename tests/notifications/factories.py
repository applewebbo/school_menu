import factory
from factory.django import DjangoModelFactory

from notifications.models import AnonymousMenuNotification


class AnonymousMenuNotificationFactory(DjangoModelFactory):
    class Meta:
        model = AnonymousMenuNotification

    school = factory.SubFactory("tests.school_menu.factories.SchoolFactory")
    subscription_info = factory.LazyFunction(dict)
