"""
Campaign models.py
"""
# pylint: disable=C0111,C0330,E1101
from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils.text import format_lazy as f
from django.utils.translation import ugettext_lazy as _

from EvalData.models import (
    AnnotationTaskRegistry,
    BaseMetadata,
    Market,
    Metadata,
)

MAX_TEAMNAME_LENGTH = 250
MAX_SMALLINTEGER_VALUE = 32767
MAX_FILEFILED_SIZE = (
    10
)  # TODO: this does not get enforced currently; remove?
MAX_CAMPAIGNNAME_LENGTH = 250


class CampaignTeam(BaseMetadata):
    """
    Models a campaign team.
    """

    teamName = models.CharField(
        max_length=MAX_TEAMNAME_LENGTH,
        verbose_name=_('Team name'),
        help_text=_(
            f('(max. {value} characters)', value=MAX_TEAMNAME_LENGTH)
        ),
    )

    owner = models.ForeignKey(
        User,
        limit_choices_to={'is_staff': True},
        on_delete=models.PROTECT,
        related_name='%(app_label)s_%(class)s_owner',
        related_query_name="%(app_label)s_%(class)ss",
        verbose_name=_('Team owner'),
        help_text=_('(must be staff member)'),
    )

    members = models.ManyToManyField(
        User,
        related_name='%(app_label)s_%(class)s_members',
        related_query_name="%(app_label)s_%(class)ss",
        verbose_name=_('Team members'),
    )

    requiredAnnotations = models.PositiveSmallIntegerField(
        verbose_name=_('Required annotations'),
        help_text=_(
            f('(value in range=[1,{value}])', value=MAX_SMALLINTEGER_VALUE)
        ),
    )

    requiredHours = models.PositiveSmallIntegerField(
        verbose_name=_('Required hours'),
        help_text=_(
            f('(value in range=[1,{value}])', value=MAX_SMALLINTEGER_VALUE)
        ),
    )

    # pylint: disable=C0111,R0903
    class Meta:
        ordering = ['_str_name']
        verbose_name = 'Team'
        verbose_name_plural = 'Teams'

    def _generate_str_name(self):
        return '{0} ({1})'.format(self.teamName, self.owner)

    def is_valid(self):
        """
        Validates the current CampaignTeam instance.
        """
        try:
            self.full_clean()
            return True

        except ValidationError:
            return False

    # pylint: disable=C0103,E1101
    def teamMembers(self):
        """
        Proxy method returning members count.
        """
        return self.members.count()

    teamMembers.short_description = '# of team members'

    # TODO: Connect to actual data, producing correct completion status.
    # pylint: disable=no-self-use
    def completionStatus(self):
        """
        Proxy method return completion status in percent.

        This is defined to be the minimum of:
        - # of completed annotations / # required annotations; and
        - # of completed hours / # required hours.
        """
        return '0%'

    completionStatus.short_description = 'Completion status'


class CampaignData(BaseMetadata):
    """
    Models a batch of campaign data.
    """

    dataFile = models.FileField(
        verbose_name=_('Data file'), upload_to='Batches'
    )

    market = models.ForeignKey(
        Market, on_delete=models.PROTECT, verbose_name=_('Market')
    )

    metadata = models.ForeignKey(
        Metadata, on_delete=models.PROTECT, verbose_name=_('Metadata')
    )

    dataValid = models.BooleanField(
        blank=True,
        default=False,
        editable=False,
        verbose_name=_('Data valid?'),
    )

    dataReady = models.BooleanField(
        blank=True,
        default=False,
        editable=False,
        verbose_name=_('Data ready?'),
    )

    # pylint: disable=C0111,R0903
    class Meta:
        ordering = ['_str_name']
        verbose_name = 'Batch'
        verbose_name_plural = 'Batches'

    def _generate_str_name(self):
        return self.dataFile.name

    # pylint: disable=C0103
    def dataName(self):
        return self.dataFile.name

    def activate(self):
        """
        Only activate current campaign data instance if both valid and ready.
        """
        if self.dataValid and self.dataReady:
            super(CampaignData, self).activate()

    def clean_fields(self, exclude=None):
        if self.activated:
            if not self.dataValid or not self.dataReady:
                raise ValidationError(
                    _(
                        'Cannot activate campaign data as it is either not valid or not ready yet.'
                    )
                )

        super(CampaignData, self).clean_fields(exclude)


class Campaign(BaseMetadata):
    """
    Models an evaluation campaign.
    """

    campaignName = models.CharField(
        max_length=MAX_CAMPAIGNNAME_LENGTH,
        verbose_name=_('Campaign name'),
        help_text=_(
            f('(max. {value} characters)', value=MAX_CAMPAIGNNAME_LENGTH)
        ),
    )

    teams = models.ManyToManyField(
        CampaignTeam,
        blank=True,
        null=True,
        related_name='%(app_label)s_%(class)s_teams',
        related_query_name="%(app_label)s_%(class)ss",
        verbose_name=_('Teams'),
    )

    batches = models.ManyToManyField(
        CampaignData,
        blank=True,
        null=True,
        related_name='%(app_label)s_%(class)s_batches',
        related_query_name="%(app_label)s_%(class)ss",
        verbose_name=_('Batches'),
    )

    packageFile = models.FileField(
        blank=True,
        null=True,
        verbose_name=_('Package file'),
        upload_to='Packages',
    )

    def _generate_str_name(self):
        return self.campaignName

    @classmethod
    def get_campaign_or_raise(cls, campaign_name):
        """
        Get campaign with name campaign_name from database.

        Returns Campaign instance if exists, otherwise LookupError.
        """
        _obj = Campaign.objects.filter(campaignName=campaign_name)
        if not _obj.exists():
            _msg = 'Failure to identify campaign {0}'.format(campaign_name)
            raise LookupError(_msg)

        return _obj.first()  # if multiple campaigns, return first

    def get_campaign_type(self) -> str:
        """
        Get campaign type based on evaldata_{cls_name}_campaign QuerySet.

        For now, we assume that campaigns can only have a single type.

        We use the following check to identify the campaign's type:
        c.evaldata_directassessmentcontexttask_campaign.exists()

        Returns class object, which is a sub class of BaseAnnotationTask.
        """
        for cls_name in AnnotationTaskRegistry.get_types():
            qs_name = cls_name.lower()
            qs_attr = 'evaldata_{0}_campaign'.format(qs_name)
            qs_obj = getattr(self, qs_attr, None)
            if qs_obj and qs_obj.exists():
                return cls_name

        _msg = 'Unknown type for campaign {0}'.format(self.campaignName)
        raise LookupError(_msg)  # This should never happen, thus raise!


class TrustedUser(models.Model):
    '''
    Models trusted users who are exempt of quality controls.
    '''

    user = models.ForeignKey(User, models.PROTECT, verbose_name=_('User'))

    campaign = models.ForeignKey(
        Campaign, models.PROTECT, verbose_name=_('Campaign')
    )

    # TODO: decide whether this needs to be optimized.
    def __str__(self):
        return 'trusted:{0}/{1}'.format(
            self.user.username, self.campaign.campaignName
        )
