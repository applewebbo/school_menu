from contacts.forms import ContactForm, MenuReportForm, ReportFeedbackForm


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
            "name": ["Campo obbligatorio."],
            "email": ["Campo obbligatorio."],
            "message": ["Campo obbligatorio."],
        }


class TestMenuReportForm:
    def test_form(self):
        form = MenuReportForm(
            data={
                "name": "Test Name",
                "message": "Test Message",
                "get_notified": False,
            }
        )

        assert form.is_valid() is True

    def test_form_with_no_email(self):
        form = MenuReportForm(
            data={
                "name": "Test Name",
                "message": "Test Message",
                "get_notified": True,
            }
        )

        assert form.is_valid() is False
        assert form.errors == {
            "email": ["Se vuoi essere ricontattato devi inserire un indirizzo email"],
        }


class TestReportFeedbackForm:
    def test_form(self):
        form = ReportFeedbackForm(
            data={
                "message": "Test Message",
            }
        )

        assert form.is_valid() is True
