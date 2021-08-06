"""
Appraise evaluation framework

See LICENSE for usage details

Keeps a registry of deprecated methods.

Use @add_deprecated_method decorator to mark method as deprecated. This
needs to be placed closest relative to the deprecated method for now.

Use get_deprecated_methods() to retrieve set of deprecated methods.
"""
from typing import Set


_DEPRECATED_METHOD_REGISTRY = set()  # Set[str]


def add_deprecated_method(func):
    """
    Add deprecated method to registry.
    """
    _DEPRECATED_METHOD_REGISTRY.add(func.__name__)
    return func


def get_deprecated_methods():
    """
    Get deprecated methods from registry.
    """
    return _DEPRECATED_METHOD_REGISTRY


# pylint: disable=undefined-variable
def fe17_status(request):
    """
    Appraise system status page.

    Used to be @login_required method in Dashboard.views.
    Method has been deprecated on 7/08/2019.
    """
    _t1 = datetime.now()

    context = {'active_page': 'system-status'}
    context.update(BASE_CONTEXT)

    _t2 = datetime.now()
    task_data = DirectAssessmentTask.objects.filter(id__gte=37)
    _t3 = datetime.now()
    task_status = []
    for task in task_data.order_by('id'):
        source_language = task.items.first().metadata.market.sourceLanguageCode
        target_language = task.items.first().metadata.market.targetLanguageCode
        annotators = task.assignedTo.count()
        results = task.evaldata_directassessmentresult_task.count()
        task_status.append(
            (
                task.id,
                source_language,
                target_language,
                annotators,
                round(100 * annotators / 4.0),
                results,
                round(100 * results / (4 * 100.0)),
            )
        )
    _t4 = datetime.now()
    context.update(
        {
            'task_status': task_status,
            'debug_times': (_t2 - _t1, _t3 - _t2, _t4 - _t3, _t4 - _t1),
            'template_debug': 'debug' in request.GET,
        }
    )

    return render(request, 'Dashboard/metrics-status.html', context)


def group_status(request):
    """
    Appraise group status page.

    Used to be @login_required method in Dashboard.views.
    Method has been deprecated on 7/08/2019.
    """
    _t1 = datetime.now()

    context = {'active_page': 'group-status'}
    context.update(BASE_CONTEXT)

    _t2 = datetime.now()
    group_data = DirectAssessmentResult.compute_accurate_group_status()
    _t3 = datetime.now()

    _group_status = []
    for group in group_data:
        _group_status.append((group, group_data[group][0], group_data[group][1]))

    sorted_status = sorted(_group_status, key=lambda x: x[1], reverse=True)
    _t4 = datetime.now()

    context.update(
        {
            'group_status': list(sorted_status),
            'sum_completed': sum([x[1] for x in _group_status]),
            'sum_total': sum([x[2] for x in _group_status]),
            'debug_times': (_t2 - _t1, _t3 - _t2, _t4 - _t3, _t4 - _t1),
            'template_debug': 'debug' in request.GET,
        }
    )

    return render(request, 'Dashboard/group-status.html', context)


def metrics_status(request):
    """
    Appraise system status page.

    Used to be @login_required method in Dashboard.views.
    Method has been deprecated on 7/08/2019.
    """
    _t1 = datetime.now()

    context = {'active_page': 'system-status'}
    context.update(BASE_CONTEXT)

    _t2 = datetime.now()
    task_data = DirectAssessmentTask.objects.filter(
        id__in=[x + 5427 for x in range(48)]
    )
    _t3 = datetime.now()
    task_status = []
    for task in task_data.order_by('id'):
        source_language = task.items.first().metadata.market.sourceLanguageCode
        target_language = task.items.first().metadata.market.targetLanguageCode
        annotators = task.assignedTo.count()
        results = task.evaldata_directassessmentresult_task.count()
        task_status.append(
            (
                task.id,
                source_language,
                target_language,
                annotators,
                round(100 * annotators / 15.0),
                results,
                round(100 * results / (15 * 70.0)),
            )
        )
    _t4 = datetime.now()
    context.update(
        {
            'task_status': task_status,
            'debug_times': (_t2 - _t1, _t3 - _t2, _t4 - _t3, _t4 - _t1),
            'template_debug': 'debug' in request.GET,
        }
    )

    return render(request, 'Dashboard/metrics-status.html', context)


