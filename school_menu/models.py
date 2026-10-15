from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models.signals import post_delete
from django.dispatch import receiver
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
    first_course = models.CharField(max_length=200, blank=True)
    second_course = models.CharField(max_length=200, blank=True)
    side_dish = models.CharField(max_length=200, blank=True)
    fruit = models.CharField(max_length=200, blank=True, default="Frutta di Stagione")
    snack = models.CharField(max_length=200, blank=True)

    class Meta:
        verbose_name = "menu dettagliato"
        verbose_name_plural = "menu dettagliati"
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
        verbose_name = "menu semplice"
        verbose_name_plural = "menu semplici"
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
        verbose_name = "menu annuale"
        verbose_name_plural = "menu annuali"
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
    seeking_maintainer = models.BooleanField(default=False)
    mirror_from = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="mirrored_by",
        verbose_name="mostra il menu di",
    )

    class Meta:
        verbose_name = "scuola"
        verbose_name_plural = "scuole"

    def __str__(self):
        return f"{self.name} - {self.city} ({str(self.user)})"

    def clean(self):
        super().clean()
        if self.mirror_from_id is not None:
            if self.pk and self.mirror_from_id == self.pk:
                raise ValidationError(
                    {"mirror_from": "Una scuola non può mostrare il menu di se stessa."}
                )
            if self.mirror_from.mirror_from_id is not None:
                raise ValidationError(
                    {
                        "mirror_from": "Non puoi selezionare una scuola che a sua volta "
                        "mostra il menu di un'altra scuola."
                    }
                )

    def get_display_school(self) -> School:
        """The school whose settings/meals should actually be rendered (#318)."""
        source = self.mirror_from
        if (
            source is None
            or not source.is_published
            or source.mirror_from_id is not None
        ):
            return self
        return source

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
    def get_json_url(self):  # pragma: no cover
        return reverse("school_menu:get_school_json_menu", kwargs={"slug": self.slug})


class AuditLog(models.Model):
    """Track critical system actions for security and compliance."""

    class Actions(models.TextChoices):
        SCHOOL_CREATE = "SCHOOL_CREATE", _("Scuola creata")
        SCHOOL_UPDATE = "SCHOOL_UPDATE", _("Scuola aggiornata")
        SCHOOL_DELETE = "SCHOOL_DELETE", _("Scuola eliminata")
        MENU_UPLOAD = "MENU_UPLOAD", _("Menu caricato")
        MENU_DELETE = "MENU_DELETE", _("Menu eliminato")
        SETTINGS_CHANGE = "SETTINGS_CHANGE", _("Impostazioni modificate")

    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )
    action = models.CharField(max_length=50, choices=Actions.choices)
    model_name = models.CharField(max_length=100)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    object_repr = models.CharField(max_length=200)
    changes = models.JSONField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=500, blank=True)

    class Meta:
        verbose_name = "registro delle modifiche"
        verbose_name_plural = "registri delle modifiche"
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["-timestamp"], name="audit_timestamp_idx"),
            models.Index(fields=["user", "-timestamp"], name="audit_user_time_idx"),
            models.Index(fields=["action", "-timestamp"], name="audit_action_time_idx"),
        ]

    def __str__(self):
        return f"{self.get_action_display()} - {self.object_repr} ({self.timestamp:%Y-%m-%d %H:%M})"


def menu_import_upload_to(instance, filename):
    """Keep uploads out of the way; the task deletes them right after extraction."""
    return f"menu_imports/{instance.school_id}/{filename}"


