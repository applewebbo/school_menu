from crispy_forms.helper import FormHelper
from django import forms

from school_menu.models import School

from .models import AnonymousMenuNotification


class AnonymousMenuNotificationForm(forms.ModelForm):
    class Meta:
        model = AnonymousMenuNotification
        fields = ["school", "subscription_info"]
        widgets = {"subscription_info": forms.HiddenInput()}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.fields["school"].label = False
        self.fields["school"].queryset = School.objects.filter(is_published=True)
        self.fields["school"].label_from_instance = lambda obj: obj.name
