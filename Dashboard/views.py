"""
Appraise evaluation framework

See LICENSE for usage details
"""
from datetime import datetime
from hashlib import md5
from inspect import currentframe, getframeinfo

# pylint: disable=import-error,C0330
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User, Group
from django.contrib.auth import authenticate, login
from django.shortcuts import render, redirect, render_to_response

from Appraise.settings import BASE_CONTEXT
from Appraise.utils import _get_logger
from Dashboard.models import UserInviteToken, LANGUAGE_CODES_AND_NAMES
from EvalData.models import (
    DirectAssessmentTask,
    DirectAssessmentResult,
    DirectAssessmentContextTask,
    DirectAssessmentContextResult,
    MultiModalAssessmentTask,
    MultiModalAssessmentResult,
    TaskAgenda,
)

from deprecated import add_deprecated_method


HITS_REQUIRED_BEFORE_ENGLISH_ALLOWED = 5

# HTTP error handlers supporting COMMIT_TAG.
def _page_not_found(request, template_name='404.html'):
    """
    Custom HTTP 404 handler that preserves URL_PREFIX.
    """
    del template_name  # Unused.

    LOGGER = _get_logger(name=__name__)

    LOGGER.info(
        'Rendering HTTP 404 for user "%s". Request.path=%s',
        request.user.username or "Anonymous",
        request.path,
    )

    return render_to_response('Dashboard/404.html', BASE_CONTEXT)


def _server_error(request, template_name='500.html'):
    """
    Custom HTTP 500 handler that preserves URL_PREFIX.
    """
    del template_name  # Unused.

    LOGGER = _get_logger(name=__name__)

    LOGGER.info(
        'Rendering HTTP 500 for user "%s". Request.path=%s',
        request.user.username or "Anonymous",
        request.path,
    )

    return render_to_response('Dashboard/500.html', BASE_CONTEXT)


def sso_login(request, username, password):
    """
    Attempts SSO login for the given username:password credentials.
    """
    # Login user and redirect to dashboard page.
    if not request.user.username:
        user = authenticate(username=username, password=password)
        login(request, user)

    LOGGER = _get_logger(name=__name__)

    LOGGER.info(
        'Rendering SSO login view for user "%s".',
        request.user.username or "Anonymous",
    )

    return redirect('dashboard')


