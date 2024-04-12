from crispy_forms.helper import FormHelper
from django import forms

from school_menu.models import School, Settings


class SchoolForm(forms.ModelForm):
    class Meta:
        model = School
        fields = ["name", "city"]
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "block w-full p-2 text-gray-900 border border-gray-300 rounded-lg bg-gray-50 text-sm focus:ring-green-500 focus:border-green-500 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white dark:focus:ring-green-500 dark:focus:border-green-500"
                }
            ),
            "city": forms.TextInput(
                attrs={
                    "class": "block w-full p-2 text-gray-900 border border-gray-300 rounded-lg bg-gray-50 text-sm focus:ring-green-500 focus:border-green-500 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white dark:focus:ring-green-500 dark:focus:border-green-500"
                }
            ),
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
        help_texts = {
            "week_bias": "Numero di settimane da saltare",
        }
        error_messages = {
            "week_bias": {
                "max_value": "Il valore massimo è 3",
            },
        }
