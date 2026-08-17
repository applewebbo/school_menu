"""
Helpers to drive the shared import review page from the tests (#254).

A CSV upload no longer writes meals: it stages the rows on a draft and sends the user to
the review page. Tests that care about what ends up in the database therefore have to go
through `confirm_import` after uploading, exactly as the browser does.
"""

from django.urls import reverse

from school_menu.menu_import_views import COLUMNS
from school_menu.models import MenuImportDraft


def staged_draft(school):
    """The review draft the upload has just staged for this school."""
    return MenuImportDraft.objects.get(
        school=school, status=MenuImportDraft.Status.READY
    )


def confirm_payload(draft, *, deleted=(), overrides=None):
    """Build what the review form posts for the rows currently on the draft."""
    columns = COLUMNS[draft.kind]
    data = {
        "form-TOTAL_FORMS": str(len(draft.rows)),
        "form-INITIAL_FORMS": str(len(draft.rows)),
        "form-MIN_NUM_FORMS": "0",
        "form-MAX_NUM_FORMS": "1000",
    }
    for index, row in enumerate(draft.rows):
        for column in columns:
            data[f"form-{index}-{column}"] = row.get(column, "")
        for column, value in (overrides or {}).get(index, {}).items():
            data[f"form-{index}-{column}"] = value
        # "Includi" is ticked by default in the browser; an unticked box posts nothing.
        if index not in deleted:
            data[f"form-{index}-includi"] = "on"
    return data


def confirm_import(client, school, **kwargs):
    """Post the staged rows back, as the review page's own form does."""
    draft = staged_draft(school)
    return client.post(
        reverse("school_menu:menu_import_confirm", args=[draft.pk]),
        data=confirm_payload(draft, **kwargs),
    )