def frontpage(request, extra_context=None):
    """
    Appraise front page.
    """
    LOGGER = _get_logger(name=__name__)

    LOGGER.info(
        'Rendering frontpage view for user "%s".',
        request.user.username or "Anonymous",
    )

    context = {'active_page': 'frontpage'}
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
                    md5(invite.group.name.encode('utf-8')).hexdigest()[:8],
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
            except Exception:
                from traceback import format_exc

                print(format_exc())  # TODO: need logger here!
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
        'active_page': "OVERVIEW",  # TODO: check
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
            except Exception:
                from traceback import format_exc

                print(format_exc())

                languages = set()

        # Detect which input should get focus for next page rendering.
        if not languages:
            focus_input = 'id_languages'
            errors = ['invalid_languages']

    # Determine user target languages
    for group in request.user.groups.all():
        if group.name.lower() in [
            x.lower() for x in LANGUAGE_CODES_AND_NAMES
        ]:
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
    _t1 = datetime.now()

    LOGGER = _get_logger(name=__name__)

    template_context = {'active_page': 'dashboard'}
    template_context.update(BASE_CONTEXT)

    result_types = (
        DirectAssessmentResult,
        DirectAssessmentContextResult,
        MultiModalAssessmentResult,
    )
    annotations = 0
    hits = 0
    total_hits = 0
    for result_cls in result_types:
        annotations += result_cls.get_completed_for_user(request.user)
        _hits, _total = result_cls.get_hit_status_for_user(request.user)
        hits, total_hits = hits + _hits, total_hits + _total

    # If user still has an assigned task, only offer link to this task.
    current_task = DirectAssessmentTask.get_task_for_user(request.user)

    # Check if marketTargetLanguage for current_task matches user languages.
    if current_task:
        code = current_task.marketTargetLanguageCode()
        print(request.user.groups.all())
        if code not in request.user.groups.values_list('name', flat=True):
            _msg = (
                'Language %s not specified for user %s. Giving up task %s'
            )
            LOGGER.info(_msg, code, request.user.username, current_task)

            current_task.assignedTo.remove(request.user)
            current_task = None

    if not current_task:
        current_task = DirectAssessmentContextTask.get_task_for_user(
            request.user
        )

    # Check if marketTargetLanguage for current_task matches user languages.
    if current_task:
        code = current_task.marketTargetLanguageCode()
        print(request.user.groups.all())
        if code not in request.user.groups.values_list('name', flat=True):
            _msg = (
                'Language %s not specified for user %s. Giving up task %s'
            )
            LOGGER.info(_msg, code, request.user.username, current_task)

            current_task.assignedTo.remove(request.user)
            current_task = None

    if not current_task:
        current_task = MultiModalAssessmentTask.get_task_for_user(
            request.user
        )

    # Check if marketTargetLanguage for current_task matches user languages.
    if current_task:
        code = current_task.marketTargetLanguageCode()
        print(request.user.groups.all())
        if code not in request.user.groups.values_list('name', flat=True):
            _msg = (
                'Language %s not specified for user %s. Giving up task %s'
            )
            LOGGER.info(_msg, code, request.user.username, current_task)

            current_task.assignedTo.remove(request.user)
            current_task = None

    _t2 = datetime.now()

    # If there is no current task, check if user is done with work agenda.
    work_completed = False
    if not current_task:
        agendas = TaskAgenda.objects.filter(user=request.user)

        for agenda in agendas:
            LOGGER.info('Identified work agenda %s', agenda)

            tasks_to_complete = []
            for serialized_open_task in agenda.serialized_open_tasks():
                open_task = serialized_open_task.get_object_instance()

                # Skip tasks which are not available anymore
                if open_task is None:
                    continue

                if open_task.next_item_for_user(request.user) is not None:
                    current_task = open_task
                    campaign = agenda.campaign
                    LOGGER.info(
                        'Current task type: %s',
                        open_task.__class__.__name__,
                    )
                else:
                    tasks_to_complete.append(serialized_open_task)

            modified = False
            for task in tasks_to_complete:
                modified = agenda.complete_open_task(task) or modified

            if modified:
                agenda.save()

        if not current_task and agendas.count() > 0:
            LOGGER.info('Work agendas completed, no more tasks for user')
            work_completed = True

    # Otherwise, compute set of language codes eligible for next task.
    campaign_languages = {}
    context_languages = {}
    multimodal_languages = {}
    languages = []
    if not current_task and not work_completed:
        for code in LANGUAGE_CODES_AND_NAMES:
            if request.user.groups.filter(name=code).exists():
                if not code in languages:
                    languages.append(code)

        if hits < HITS_REQUIRED_BEFORE_ENGLISH_ALLOWED:
            if len(languages) > 1 and 'eng' in languages:
                languages.remove('eng')

        # Remove any language for which no free task is available.
        from Campaign.models import Campaign

        for campaign in Campaign.objects.all():

            direct = DirectAssessmentTask.objects.filter(
                campaign__campaignName=campaign.campaignName
            )

            context = DirectAssessmentContextTask.objects.filter(
                campaign__campaignName=campaign.campaignName
            )

            multimodal = MultiModalAssessmentTask.objects.filter(
                campaign__campaignName=campaign.campaignName
            )

            is_context_campaign = context.exists()
            is_multi_modal_campaign = multimodal.exists()

            if is_multi_modal_campaign:
                multimodal_languages[campaign.campaignName] = []
                multimodal_languages[campaign.campaignName].extend(
                    languages
                )

            elif is_context_campaign:
                context_languages[campaign.campaignName] = []
                context_languages[campaign.campaignName].extend(languages)

            else:
                campaign_languages[campaign.campaignName] = []
                campaign_languages[campaign.campaignName].extend(languages)

            for code in languages:
                next_task_available = None

                if is_multi_modal_campaign:
                    _cls = MultiModalAssessmentTask
                elif is_context_campaign:
                    _cls = DirectAssessmentContextTask
                else:
                    _cls = DirectAssessmentTask

                next_task_available = _cls.get_next_free_task_for_language(
                    code, campaign, request.user
                )

                if not next_task_available:
                    if is_multi_modal_campaign:
                        multimodal_languages[campaign.campaignName].remove(
                            code
                        )
                    elif is_context_campaign:
                        context_languages[campaign.campaignName].remove(
                            code
                        )
                    else:
                        campaign_languages[campaign.campaignName].remove(
                            code
                        )

            _type = 'direct'
            _languages = campaign_languages
            if is_multi_modal_campaign:
                _type = 'multimodal'
                _languages = multimodal_languages
            elif is_context_campaign:
                _type = 'context'
                _languages = context_languages

            print(
                "campaign = {0}, type = {1}, languages = {2}".format(
                    campaign.campaignName,
                    _type,
                    _languages[campaign.campaignName],
                )
            )

    _t3 = datetime.now()

    duration = DirectAssessmentResult.get_time_for_user(request.user)
    days = duration.days
    hours = int((duration.total_seconds() - (days * 86400)) / 3600)
    minutes = int(
        ((duration.total_seconds() - (days * 86400)) % 3600) / 60
    )
    seconds = int((duration.total_seconds() - (days * 86400)) % 60)

    duration = DirectAssessmentContextResult.get_time_for_user(
        request.user
    )
    days += duration.days
    hours += int((duration.total_seconds() - (days * 86400)) / 3600)
    minutes += int(
        ((duration.total_seconds() - (days * 86400)) % 3600) / 60
    )
    seconds += int((duration.total_seconds() - (days * 86400)) % 60)

    duration = MultiModalAssessmentResult.get_time_for_user(request.user)
    days += duration.days
    hours += int((duration.total_seconds() - (days * 86400)) / 3600)
    minutes += int(
        ((duration.total_seconds() - (days * 86400)) % 3600) / 60
    )
    seconds += int((duration.total_seconds() - (days * 86400)) % 60)

    _t4 = datetime.now()

    all_languages = []
    for key, values in campaign_languages.items():
        for value in values:
            all_languages.append(
                (value, LANGUAGE_CODES_AND_NAMES[value], key)
            )

    print(str(all_languages).encode('utf-8'))

    ctx_languages = []
    for key, values in context_languages.items():
        for value in values:
            ctx_languages.append(
                (value, LANGUAGE_CODES_AND_NAMES[value], key)
            )

    print(str(ctx_languages).encode('utf-8'))

    mmt_languages = []
    for key, values in multimodal_languages.items():
        for value in values:
            mmt_languages.append(
                (value, LANGUAGE_CODES_AND_NAMES[value], key)
            )

    print(str(mmt_languages).encode('utf-8'))

    is_context_campaign = False
    is_multi_modal_campaign = False
    if current_task:
        is_context_campaign = (
            current_task.__class__.__name__
            == 'DirectAssessmentContextTask'
        )
        is_multi_modal_campaign = (
            current_task.__class__.__name__ == 'MultiModalAssessmentTask'
        )

    current_type = 'direct'
    if is_context_campaign:
        current_type = 'context'
    elif is_multi_modal_campaign:
        current_type = 'multimodal'

    template_context.update(
        {
            'annotations': annotations,
            'hits': hits,
            'total_hits': total_hits,
            'days': days,
            'hours': hours,
            'minutes': minutes,
            'seconds': seconds,
            'current_task': current_task,
            'current_type': current_type,
            'languages': all_languages,
            'context': ctx_languages,
            'multimodal': mmt_languages,
            'debug_times': (_t2 - _t1, _t3 - _t2, _t4 - _t3, _t4 - _t1),
            'template_debug': 'debug' in request.GET,
            'work_completed': work_completed,
        }
    )

    return render(request, 'Dashboard/dashboard.html', template_context)


