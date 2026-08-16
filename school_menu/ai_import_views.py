"""
Views driving the AI menu import (#234).

The flow is: the upload modal offers a draft (`OFFERED`), `start` charges the quota and
queues it (`PENDING`), `status` is polled until the draft is `READY` or `FAILED`, the
preview lets the user fix what the AI got wrong, and `confirm` sends the corrected rows
through the very same import path a CSV upload uses.

Every draft is looked up with `user=request.user`, so a draft belonging to somebody else
is a 404 rather than a leak: uploaded menus can carry third-party data.
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.views.decorators.http import require_http_methods
from tablib import Dataset

from school_menu.forms import UploadAnnualMenuForm, UploadMenuForm, ai_row_formset
from school_menu.models import MenuImportDraft
from school_menu.services import ai_quota
from school_menu.services.menu_import import (
    import_annual_dataset,
    import_weekly_dataset,
)
from school_menu.tasks import queue_menu_import
from school_menu.utils import validate_annual_dataset, validate_dataset

STATUS_TEMPLATE = "partials/ai-import-status.html"
PREVIEW_TEMPLATE = "ai-import-preview.html"

# Column order per kind, and the order the preview table renders them in.
COLUMNS = {
    MenuImportDraft.Kinds.SIMPLE: [
        "giorno",
        "settimana",
        "pranzo",
        "spuntino",
        "merenda",
    ],
    MenuImportDraft.Kinds.DETAILED: [
        "giorno",
        "settimana",
        "primo",
        "secondo",
        "contorno",
        "frutta",
        "spuntino",
    ],
    MenuImportDraft.Kinds.ANNUAL: [
        "data",
        "primo",
        "secondo",
        "contorno",
        "frutta",
        "altro",
    ],
}


def _get_draft(request, draft_id, **filters):
    return get_object_or_404(MenuImportDraft, pk=draft_id, user=request.user, **filters)


def _status_response(request, draft):
    return TemplateResponse(
        request,
        STATUS_TEMPLATE,
        {"draft": draft, "remaining": ai_quota.remaining(request.user)},
    )


@login_required
@require_http_methods(["POST"])
def ai_import_start(request: HttpRequest, draft_id: int) -> HttpResponse:
    """Charge the quota and hand the already uploaded file to the worker."""
    draft = _get_draft(request, draft_id, status=MenuImportDraft.Status.OFFERED)
    try:
        queue_menu_import(draft)
    except ai_quota.QuotaExceeded as exceeded:
        # The draft stays OFFERED: the file is still there if the user retries tomorrow,
        # and the CSV route is still open in the meantime.
        return TemplateResponse(
            request,
            STATUS_TEMPLATE,
            {"draft": draft, "quota_message": str(exceeded), "remaining": 0},
        )
    draft.refresh_from_db()
    return _status_response(request, draft)


@login_required
def ai_import_status(request: HttpRequest, draft_id: int) -> HttpResponse:
    """Polled while the extraction runs; stops polling as soon as it is over."""
    draft = _get_draft(request, draft_id)
    return _status_response(request, draft)


@login_required
@require_http_methods(["POST"])
def ai_import_cancel(request: HttpRequest, draft_id: int) -> HttpResponse:
    """
    Give up on the draft and hand back the plain upload modal.

    Not a page refresh: while the assistant is on offer the upload form is hidden, so this
    is the way back to it — the user gets the fields again and can try another file. The
    draft goes, and the uploaded file with it.
    """
    draft = _get_draft(request, draft_id)
    school, meal_type = draft.school, draft.meal_type
    draft.delete()
    return TemplateResponse(
        request,
        "upload-menu.html",
        {
            "form": UploadAnnualMenuForm() if school.annual_menu else UploadMenuForm(),
            "school": school,
            "active_menu": meal_type,
            "ai_draft": None,
        },
    )


def _initial_rows(draft):
    columns = COLUMNS[draft.kind]
    return [{column: row.get(column, "") for column in columns} for row in draft.rows]


# The short fields that say which row this is, as opposed to the menu text itself.
KEY_COLUMNS = {"giorno", "settimana", "data"}


def _row_title(form, kind, index):
    """
    Name the card so the user can find the row they want to fix.

    Built from the values currently in the form, not from the draft, so it still reads
    correctly after a failed confirm re-renders the submitted data.
    """
    if kind == MenuImportDraft.Kinds.ANNUAL:
        return form["data"].value() or f"Riga {index}"
    day = form["giorno"].value() or f"Riga {index}"
    week = form["settimana"].value()
    return f"{day} · Settimana {week}" if week else day


def _preview_context(draft, formset):
    """
    Pair every form with its labelled fields, in column order.

    Done here rather than in the template: looking a field up by name from a template
    needs a filter that adds nothing. Each field appears exactly once — a second copy for
    a different breakpoint would post twice and quietly overwrite the first (#239).
    """
    columns = COLUMNS[draft.kind]
    return {
        "draft": draft,
        "formset": formset,
        "preview_rows": [
            {
                "form": form,
                "title": _row_title(form, draft.kind, index),
                # Split so the short identifying fields can sit side by side in the card
                # and the menu text gets the full width it needs.
                "key_fields": [
                    (column.capitalize(), form[column])
                    for column in columns
                    if column in KEY_COLUMNS
                ],
                "menu_fields": [
                    (column.capitalize(), form[column])
                    for column in columns
                    if column not in KEY_COLUMNS
                ],
            }
            for index, form in enumerate(formset, start=1)
        ],
        "school": draft.school,
    }


@login_required
def ai_import_preview(request: HttpRequest, draft_id: int) -> HttpResponse:
    """Show what the AI read, so the user can correct it before anything is saved."""
    draft = _get_draft(request, draft_id, status=MenuImportDraft.Status.READY)
    formset = ai_row_formset(draft.kind)(initial=_initial_rows(draft))
    return TemplateResponse(request, PREVIEW_TEMPLATE, _preview_context(draft, formset))


def _dataset_from(formset, columns):
    """Rebuild the CSV shape from the corrected rows, deletions excluded."""
    dataset = Dataset()
    dataset.headers = columns
    for form in formset.forms:
        if not form.cleaned_data.get("includi"):
            continue
        dataset.append([str(form.cleaned_data.get(column, "")) for column in columns])
    return dataset


@login_required
@require_http_methods(["POST"])
def ai_import_confirm(request: HttpRequest, draft_id: int) -> HttpResponse:
    """
    Import the corrected rows.

    They go through `validate_dataset` and the same resources as a CSV upload: the AI
    path must not be able to write anything a CSV upload could not.
    """
    draft = _get_draft(request, draft_id, status=MenuImportDraft.Status.READY)
    columns = COLUMNS[draft.kind]
    formset = ai_row_formset(draft.kind)(request.POST, initial=_initial_rows(draft))
    context = _preview_context(draft, formset)
    if not formset.is_valid():
        return TemplateResponse(request, PREVIEW_TEMPLATE, context)

    dataset = _dataset_from(formset, columns)
    if not dataset.height:
        context["error_message"] = "Non è rimasta nessuna riga da importare."
        return TemplateResponse(request, PREVIEW_TEMPLATE, context)

    if draft.is_annual:
        validates, message, filtered = validate_annual_dataset(dataset)
    else:
        validates, message, filtered = validate_dataset(dataset, draft.school.menu_type)
    if not validates:
        context["error_message"] = message
        return TemplateResponse(request, PREVIEW_TEMPLATE, context)

    if draft.is_annual:
        imported = import_annual_dataset(
            request, draft.school, filtered, draft.meal_type, source="ai"
        )
    else:
        imported = import_weekly_dataset(
            request, draft.school, filtered, draft.season, draft.meal_type, source="ai"
        )
    if not imported:  # pragma: no cover
        # Same reason as menu_import._log_failure: django-import-export only reports row
        # errors for rows the validation above has already rejected.
        context["error_message"] = "Qualcosa è andato storto durante l'importazione."
        return TemplateResponse(request, PREVIEW_TEMPLATE, context)

    draft.status = MenuImportDraft.Status.CONFIRMED
    draft.save(update_fields=["status", "updated_at"])
    request.session["active_menu"] = draft.meal_type
    messages.add_message(request, messages.SUCCESS, "Menu importato con successo")
    # The preview is a full page posting a plain form, so it needs a real redirect: an
    # HX-Redirect header would be ignored and the user would sit on a stale page whose
    # draft is already CONFIRMED, making the next click a 404 (#250).
    return redirect("school_menu:settings")
