from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout
from django import forms

from school_menu.models import School, Settings


class SchoolForm(forms.ModelForm):
    class Meta:
        model = School
        fields = ["name", "city"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "input-small"}),
            "city": forms.TextInput(attrs={"class": "input-small"}),
        }
        labels = {
            "name": "Nome",
            "city": "Città",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.form_show_labels = False


class SettingsForm(forms.ModelForm):
    class Meta:
        model = Settings
        fields = ["season_choice", "week_bias"]
        labels = {
            "season_choice": "Stagione",
            "week_bias": "Scarto",
        }
        widgets = {
            "season_choice": forms.Select(attrs={"class": "form-select"}),
            "week_bias": forms.NumberInput(attrs={"class": "input-small"}),
        }
        help_texts = {
            "week_bias": "Numero di settimane da saltare",
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
        self.helper.form_show_labels = False
        self.helper.layout = Layout(
            "season_choice",
            "week_bias",
        )
