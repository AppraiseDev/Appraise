"""
Appraise evaluation framework

See LICENSE for usage details
"""
from django.contrib import messages
from django.contrib.auth.decorators import (
    login_required,
    permission_required,
)
from django.http import HttpResponseRedirect

# pylint: disable=unused-import
from django.shortcuts import get_object_or_404, render
from django.urls import reverse

from .models import TaskAgenda


@login_required
@permission_required("EvalData.reset_taskagenda")
def reset_taskagenda(request, agenda_id):
    """
    Attempts to reset the TaskAgenda matching the given pk.

    Only possible for users who:
    1) are logged in;
    2) are staff members; and
    3) have reset_taskagenda permission.

    Redirects back to TaskAgenda changelist when done.
    """
    _obj = get_object_or_404(TaskAgenda, pk=agenda_id)

    # This will return triple with a status message and level.
    _ret, _msg, _lvl = _obj.reset_taskagenda()
    messages.add_message(request, _lvl, _msg)

    return HttpResponseRedirect(
        reverse('admin:EvalData_taskagenda_changelist')
    )
