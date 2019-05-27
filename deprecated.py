"""
Appraise evaluation framework

See LICENSE for usage details
"""
from django.contrib.auth.models import User

# pylint: disable=protected-access
def reassign_tasks(cls, old_username, new_username):
    """
    Reassigns tasks in TaskAgenda for old user to new user.

    Used to be @classmethod in EvalData.models.TaskAgenda.
    Method has been deprecated on 5/27/2019.
    """
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