# pylint: disable=missing-docstring
@login_required
def group_status(request):
    _method = getframeinfo(currentframe()).function
    _msg = '{0}.{1} deprecated as of 7/08/2019.'.format(
        'Dashboard.views', _method
    )
    raise NotImplementedError(_msg)


# pylint: disable=missing-docstring
@login_required
def multimodal_status(request):
    _method = getframeinfo(currentframe()).function
    _msg = '{0}.{1} deprecated as of 7/08/2019.'.format(
        'Dashboard.views', _method
    )
    raise NotImplementedError(_msg)


# pylint: disable=missing-docstring
@login_required
def system_status(request):
    _method = getframeinfo(currentframe()).function
    _msg = '{0}.{1} deprecated as of 7/08/2019.'.format(
        'Dashboard.views', _method
    )
    raise NotImplementedError(_msg)


# pylint: disable=missing-docstring
@login_required
def multimodal_systems(request):
    _method = getframeinfo(currentframe()).function
    _msg = '{0}.{1} deprecated as of 7/08/2019.'.format(
        'Dashboard.views', _method
    )
    raise NotImplementedError(_msg)


# pylint: disable=missing-docstring
@login_required
@add_deprecated_method
def metrics_status(request):
    _method = getframeinfo(currentframe()).function
    _msg = '{0}.{1} deprecated as of 7/08/2019.'.format(
        'Dashboard.views', _method
    )
    raise NotImplementedError(_msg)


# pylint: disable=missing-docstring
@login_required
@add_deprecated_method
def fe17_status(request):
    _method = getframeinfo(currentframe()).function
    _msg = '{0}.{1} deprecated as of 7/08/2019.'.format(
        'Dashboard.views', _method
    )
    raise NotImplementedError(_msg)
