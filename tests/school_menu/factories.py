import factory
from faker import Faker

from school_menu.models import DetailedMeal, School, SimpleMeal
from tests.users.factories import UserFactory

SCHOOL_PRE = ["Scuola", "Istituto", "Liceo", "Collegio", "Convitto", "Istituto Tecnico"]

MEAL_LIST = [
    "Pappa con formaggio\n200 cc brodo vegetale con verdure passate + 1 cucchiaio di lenticchie\n30 gr formaggio 1 cucchiaino olio d'oliva extravergine\n20 gr riso",
    "Pappa con pomodoro\n200 cc brodo vegetale con carne + 1 cucchiaio di piselli\n30 gr formaggio 1 cucchiaino olio d'oliva extravergine\n20 gr pasta corta",
    "Pappa con tapioca\n200 cc brodo vegetale con verdure passate + 1 cucchiaio di legumi\n30 gr formaggio 1 cucchiaino olio d'oliva extravergine\n20 gr riso",
    "Pappa con formaggio\n200 cc brodo vegetale con carne + 1 cucchiaio di piselli\n30 gr formaggio 1 cucchiaino olio d'oliva extravergine\n20 gr pasta corta",
    "Pappa con tapioca\n200 cc brodo vegetale con carne + 1 cucchiaio di fagioli neri\n30 gr formaggio 1 cucchiaino olio d'oliva extravergine\n20 gr riso",
]

FRUIT_LIST = [
    "Frutta di stagione (banana)",
    "Frutta di stagione (mela)",
    "Frutta di stagione (pera)",
    "Frutta di stagione (arancia)",
    "Frutta di stagione (kiwi)",
]

FIRST_COURSE_LIST = [
    "Pasta al pomodoro",
    "Risotto ai funghi",
    "Pasta al pesto",
    "Risotto alla milanese",
    "Pasta alla carbonara",
]

SECOND_COURSE_LIST = [
    "Pollo alla griglia",
    "Cotoletta di pollo",
    "Pollo al forno",
    "Cotoletta di maiale",
    "Pollo alla cacciatora",
]

SIDE_DISH_LIST = [
    "Fagiolini",
    "Insalata di pomodoro",
    "Broccoli al vapore",
    "Piselli",
    "Patate al forno",
]

SNACK_LIST = [
    "Yogurt",
    "Barretta di cereali",
    "Frutta secca",
    "Frutta fresca",
    "Biscotti",
]

SNACK_LIST_2 = [
    "Yogurt",
    "Frutta Fresca",
    "The deteinato con biscotti",
]

fake = Faker(locale="it_IT")


def generate_school_name():
    # Assuming SCHOOL_PRE is a list of prefixes
    prefix = fake.random_element(elements=SCHOOL_PRE)
    words = " ".join(fake.words(nb=2))
    return f"{prefix} {words}"


class SchoolFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = School

    name = factory.LazyFunction(generate_school_name)
    city = factory.Faker("city")
    user = factory.SubFactory(UserFactory)
    season_choice = factory.Iterator(School.Seasons.choices, getter=lambda c: c[0])
    menu_type = factory.Iterator(School.Types.choices, getter=lambda c: c[0])
    week_bias = factory.Faker("random_int", min=0, max=3)


class SimpleMealFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = SimpleMeal

    school = factory.SubFactory(SchoolFactory)
    day = factory.Iterator(SimpleMeal.Days.choices, getter=lambda c: c[0])
    week = factory.Iterator(SimpleMeal.Weeks.choices, getter=lambda c: c[0])
    season = factory.Iterator(SimpleMeal.Seasons.choices, getter=lambda c: c[0])
    menu = factory.Iterator(MEAL_LIST)
    morning_snack = factory.Iterator(FRUIT_LIST)
    afternoon_snack = factory.Iterator(SNACK_LIST_2)


class DetailedMealFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = DetailedMeal

    school = factory.SubFactory(SchoolFactory)
    day = factory.Iterator(SimpleMeal.Days.choices, getter=lambda c: c[0])
    week = factory.Iterator(SimpleMeal.Weeks.choices, getter=lambda c: c[0])
    season = factory.Iterator(SimpleMeal.Seasons.choices, getter=lambda c: c[0])
    first_course = factory.Iterator(FIRST_COURSE_LIST)
    second_course = factory.Iterator(SECOND_COURSE_LIST)
    side_dish = factory.Iterator(SIDE_DISH_LIST)
    fruit = factory.Iterator(FRUIT_LIST)
    snack = factory.Iterator(SNACK_LIST)
