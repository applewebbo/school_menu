from django.conf import settings
from django.core.validators import MaxValueValidator
from django.db import models
from django.template.defaultfilters import slugify


class Meal(models.Model):
    class Types(models.IntegerChoices):
        STANDARD = 1
        GLUTEN_FREE = 2
        LACTOSE_FREE = 3
        VEGAN = 4

    class Seasons(models.IntegerChoices):
        ESTIVO = 1
        INVERNALE = 2

    class Weeks(models.IntegerChoices):
        SETTIMANA_1 = 1
        SETTIMANA_2 = 2
        SETTIMANA_3 = 3
        SETTIMANA_4 = 4

    class Days(models.IntegerChoices):
        LUNEDÌ = 1
        MARTEDÌ = 2
        MERCOLEDÌ = 3
        GIOVEDÌ = 4
        VENERDÌ = 5

    day = models.SmallIntegerField(choices=Days.choices, default=Days.LUNEDÌ)
    week = models.SmallIntegerField(choices=Weeks.choices, default=Weeks.SETTIMANA_1)
    season = models.SmallIntegerField(
        choices=Seasons.choices, default=Seasons.INVERNALE
    )
    type = models.SmallIntegerField(choices=Types.choices, default=Types.STANDARD)
    school = models.ForeignKey("School", on_delete=models.CASCADE, null=True)

    class Meta:
        abstract = True

    def __str__(self):
        return f"{self.get_day_display()} - {self.get_week_display()} [{self.get_season_display()}]"


class DetailedMeal(Meal):
    first_course = models.CharField(max_length=200)
    second_course = models.CharField(max_length=200)
    side_dish = models.CharField(max_length=200)
    fruit = models.CharField(max_length=200, default="Frutta di Stagione")
    snack = models.CharField(max_length=200)


class SimpleMeal(Meal):
    menu = models.CharField(max_length=600)


class Settings(models.Model):
    class Seasons(models.IntegerChoices):
        PRIMAVERILE = 1
        INVERNALE = 2

    season_choice = models.SmallIntegerField(
        choices=Seasons.choices, default=Seasons.INVERNALE, verbose_name="stagione"
    )
    week_bias = models.PositiveSmallIntegerField(
        validators=[MaxValueValidator(3)], default=0, verbose_name="scarto"
    )
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    class Meta:
        verbose_name = "impostazione"
        verbose_name_plural = "impostazioni"

    def __str__(self):
        return str(self.user)


class School(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True, editable=False)
    city = models.CharField(max_length=200)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    class Meta:
        verbose_name = "scuola"
        verbose_name_plural = "scuole"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.slug = slugify(self.name)
        super().save(*args, **kwargs)
