from crispy_forms.helper import FormHelper
from crispy_forms.layout import Div, Layout
from django import forms

from contacts.models import MenuReport


class HoneypotMixin(forms.Form):
    """
    Hidden `website` field (#292): invisible to real visitors via CSS, but a bot that
    blindly fills every `<input>` on the page populates it, so any value here means the
    submission wasn't a human. Same technique already used on signup (#272).

    Must inherit from `forms.Form` (not just `object`): Django's form metaclass only
    collects declared fields from base classes that went through it themselves, so a
    plain mixin's fields are silently dropped.
    """

    website = forms.CharField(
        required=False,
        label="",
        widget=forms.TextInput(
            attrs={"autocomplete": "off", "tabindex": "-1", "aria-hidden": "true"}
        ),
    )

    def clean_website(self):
        if self.cleaned_data.get("website"):
            raise forms.ValidationError("Invio non disponibile al momento.")
        return self.cleaned_data.get("website")


class ContactForm(HoneypotMixin):
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
        label="Messaggio",
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
                Div("website", css_class="absolute -left-[9999px]"),
            ),
        )


class MenuReportForm(HoneypotMixin, forms.ModelForm):
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
                Div("website", css_class="absolute -left-[9999px]"),
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
