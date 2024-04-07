from django import forms

from school_menu.models import School, Settings


class SchoolForm(forms.ModelForm):
    class Meta:
        model = School
        fields = ["name", "city"]
        labels = {
            "name": "Nome",
            "city": "Città",
        }


class SettingsForm(forms.ModelForm):
    class Meta:
        model = Settings
        fields = ["season_choice", "week_bias"]
        labels = {
            "season_choice": "Stagione",
            "week_bias": "Scarto",
        }
        help_texts = {
            "week_bias": "Numero di settimane da saltare",
        }
        error_messages = {
            "week_bias": {
                "max_value": "Il valore massimo è 3",
            },
        }
