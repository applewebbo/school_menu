from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _

from .managers import UserManager


class User(AbstractUser):
    username = None  # type: ignore[assignment]
    email = models.EmailField(_("email address"), unique=True)
    tc_agreement = models.BooleanField(
        default=False, verbose_name="Termini e condizioni"
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()  # type: ignore[assignment,misc]

    def __str__(self):
        return self.email