class MenuImportDraft(models.Model):
    """An uploaded menu and the rows read out of it — by the AI or by the CSV parser —
    pending user review."""

    class Status(models.TextChoices):
        OFFERED = "OFFERED", _("Proposto")
        PENDING = "PENDING", _("In elaborazione")
        READY = "READY", _("Pronto")
        FAILED = "FAILED", _("Fallito")
        CONFIRMED = "CONFIRMED", _("Confermato")

    class Kinds(models.TextChoices):
        SIMPLE = "S", _("Semplice")
        DETAILED = "D", _("Dettagliato")
        ANNUAL = "A", _("Annuale")

    class Sources(models.TextChoices):
        CSV = "csv", _("CSV")
        AI = "ai", _("Assistente")

    school = models.ForeignKey(
        "School", on_delete=models.CASCADE, related_name="menu_import_drafts"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="menu_import_drafts",
    )
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.OFFERED
    )
    kind = models.CharField(max_length=1, choices=Kinds.choices)
    # Where the rows came from: a CSV upload stages them here too (#254), so the review
    # page is shared and the audit log keeps reporting the real source.
    source = models.CharField(
        max_length=3, choices=Sources.choices, default=Sources.CSV
    )
    meal_type = models.CharField(
        max_length=1, choices=Meal.Types.choices, default=Meal.Types.STANDARD
    )
    season = models.SmallIntegerField(
        choices=Meal.Seasons.choices, null=True, blank=True
    )
    # Holds the uploaded file only between the offer and the end of extraction: menus may
    # carry third-party data, so the task deletes it in a finally block.
    source_file = models.FileField(upload_to=menu_import_upload_to, blank=True)
    source_filename = models.CharField(max_length=255)
    source_size = models.PositiveIntegerField(default=0)
    # Rows use the Italian CSV headers, so confirming rebuilds a tablib Dataset and goes
    # through the very same validation and resources as a CSV upload.
    rows = models.JSONField(default=list, blank=True)
    warnings = models.JSONField(default=list, blank=True)
    error_code = models.CharField(max_length=30, blank=True)
    error_message = models.TextField(blank=True)
    task_id = models.CharField(max_length=32, blank=True)
    usage = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "bozza di importazione"
        verbose_name_plural = "bozze di importazione"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "-created_at"], name="draft_user_created_idx"),
            models.Index(fields=["status", "created_at"], name="draft_status_time_idx"),
            models.Index(fields=["school", "status"], name="draft_school_status_idx"),
        ]

    def __str__(self):
        return f"{self.school.name} - {self.get_status_display()} ({self.created_at:%d/%m/%Y %H:%M})"

    @staticmethod
    def weekly_kind(menu_type):
        """The kind of a weekly import, whatever the school's annual flag says."""
        if menu_type == School.Types.SIMPLE:
            return MenuImportDraft.Kinds.SIMPLE
        return MenuImportDraft.Kinds.DETAILED

    @staticmethod
    def kind_from_school(school):
        """An annual school always imports annual rows, whatever its menu_type says."""
        if school.annual_menu:
            return MenuImportDraft.Kinds.ANNUAL
        return MenuImportDraft.weekly_kind(school.menu_type)

    @property
    def is_annual(self):
        return self.kind == self.Kinds.ANNUAL


class MenuImportQuota(models.Model):
    """Daily AI import counter, per user plus one site-wide bucket (user is null)."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="menu_import_quotas",
    )
    date = models.DateField()
    count = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "quota di importazione"
        verbose_name_plural = "quote di importazione"
        ordering = ["-date"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "date"], name="unique_user_quota_per_day"
            ),
            # SQL treats NULLs as distinct, so the constraint above would happily allow
            # several site-wide rows for the same day and the global cap would leak.
            models.UniqueConstraint(
                fields=["date"],
                condition=models.Q(user__isnull=True),
                name="unique_global_quota_per_day",
            ),
        ]

    def __str__(self):
        owner = self.user.email if self.user else "globale"
        return f"{owner} - {self.date:%d/%m/%Y}: {self.count}"


class MenuHealthCheck(models.Model):
    """Tracks consecutive weeks a published school has gone without a menu (#316).

    Kept out of ``School`` itself so this operational state doesn't bloat the main
    model: it only exists for schools the weekly check has actually flagged at least
    once.
    """

    school = models.OneToOneField(
        School, on_delete=models.CASCADE, related_name="menu_health_check"
    )
    consecutive_missing_weeks = models.PositiveSmallIntegerField(default=0)
    warning_sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "controllo pubblicazione menu"
        verbose_name_plural = "controlli pubblicazione menu"

    def __str__(self):
        return (
            f"{self.school.name}: {self.consecutive_missing_weeks} settimane senza menu"
        )


class MirrorFallbackCheck(models.Model):
    """Tracks whether a mirroring school's owner has already been notified that its
    `mirror_from` source is unpublished (#318)."""

    school = models.OneToOneField(
        School, on_delete=models.CASCADE, related_name="mirror_fallback_check"
    )
    notified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "controllo fallback mirror"
        verbose_name_plural = "controlli fallback mirror"

    def __str__(self):
        status = "attivo" if self.notified_at else "non attivo"
        return f"{self.school.name}: fallback {status}"


class SchoolTransfer(models.Model):
    """A request to take over a school flagged as `seeking_maintainer` (#291).

    `from_user`/`to_user` are always set from the request itself (the current owner,
    the logged-in requester) rather than typed by an admin, so confirming a transfer
    never risks assigning the wrong account.
    """

    class Status(models.TextChoices):
        REQUESTED = "R", "Richiesto"
        COMPLETED = "C", "Effettuato"
        REJECTED = "J", "Rifiutato"

    school = models.ForeignKey(
        School, on_delete=models.CASCADE, related_name="transfers"
    )
    from_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="transfers_given",
    )
    to_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="transfers_requested",
    )
    message = models.TextField(blank=True)
    status = models.CharField(
        max_length=1, choices=Status.choices, default=Status.REQUESTED
    )
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "trasferimento"
        verbose_name_plural = "trasferimenti"
        ordering = ["-created_at"]

    def __str__(self):
        return (
            f"{self.school.name}: {self.from_user} -> {self.to_user} "
            f"({self.get_status_display()})"
        )


@receiver(post_delete, sender=MenuImportDraft)
def delete_menu_import_file(sender, instance, **kwargs):
    """Never leave an uploaded menu behind: it may contain third-party data.

    The task already deletes the file once extraction ends; this covers the drafts that
    are purged, cancelled or removed from the admin before that happens.
    """
    if instance.source_file:
        instance.source_file.delete(save=False)
