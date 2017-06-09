# pylint: disable=C0330
import logging

from collections import defaultdict
from datetime import datetime
from hashlib import md5
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AdminPasswordChangeForm
from django.contrib.auth.views import password_change
from django.contrib.auth.models import User, Group
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.shortcuts import render, reverse, redirect, render_to_response

from Appraise.settings import LOG_LEVEL, LOG_HANDLER, STATIC_URL, BASE_CONTEXT
from EvalData.models import DirectAssessmentTask, DirectAssessmentResult
from .models import UserInviteToken, LANGUAGE_CODES_AND_NAMES


# Setup logging support.
logging.basicConfig(level=LOG_LEVEL)
LOGGER = logging.getLogger('Dashboard.views')
LOGGER.addHandler(LOG_HANDLER)


HITS_REQUIRED_BEFORE_ENGLISH_ALLOWED = 5

# HTTP error handlers supporting COMMIT_TAG.
def _page_not_found(request, template_name='404.html'):
    """Custom HTTP 404 handler that preserves URL_PREFIX."""
    LOGGER.info('Rendering HTTP 404 for user "{0}". Request.path={1}'.format(
      request.user.username or "Anonymous", request.path))

    return render_to_response('Dashboard/404.html', BASE_CONTEXT)


def _server_error(request, template_name='500.html'):
    """Custom HTTP 500 handler that preserves URL_PREFIX."""
    LOGGER.info('Rendering HTTP 500 for user "{0}". Request.path={1}'.format(
      request.user.username or "Anonymous", request.path))

    return render_to_response('Dashboard/500.html', BASE_CONTEXT)

def frontpage(request, extra_context=None):
    """
    Appraise front page.
    """
    LOGGER.info('Rendering frontpage view for user "{0}".'.format(
      request.user.username or "Anonymous"))

    context = {
      'active_page': 'frontpage'
    }
    context.update(BASE_CONTEXT)
    if extra_context:
        context.update(extra_context)

    return render(request, 'Dashboard/frontpage.html', context)

def create_profile(request):
    """
    Renders the create profile view.
    """
    errors = None
    username = None
    email = None
    token = None
    languages = []
    language_choices = [x for x in LANGUAGE_CODES_AND_NAMES.items()]
    language_choices.sort(key=lambda x: x[1])

    focus_input = 'id_username'

    if request.method == "POST":
        username = request.POST.get('username', None)
        email = request.POST.get('email', None)
        token = request.POST.get('token', None)
        languages = request.POST.getlist('languages', None)

        if username and email and token and languages:
            try:
                # Check if given invite token is still active.
                invite = UserInviteToken.objects.filter(token=token)
                if not invite.exists() or not invite[0].active:
                    raise ValueError('invalid_token')

                # We now have a valid invite token...
                invite = invite[0]

                # Check if desired username is already in use.
                current_user = User.objects.filter(username=username)
                if current_user.exists():
                    raise ValueError('invalid_username')

                # Compute set of evaluation languages for this user.
                eval_groups = []
                for code in languages:
                    language_group = Group.objects.filter(name=code)
                    if language_group.exists():
                        eval_groups.extend(language_group)

                # Create new user account and add to group.
                password = '{0}{1}'.format(
                  invite.group.name[:2].upper(),
                  md5(invite.group.name.encode('utf-8')).hexdigest()[:8]
                )
                user = User.objects.create_user(username, email, password)

                # Update group settings for the new user account.
                user.groups.add(invite.group)
                for eval_group in eval_groups:
                    user.groups.add(eval_group)

                user.save()

                # Disable invite token and attach to current user.
                invite.active = False
                invite.user = user
                invite.save()

                # Login user and redirect to dashboard page.
                user = authenticate(username=username, password=password)
                login(request, user)
                return redirect('dashboard')

            # For validation errors, invalidate the respective value.
            except ValueError as issue:
                if issue.args[0] == 'invalid_username':
                    username = None

                elif issue.args[0] == 'invalid_token':
                    token = None

                else:
                    username = None
                    email = None
                    token = None
                    languages = None

            # For any other exception, clean up and ask user to retry.
            except:
                from traceback import format_exc
                print(format_exc()) # TODO: need logger here!
                username = None
                email = None
                token = None
                languages = None

        # Detect which input should get focus for next page rendering.
        if not username:
            focus_input = 'id_username'
            errors = ['invalid_username']

        elif not email:
            focus_input = 'id_email'
            errors = ['invalid_email']

        elif not token:
            focus_input = 'id_token'
            errors = ['invalid_token']

        elif not languages:
            focus_input = 'id_languages'
            errors = ['invalid_languages']

    context = {
      'active_page': "OVERVIEW", # TODO: check
      'errors': errors,
      'focus_input': focus_input,
      'username': username,
      'email': email,
      'token': token,
      'languages': languages,
      'language_choices': language_choices,
      'title': 'Create profile',
    }
    context.update(BASE_CONTEXT)

    return render(request, 'Dashboard/create-profile.html', context)

