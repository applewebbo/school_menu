from crispy_forms.helper import FormHelper
from django import forms

from school_menu.models import School


class AnonymousMenuNotificationForm(forms.Form):
    school = forms.ModelChoiceField(
        queryset=School.objects.all(), required=True, label="Seleziona la scuola"
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.fields["school"].label = False
        self.fields["school"].label_from_instance = lambda obj: obj.name
