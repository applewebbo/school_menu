from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.template.defaultfilters import slugify
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from school_menu.cache import invalidate_meal_cache, invalidate_school_cache


class Meal(models.Model):
    class Types(models.TextChoices):
        STANDARD = "S", _("Standard")
        GLUTEN_FREE = "G", _("No Glutine")
        LACTOSE_FREE = "L", _("No Lattosio")
        VEGETARIAN = "V", _("Vegetariano")
        SPECIAL = "P", _("Speciale")

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
        choices=Seasons.choices, default=Seasons.INVERNALE, null=True, blank=True
    )
    type = models.CharField(max_length=1, choices=Types.choices, default=Types.STANDARD)
    school = models.ForeignKey("School", on_delete=models.CASCADE, null=True)

    class Meta:
        abstract = True


class DetailedMeal(Meal):
    first_course = models.CharField(max_length=200)
    second_course = models.CharField(max_length=200)
    side_dish = models.CharField(max_length=200)
    fruit = models.CharField(max_length=200, default="Frutta di Stagione")
    snack = models.CharField(max_length=200)

    class Meta:
        indexes = [
            models.Index(
                fields=["school", "week", "season"], name="detailed_sch_week_season"
            ),
        ]

    def __str__(self):
        return f"{self.get_day_display()} - {self.get_week_display()} [{self.get_season_display()}]"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Invalidate meal cache after successful save
        if self.school_id:
            invalidate_meal_cache(self.school_id)

    def delete(self, *args, **kwargs):
        school_id = self.school_id
        super().delete(*args, **kwargs)
        # Invalidate meal cache after successful delete
        if school_id:
            invalidate_meal_cache(school_id)


class SimpleMeal(Meal):
    menu = models.TextField(max_length=600)
    morning_snack = models.CharField(max_length=200, blank=True)
    afternoon_snack = models.CharField(max_length=200, blank=True)

    class Meta:
        indexes = [
            models.Index(
                fields=["school", "week", "season"], name="simple_sch_week_season"
            ),
        ]

    def __str__(self):
        return f"{self.get_day_display()} - {self.get_week_display()} [{self.get_season_display()}]"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Invalidate meal cache after successful save
        if self.school_id:
            invalidate_meal_cache(self.school_id)

    def delete(self, *args, **kwargs):
        school_id = self.school_id
        super().delete(*args, **kwargs)
        # Invalidate meal cache after successful delete
        if school_id:
            invalidate_meal_cache(school_id)


class AnnualMeal(Meal):
    menu = models.TextField(max_length=600)
    snack = models.CharField(max_length=200, blank=True)
    date = models.DateField()
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.school.name} [{self.date:%d/%m}]"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Invalidate meal cache after successful save
        if self.school_id:
            invalidate_meal_cache(self.school_id)

    def delete(self, *args, **kwargs):
        school_id = self.school_id
        super().delete(*args, **kwargs)
        # Invalidate meal cache after successful delete
        if school_id:
            invalidate_meal_cache(school_id)

    class Meta:
        ordering = ["-date"]
        indexes = [
            models.Index(
                fields=["school", "date", "is_active"], name="annual_sch_date_active"
            ),
        ]


class School(models.Model):
    class Seasons(models.IntegerChoices):
        PRIMAVERILE = 1
        INVERNALE = 2
        AUTOMATICA = 3

    class Types(models.TextChoices):
        SIMPLE = "S", _("Semplice")
        DETAILED = "D", _("Dettagliato")

    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True, editable=False)
    city = models.CharField(max_length=200)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    start_day = models.PositiveSmallIntegerField(
        default=10,
        validators=[MinValueValidator(1), MaxValueValidator(31)],
        verbose_name=_("Giorno inizio anno scolastico"),
    )
    start_month = models.PositiveSmallIntegerField(
        default=9,
        validators=[MinValueValidator(1), MaxValueValidator(12)],
        verbose_name=_("Mese inizio anno scolastico"),
    )
    end_day = models.PositiveSmallIntegerField(
        default=10,
        validators=[MinValueValidator(1), MaxValueValidator(31)],
        verbose_name=_("Giorno fine anno scolastico"),
    )
    end_month = models.PositiveSmallIntegerField(
        default=6,
        validators=[MinValueValidator(1), MaxValueValidator(12)],
        verbose_name=_("Mese fine anno scolastico"),
    )
    season_choice = models.SmallIntegerField(
        choices=Seasons.choices, default=Seasons.AUTOMATICA, verbose_name="stagione"
    )
    week_bias = models.PositiveSmallIntegerField(
        validators=[MaxValueValidator(3)], default=0, verbose_name="scarto"
    )
    menu_type = models.CharField(
        max_length=1, choices=Types.choices, default=Types.DETAILED
    )
    is_published = models.BooleanField(default=True)
    no_gluten = models.BooleanField(default=False)
    no_lactose = models.BooleanField(default=False)
    vegetarian = models.BooleanField(default=False)
    special = models.BooleanField(default=False)
    annual_menu = models.BooleanField(default=False)

    class Meta:
        verbose_name = "scuola"
        verbose_name_plural = "scuole"

    def __str__(self):
        return f"{self.name} - {self.city} ({str(self.user)})"

    def save(self, *args, **kwargs):
        # Only generate slug on creation to prevent URL changes and IntegrityErrors
        if not self.pk:
            self.slug = slugify(f"{self.name}-{self.city}")
        super().save(*args, **kwargs)
        # Invalidate all caches when school settings change
        # Settings like menu_type, season_choice, week_bias, and alternative
        # menu flags affect display even without modifying meals
        invalidate_school_cache(self.id, self.slug)

    def get_absolute_url(self):
        return reverse("school_menu:school_menu", kwargs={"slug": self.slug})

    @property
    def get_json_url(self):
        return reverse("school_menu:get_school_json_menu", kwargs={"slug": self.slug})