@login_required
def update_profile(request):
    """
    Renders the profile update view.
    """
    errors = None
    languages = set()
    language_choices = [x for x in LANGUAGE_CODES_AND_NAMES.items()]
    language_choices.sort(key=lambda x: x[1])
    focus_input = 'id_projects'

    if request.method == "POST":
        languages = set(request.POST.getlist('languages', None))
        if languages:
            try:
                # Compute set of evaluation languages for this user.
                for code, _ in language_choices:
                    language_group = Group.objects.filter(name=code)
                    if language_group.exists():
                        language_group = language_group[0]
                        if code in languages:
                            language_group.user_set.add(request.user)
                        else:
                            language_group.user_set.remove(request.user)
                        language_group.save()

                # Redirect to dashboard.
                return redirect('dashboard')

            # For any other exception, clean up and ask user to retry.
            except:
                from traceback import format_exc
                print(format_exc())

                languages = set()

        # Detect which input should get focus for next page rendering.
        if not languages:
            focus_input = 'id_languages'
            errors = ['invalid_languages']

    # Determine user target languages
    for group in request.user.groups.all():
        if group.name.lower() in [x.lower() for x in LANGUAGE_CODES_AND_NAMES.keys()]:
            languages.add(group.name.lower())

    context = {
      'active_page': "OVERVIEW",
      'errors': errors,
      'focus_input': focus_input,
      'languages': languages,
      'language_choices': language_choices,
      'title': 'Update profile',
    }
    context.update(BASE_CONTEXT)

    return render(request, 'Dashboard/update-profile.html', context)

@login_required
def dashboard(request):
    """
    Appraise dashboard page.
    """
    t1 = datetime.now()

    context = {
      'active_page': 'dashboard'
    }
    context.update(BASE_CONTEXT)

    annotations = DirectAssessmentResult.get_completed_for_user(request.user)
    hits = int(annotations/100)

    # If user still has an assigned task, only offer link to this task.
    current_task = DirectAssessmentTask.get_task_for_user(request.user)
    t2 = datetime.now()

    # Otherwise, compute set of language codes eligible for next task.
    languages = []
    if not current_task:
        for code in LANGUAGE_CODES_AND_NAMES:
            if request.user.groups.filter(name=code).exists():
                if not code in languages:
                    languages.append(code)

        if hits < HITS_REQUIRED_BEFORE_ENGLISH_ALLOWED:
            if len(languages) > 1 and 'eng' in languages:
                languages.remove('eng')

        # Remove any language for which no free task is available.
        for code in languages:
            next_task_available = DirectAssessmentTask.get_next_free_task_for_language(code)
            if not next_task_available:
                languages.remove(code)

        print("languages = {0}".format(languages))

    t3 = datetime.now()

    duration = DirectAssessmentResult.get_time_for_user(request.user)
    days = duration.days
    hours = int((duration.total_seconds() - (days * 86400)) / 3600)
    minutes = int(((duration.total_seconds() - (days * 86400)) % 3600) / 60)
    seconds = int((duration.total_seconds() - (days * 86400)) % 60)

    t4 = datetime.now()

    context.update({
      'annotations': annotations,
      'hits': hits,
      'days': days,
      'hours': hours,
      'minutes': minutes,
      'seconds': seconds,
      'current_task': current_task,
      'languages': [(x, LANGUAGE_CODES_AND_NAMES[x]) for x in languages],
      'debug_times': (t2-t1, t3-t2, t4-t3, t4-t1),
      'template_debug': 'debug' in request.GET,
    })

    return render(request, 'Dashboard/dashboard.html', context)


@login_required
def group_status(request):
    """
    Appraise group status page.
    """
    t1 = datetime.now()

    context = {
      'active_page': 'group-status'
    }
    context.update(BASE_CONTEXT)

    group_data = defaultdict(int)
    t2 = datetime.now()
    qs = DirectAssessmentTask.objects.filter(completed=True)
    for group_name in qs.values_list('assignedTo__groups__name', flat=True):
        #for user in completed_task.all(): #.assignedTo.all():
        #    for group in user.groups.all():
        if not group_name in LANGUAGE_CODES_AND_NAMES.keys():
            group_data[group_name] += 1
    t3 = datetime.now()

    group_status = []
    for group in group_data:
        group_status.append((group, group_data[group]))

    sorted_status = sorted(group_status, key=lambda x: x[1], reverse=True)
    t4 = datetime.now()

    context.update({
      'group_status': list(sorted_status),
      'total_completed': sum(group_data.values()),
      'debug_times': (t2-t1, t3-t2, t4-t3, t4-t1),
      'template_debug': 'debug' in request.GET,
    })

    return render(request, 'Dashboard/group-status.html', context)


@login_required
def system_status(request):
    """
    Appraise system status page.
    """
    t1 = datetime.now()

    context = {
      'active_page': 'system-status'
    }
    context.update(BASE_CONTEXT)

    t2 = datetime.now()
    system_data = DirectAssessmentResult.get_system_status(sort_index=1)
    t3 = datetime.now()
    sorted_status = []
    total_completed = 0
    for code in system_data:
        if not system_data[code]:
            continue

        for data in system_data[code]:
            sorted_status.append((code, data[0], data[1]))
            total_completed += data[1]

    t4 = datetime.now()
    context.update({
      'system_status': sorted_status,
      'total_completed': total_completed,
      'debug_times': (t2-t1, t3-t2, t4-t3, t4-t1),
      'template_debug': 'debug' in request.GET,
    })

    return render(request, 'Dashboard/system-status.html', context)
