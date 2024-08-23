from contacts.forms import ContactForm


class TestContactForm:
    def test_form(self):
        form = ContactForm(
            data={
                "name": "Test Name",
                "email": "test@test.com",
                "message": "Test Message",
            }
        )

        assert form.is_valid() is True

    def test_form_no_data(self):
        form = ContactForm(data={})

        assert form.is_valid() is False
        assert form.errors == {
            "name": ["Questo campo è obbligatorio."],
            "email": ["Questo campo è obbligatorio."],
            "message": ["Questo campo è obbligatorio."],
        }
