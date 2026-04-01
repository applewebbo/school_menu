from crispy_forms.helper import FormHelper
from django import forms
from django.db import models as db_models

from school_menu.models import Meal, School

from .models import AnonymousMenuNotification


class AnonymousMenuNotificationForm(forms.ModelForm):
    class Meta:
        model = AnonymousMenuNotification
        fields = ["school", "meal_type", "notification_time", "subscription_info"]
        widgets = {
            "subscription_info": forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.fields["school"].label = "Scuola"
        self.fields["school"].queryset = School.objects.filter(
            is_published=True
        ).order_by("name")
        self.fields["school"].label_from_instance = lambda obj: obj.name
        self.fields["school"].empty_label = None
        self.fields["notification_time"].label = "Orario di notifica"
        self.fields["meal_type"].label = "Tipo di menu"
        self.fields["meal_type"].required = False
        self.fields["meal_type"].initial = Meal.Types.STANDARD

        # If editing an existing subscription with a known school, filter choices
        if self.instance and self.instance.pk and self.instance.school_id:
            choices = self._build_meal_type_choices(self.instance.school)
            self.fields["meal_type"].choices = choices
            if len(choices) <= 1:
                self.fields["meal_type"].widget = forms.HiddenInput()

    @staticmethod
    def _build_meal_type_choices(school):
        choices = [(Meal.Types.STANDARD, Meal.Types.STANDARD.label)]
        if school.no_gluten:
            choices.append((Meal.Types.GLUTEN_FREE, Meal.Types.GLUTEN_FREE.label))
        if school.no_lactose:
            choices.append((Meal.Types.LACTOSE_FREE, Meal.Types.LACTOSE_FREE.label))
        if school.vegetarian:
            choices.append((Meal.Types.VEGETARIAN, Meal.Types.VEGETARIAN.label))
        if school.special:
            choices.append((Meal.Types.SPECIAL, Meal.Types.SPECIAL.label))
        return choices

    @staticmethod
    def get_schools_with_alt_menus():
        """Return a list of school IDs that have at least one alternative menu type."""
        return list(
            School.objects.filter(is_published=True)
            .filter(
                db_models.Q(no_gluten=True)
                | db_models.Q(no_lactose=True)
                | db_models.Q(vegetarian=True)
                | db_models.Q(special=True)
            )
            .values_list("id", flat=True)
        )
