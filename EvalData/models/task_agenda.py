"""
Appraise evaluation framework

See LICENSE for usage details
"""
# pylint: disable=C0103,C0330,no-member
from inspect import currentframe
from inspect import getframeinfo
from re import compile as re_compile

from django.contrib import messages
from django.contrib.auth.models import User
from django.db import models
from django.utils.translation import gettext_lazy as _

from deprecated import add_deprecated_method
from EvalData.models.base_models import ObjectID
from EvalData.models.data_assessment import DataAssessmentResult
from EvalData.models.direct_assessment import DirectAssessmentResult
from EvalData.models.direct_assessment import DirectAssessmentTask
from EvalData.models.direct_assessment_context import (
    DirectAssessmentContextResult,
)
from EvalData.models.direct_assessment_document import (
    DirectAssessmentDocumentResult,
)
from EvalData.models.multi_modal_assessment import (
    MultiModalAssessmentResult,
)
from EvalData.models.pairwise_assessment import PairwiseAssessmentResult
from EvalData.models.pairwise_assessment_document import (
    PairwiseAssessmentDocumentResult,
)

# TODO: Unclear if these are needed?
# from Appraise.settings import STATIC_URL, BASE_CONTEXT


class TaskAgenda(models.Model):
    user = models.ForeignKey(User, models.PROTECT, verbose_name=_('User'))

    campaign = models.ForeignKey(
        'Campaign.Campaign', models.PROTECT, verbose_name=_('Campaign')
    )

    _open_tasks = models.ManyToManyField(
        ObjectID,
        blank=True,
        related_name='%(app_label)s_%(class)s_opentasks',
        related_query_name="%(app_label)s_%(class)ss_open",
        verbose_name=_('Open tasks'),
    )

    _completed_tasks = models.ManyToManyField(
        ObjectID,
        blank=True,
        related_name='%(app_label)s_%(class)s_completedtasks',
        related_query_name="%(app_label)s_%(class)ss_completed",
        verbose_name=_('Completed tasks'),
    )

    class Meta:
        permissions = (("reset_taskagenda", "Can reset task agendas"),)

    def completed(self):
        return self._open_tasks.count() == 0

    def open_tasks(self):
        return (x.get_object_instance() for x in self._open_tasks.all())

    def serialized_open_tasks(self):
        return list(self._open_tasks.all())

    def completed_tasks(self):
        return (x.get_object_instance() for x in self._completed_tasks.all())

    def activate_task(self, task):
        return self.activate_completed_task(task, only_completed=False)

    def activate_completed_task(self, task, only_completed=True):
        if not isinstance(task, ObjectID):
            raise ValueError('Invalid task {0!r} not ObjectID ' 'instance'.format(task))

        if only_completed and not task in self._completed_tasks.all():
            return False

        self._completed_tasks.remove(task)

        if not task in self._open_tasks.all():
            self._open_tasks.add(task)

        return True

    def complete_task(self, task):
        return self.complete_open_task(task, only_open=False)

    def complete_open_task(self, task, only_open=False):
        if not isinstance(task, ObjectID):
            raise ValueError('Invalid task {0!r} not ObjectID ' 'instance'.format(task))

        if only_open and not task in self._open_tasks.all():
            return False

        self._open_tasks.remove(task)

        if not task in self._completed_tasks.all():
            self._completed_tasks.add(task)

        return True

    def contains_task(self, task):
        """
        Returns True if task is assigned in this TaskAgenda, False otherwise.
        """
        if task in self._open_tasks.all():
            return True

        if task in self._completed_tasks.all():
            return True

        return False

    # TODO: decide whether this needs to be optimized.
    def __str__(self):
        return '{0}/{1}[{2}:{3}]'.format(
            self.user.username,
            self.campaign.campaignName,
            self._open_tasks.count(),
            self._completed_tasks.count(),
        )

    # pylint: disable=protected-access,missing-docstring
    @classmethod
    @add_deprecated_method
    def reassign_tasks(cls, old_username, new_username):
        _method = getframeinfo(currentframe()).function
        _msg = '{0}.{1} deprecated as of 5/27/2019.'.format(cls, _method)
        raise NotImplementedError(_msg)

    # pylint: disable=undefined-variable
    def reset_taskagenda(self):
        """
        Resets annotations and state for this task agenda instance.

        This will do nothing if there are no annotations yet.

        Moves all annotations for the agenda owner to a new user account,
        named as '{self.user.username}-{number:02x}', preserving data for
        future analysis. This user is not added to the respective campaign
        team, so that these annotations will not affect final results.

        The reset moves all related tasks back into self._open_tasks.

        Returns True upon success, False otherwise.
        """
        type_to_result_class_mapping = {
            'DataAssessmentTask': DataAssessmentResult,
            'DirectAssessmentTask': DirectAssessmentResult,
            'DirectAssessmentContextTask': DirectAssessmentContextResult,
            'DirectAssessmentDocumentTask': DirectAssessmentDocumentResult,
            'MultiModalAssessmentTask': MultiModalAssessmentResult,
            'PairwiseAssessmentDocumentTask': PairwiseAssessmentDocumentResult,
            'PairwiseAssessmentTask': PairwiseAssessmentResult,
        }

        result_class = type_to_result_class_mapping.get(
            self.campaign.get_campaign_type(), None
        )

        if not result_class:
            _msg = 'Unknown annotation type {0} for user {1}'.format(
                self.campaign.get_campaign_type(), self.user
            )
            _lvl = messages.ERROR
            return (False, _msg, _lvl)

        annotated_output_for_user = result_class.objects.filter(createdBy=self.user)

        if not annotated_output_for_user.exists():
            _msg = 'Nothing to be done for user {0}.'.format(self.user)
            _lvl = messages.INFO
            return (False, _msg, _lvl)

        _shadow = re_compile(r'{0}-[0-9a-f]{{2}}'.format(self.user.username))
        _users = User.objects.filter(username__startswith=self.user.username)
        _shadow_copies = 0
        for _candidate in _users:
            if _shadow.match(_candidate.username):
                _shadow_copies += 1

        if (_shadow_copies + 1) > 255:
            _msg = 'Cannot create shadow copy for user {0}.'.format(self.user)
            _lvl = messages.WARNING
            return (False, _msg, _lvl)

        # Next shadow copy will be named:
        #   {self.user.username}-{_shadow_copies+1:02x}
        #
        # This user will be inactive and won't allow authentication as we
        # do not set a password. The account is purely for archival use.
        _name = '{0}-{1:02x}'.format(self.user.username, _shadow_copies + 1)
        _shadow_copy = User.objects.create_user(_name)
        _shadow_copy.is_active = False
        _shadow_copy.save()

        for annotation_result in annotated_output_for_user:
            annotation_result.createdBy = _shadow_copy
            annotation_result.modifiedBy = _shadow_copy
            annotation_result.retire()  # Implictly calls save()

        # pylint: disable=protected-access
        for task in self._completed_tasks.all():
            self._open_tasks.add(task)
            self._completed_tasks.remove(task)

        _msg = (
            'Succesfully reset task agenda for user {0}, creating '
            'shadow copy {1}.'.format(self.user, _shadow_copy)
        )
        _lvl = messages.INFO
        return (True, _msg, _lvl)


class WorkAgenda(models.Model):
    user = models.ForeignKey(User, models.PROTECT, verbose_name=_('User'))

    campaign = models.ForeignKey(
        'Campaign.Campaign', models.PROTECT, verbose_name=_('Campaign')
    )

    openTasks = models.ManyToManyField(
        DirectAssessmentTask,
        blank=True,
        related_name='%(app_label)s_%(class)s_opentasks',
        related_query_name="%(app_label)s_%(class)ss_open",
        verbose_name=_('Open tasks'),
    )

    completedTasks = models.ManyToManyField(
        DirectAssessmentTask,
        blank=True,
        related_name='%(app_label)s_%(class)s_completedtasks',
        related_query_name="%(app_label)s_%(class)ss_completed",
        verbose_name=_('Completed tasks'),
    )

    def completed(self):
        return self.openTasks.count() == 0

    # TODO: decide whether this needs to be optimized.
    def __str__(self):
        return '{0}/{1}[{2}:{3}]'.format(
            self.user.username,
            self.campaign.campaignName,
            self.openTasks.count(),
            self.completedTasks.count(),
        )