def multimodal_status(request):
    """
    Appraise group status page.

    Used to be @login_required method in Dashboard.views.
    Method has been deprecated on 7/08/2019.

    """
    _t1 = datetime.now()

    context = {'active_page': 'group-status'}
    context.update(BASE_CONTEXT)

    _t2 = datetime.now()
    group_data = MultiModalAssessmentResult.compute_accurate_group_status()
    _t3 = datetime.now()

    _group_status = []
    for group in group_data:
        _group_status.append((group, group_data[group][0], group_data[group][1]))

    sorted_status = sorted(_group_status, key=lambda x: x[1], reverse=True)
    _t4 = datetime.now()

    context.update(
        {
            'group_status': list(sorted_status),
            'sum_completed': sum([x[1] for x in _group_status]),
            'sum_total': sum([x[2] for x in _group_status]),
            'debug_times': (_t2 - _t1, _t3 - _t2, _t4 - _t3, _t4 - _t1),
            'template_debug': 'debug' in request.GET,
        }
    )

    return render(request, 'Dashboard/group-status.html', context)


def multimodal_systems(request):
    """
    Appraise system status page.

    Used to be @login_required method in Dashboard.views.
    Method has been deprecated on 7/08/2019.
    """
    _t1 = datetime.now()

    context = {'active_page': 'system-status'}
    context.update(BASE_CONTEXT)

    _t2 = datetime.now()
    system_data = MultiModalAssessmentResult.get_system_status(sort_index=1)
    _t3 = datetime.now()
    sorted_status = []
    total_completed = 0
    for code in system_data:
        if not system_data[code]:
            continue

        for data in system_data[code]:
            sorted_status.append((code, data[0], data[1]))
            total_completed += data[1]

    _t4 = datetime.now()
    context.update(
        {
            'system_status': sorted_status,
            'total_completed': total_completed,
            'debug_times': (_t2 - _t1, _t3 - _t2, _t4 - _t3, _t4 - _t1),
            'template_debug': 'debug' in request.GET,
        }
    )

    return render(request, 'Dashboard/system-status.html', context)


# pylint: disable=protected-access
def reassign_tasks(cls, old_username, new_username):
    """
    Reassigns tasks in TaskAgenda for old user to new user.

    Used to be @classmethod in EvalData.models.TaskAgenda.
    Method has been deprecated on 5/27/2019.
    """
    from django.contrib.auth.models import User

    old_user = User.objects.get(username=old_username)
    new_user = User.objects.get(username=new_username)

    old_agenda = cls.objects.get(user=old_user)
    new_agenda = cls()
    new_agenda.user = new_user
    new_agenda.campaign = old_agenda.campaign
    new_agenda.save()

    for _t in old_agenda._completed_tasks.all():
        new_agenda._open_tasks.add(_t)
    for _t in old_agenda._open_tasks.all():
        new_agenda._open_tasks.add(_t)
    new_agenda.save()

    old_tasks = list(old_agenda._completed_tasks.all())
    old_tasks.extend(old_agenda._open_tasks.all())
    new_tasks = list(new_agenda._open_tasks.all())

    return (old_tasks, new_tasks)


def system_status(request):
    """
    Appraise system status page.

    Used to be @login_required method in Dashboard.views.
    Method has been deprecated on 7/08/2019.
    """
    _t1 = datetime.now()

    context = {'active_page': 'system-status'}
    context.update(BASE_CONTEXT)

    _t2 = datetime.now()
    system_data = DirectAssessmentResult.get_system_status(sort_index=1)
    _t3 = datetime.now()
    sorted_status = []
    total_completed = 0
    for code in system_data:
        if not system_data[code]:
            continue

        for data in system_data[code]:
            sorted_status.append((code, data[0], data[1]))
            total_completed += data[1]

    _t4 = datetime.now()
    context.update(
        {
            'system_status': sorted_status,
            'total_completed': total_completed,
            'debug_times': (_t2 - _t1, _t3 - _t2, _t4 - _t3, _t4 - _t1),
            'template_debug': 'debug' in request.GET,
        }
    )

    return render(request, 'Dashboard/system-status.html', context)
