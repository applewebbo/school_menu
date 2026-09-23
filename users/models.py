from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

from .managers import UserManager


class User(AbstractUser):
    username = None  # type: ignore[assignment]
    email = models.EmailField(_("email address"), unique=True)
    tc_agreement = models.BooleanField(
        default=False, verbose_name="Termini e condizioni"
    )
    favorite_school = models.ForeignKey(
        "school_menu.School",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="favorited_by",
        verbose_name=_("Scuola preferita"),
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()  # type: ignore[assignment,misc]

    def __str__(self):
        return self.email

    def clean(self):
        super().clean()
        if self.favorite_school_id and hasattr(self, "school"):
            if self.favorite_school_id == self.school.id:
                raise ValidationError(
                    {"favorite_school": _("Non puoi preferire la tua scuola.")}
                )
