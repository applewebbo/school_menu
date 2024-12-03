import pytest

pytestmark = pytest.mark.django_db


class TestMenuReportModel:
    def test_factory(self, user_factory, menu_report_factory):
        user = user_factory()
        menu_report = menu_report_factory(receiver=user)

        assert menu_report.__str__() == f"Segnalazione da {menu_report.name}"
