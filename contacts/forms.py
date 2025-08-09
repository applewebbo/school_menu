from crispy_forms.helper import FormHelper
from crispy_forms.layout import Div, Layout
from django import forms

from contacts.models import MenuReport


class ContactForm(forms.Form):
    name = forms.CharField(
        max_length=100,
        label="Nome",
        widget=forms.TextInput(),
    )
    email = forms.EmailField(
        label="Indirizzo email",
        widget=forms.EmailInput(),
    )
    message = forms.CharField(
        widget=forms.Textarea(attrs={"placeholder": "Scrivi un messaggio"}),
        label="",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Div(
                "name",
                "email",
                "message",
            ),
        )


class MenuReportForm(forms.ModelForm):
    name = forms.CharField(
        max_length=100,
        label="Nome",
        widget=forms.TextInput(attrs={"class": "input w-full"}),
    )
    message = forms.CharField(
        widget=forms.Textarea(
            attrs={"placeholder": "Messaggio", "class": "textarea w-full"}
        ),
        label="",
    )
    get_notified = forms.BooleanField(
        required=False,
        label="Voglio essere ricontattato",
        help_text="Vuoi ricevere informazioni sulla risoluzione del problema segnalato da chi ha creato il menu?",
    )
    email = forms.EmailField(
        label="Indirizzo email",
        required=False,
        widget=forms.EmailInput(attrs={"class": "input w-full"}),
    )

    class Meta:
        model = MenuReport
        fields = ["name", "message", "get_notified", "email"]

    def clean(self):
        """Validate email field as required only if get_notified is True"""
        cleaned_data = super().clean()
        get_notified = cleaned_data.get("get_notified")
        email = cleaned_data.get("email")
        if get_notified and not email:
            self.add_error(
                "email", "Se vuoi essere ricontattato devi inserire un indirizzo email"
            )
        return cleaned_data

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Div(
                "name",
                "message",
                "get_notified",
                "email",
            ),
        )


class ReportFeedbackForm(forms.Form):
    message = forms.CharField(
        widget=forms.Textarea(
            attrs={"placeholder": "Messaggio", "class": "textarea w-full"}
        ),
        label="",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Div(
                "message",
            ),
        )
