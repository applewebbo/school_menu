from crispy_forms.helper import FormHelper
from crispy_forms.layout import Div, Layout
from django import forms

from school_menu.models import School


class SchoolForm(forms.ModelForm):
    class Meta:
        model = School
        fields = ["name", "city", "season_choice", "week_bias", "menu_type"]
        widgets = {
            "season_choice": forms.Select(attrs={"class": "form-select"}),
            "week_bias": forms.NumberInput(),
            "menu_type": forms.Select(attrs={"class": "form-select"}),
        }
        labels = {
            "name": "Nome",
            "city": "Città",
            "season_choice": "Stagione",
            "week_bias": "Scarto",
            "menu_type": "Tipo di Menù",
        }
        error_messages = {
            "week_bias": {
                "max_value": "Il valore massimo è 3",
            },
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Div(
                Div(
                    "name",
                    "city",
                ),
                Div(
                    "season_choice",
                    "week_bias",
                    "menu_type",
                ),
                css_class="grid grid-cols-1 md:grid-cols-2 md:gap-4",
            ),
        )
