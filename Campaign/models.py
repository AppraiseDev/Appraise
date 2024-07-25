"""
Campaign models.py
"""
# pylint: disable=C0111,C0330,E1101
from json import JSONDecodeError
from json import loads
from pathlib import Path
from zipfile import is_zipfile
from zipfile import ZipFile

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.text import format_lazy as f
from django.utils.translation import gettext_lazy as _

from Dashboard.models import validate_language_code
from EvalData.models import AnnotationTaskRegistry
from EvalData.models import BaseMetadata
from EvalData.models import Market
from EvalData.models import Metadata
from EvalData.models import RESULT_TYPES

MAX_TEAMNAME_LENGTH = 250
MAX_SMALLINTEGER_VALUE = 32767
MAX_FILEFILED_SIZE = 10  # TODO: this does not get enforced currently; remove?
MAX_CAMPAIGNNAME_LENGTH = 250

# TODO: _validate_task_json(task_json)


def _validate_manifest_json(manifest_json):
    '''Validates manifest JSON data.

    Parameters:
    - manifest_json:str contains manifest.json contents for validation.

    Raises:
    - JSONDecodeError in case of invalid JSON contents;
    - ValidationError in case of missing manifest data.

    Returns:
    - True if validation is successful.
    '''
    manifest_data = loads(manifest_json)  # May raise JSONDecodeError

    if not isinstance(manifest_data, dict):
        raise ValidationError('manifest.json should contain single object')

    required_keys = (
        'CAMPAIGN_URL',
        'CAMPAIGN_NAME',
        'CAMPAIGN_KEY',
        'CAMPAIGN_NO',
        'REDUNDANCY',
        'TASKS_TO_ANNOTATORS',
    )
    for required_key in required_keys:
        if not required_key in manifest_data.keys():
            raise ValidationError(
                'manifest.json should contain {0!r} key'.format(required_key)
            )

    # Validate string types
    string_types = ('CAMPAIGN_URL', 'CAMPAIGN_NAME', 'CAMPAIGN_KEY')
    for string_type in string_types:
        if not isinstance(manifest_data[string_type], str):
            raise ValidationError(
                'manifest.json key {0!r} should be string type, '
                'is {1!r}'.format(string_type, manifest_data[string_type])
            )

    # Validate int types
    int_types = ('CAMPAIGN_NO', 'REDUNDANCY')
    for int_type in int_types:
        if not isinstance(manifest_data[int_type], int):
            raise ValidationError(
                'manifest.json key {0!r} should be number (int) type, '
                'is {1!r}'.format(int_type, manifest_data[int_type])
            )

    tasks_to_annotators = manifest_data['TASKS_TO_ANNOTATORS']
    redundancy = manifest_data['REDUNDANCY']
    _validate_tasks_to_annotators_map(tasks_to_annotators, redundancy)

    return True


def _validate_tasks_to_annotators_map(tasks_to_annotators, redundancy):
    '''Validates TASKS_TO_ANNOTATORS data.

    Description:
        This should be an array of arrays, like this:
            "TASKS_TO_ANNOTATORS": [
                ["eng", "trk", "uniform", 18, 36],
                ["trk", "eng", "uniform", 18, 36]
            ]

        Each inner array should have five values:
            1. str: source language code
            2. str: target language code
            3. str: task map setup mode
            4. int: number of annotators
            5. int: number of tasks

        Currently, the only supported task map setup mode is "uniform";
        this requires the following invariant:

            annotators * 2 * redundancy == tasks

    Parameters:
    - tasks_to_annototators:dict contains TASKS_TO_ANNOTATORS dict;
    - redundancy:int specifies campaign redundancy.

    Raises:
    - ValidationError in case of missing manifest data.

    Returns:
    - True if validation is successful.
    '''
    if not isinstance(tasks_to_annotators, list):
        raise ValidationError(
            "manifest.json key 'TASKS_TO_ANNOTATORS' should have "
            'list type, is {0!r}'.format(tasks_to_annotators)
        )

    # Validate items in TASKS_TO_ANNOTATORS
    for item in tasks_to_annotators:
        if not isinstance(item, list):
            raise ValidationError(
                "manifest.json key 'TASKS_TO_ANNOTATORS' list "
                'item should have list type, is {0!r}'.format(item)
            )

        if not len(item) == 5:
            raise ValidationError(
                "manifest.json key 'TASKS_TO_ANNOTATORS' list "
                'item should be 5-tuple, is {0!r}'.format(item)
            )

        source_code, target_code, mode, annotators, tasks = item

        # Vaidate correct item type signature: <str, str, str, int, int>
        correct_types = [isinstance(x, str) for x in (source_code, target_code, mode)]
        correct_types.extend([isinstance(x, int) for x in (annotators, tasks)])
        if not all(correct_types):
            raise ValidationError(
                "manifest.json key 'TASKS_TO_ANNOTATORS' list "
                'item should have <str, str, str, int, int> '
                'signature, is {0!r}'.format(item)
            )

        # Validate that source_code/target_code are valid language codes
        valid_language_codes = [
            validate_language_code(x) for x in (source_code, target_code)
        ]
        if not all(valid_language_codes):
            raise ValidationError(
                "manifest.json key 'TASKS_TO_ANNOTATORS' list item "
                'has invalid language codes, check {0!r}'.format(item)
            )

        # Validate mode is set to "uniform" -- which is the only task
        # map creation mode currently supported. For "uniform" mode, we
        # also require that: annotators * 2 * redundancy == tasks.
        if not mode.lower() == 'uniform':
            raise ValidationError(
                "manifest.json key 'TASKS_TO_ANNOTATORS' list item only"
                'supports "uniform" mode, check {0!r}'.format(item)
            )

        expected = annotators * 2 * redundancy
        if not expected == tasks:
            raise ValidationError(
                "manifest.json key 'TASKS_TO_ANNOTATORS' list item has "
                'bad task map ({0} * 2 * {1} != {2}), check {3!r}'.format(
                    annotators, redundancy, tasks, item
                )
            )

    return True


def _validate_package_file(package_file):
    '''Validates package file.

    Parameters:
    - package_file:FieldFile contains binary contents of package ZIP file.

    Raises:
    - django.core.exceptions.ValidationError if package file is invalid.

    Returns:
    - True if validation is successful.
    '''
    package_path = Path(package_file.name)

    if not package_file.name.lower().endswith('.zip'):
        raise ValidationError(
            'Invalid package file {0!r} -- expected '
            "'.zip' extension".format(package_file.name)
        )  # TODO: add test

    if not is_zipfile(package_file):
        raise ValidationError(
            'Invalid package file {0!r} -- expected '
            'valid ZIP archive'.format(package_file.name)
        )  # TODO: add test

    package_zip = ZipFile(package_file)
    if not 'manifest.json' in package_zip.namelist():
        raise ValidationError(
            'Invalid package file {0!r} -- expected '
            'manifest.json'.format(package_file.name)
        )  # TODO: add test

    manifest_json = package_zip.read('manifest.json').decode('utf-8')
    try:
        _validate_manifest_json(manifest_json)

    except JSONDecodeError as exc:
        raise ValidationError(
            'Invalid package file {0!r} -- bad JSON: '
            '{1}'.format(package_file.name, exc)
        )  # TODO: add test

    contains_batches_folder = any(
        [x.startswith('Batches/') for x in package_zip.namelist()]
    )
    if not contains_batches_folder:
        raise ValidationError(
            'Invalid package file {0!r} -- expected '
            'Batches/ folder'.format(package_file.name)
        )  # TODO: add test

    batches_json = [
        x
        for x in package_zip.namelist()
        if x.startswith('Batches/') and x.endswith('.json')
    ]

    if not batches_json:
        raise ValidationError(
            'Invalid package file {0!r} -- expected at least one '
            'batch JSON archive file'.format(package_path.name)
        )

    manifest_data = loads(manifest_json)
    manifest_tasks = manifest_data['TASKS_TO_ANNOTATORS']
    if not len(manifest_tasks) == len(batches_json):
        raise ValidationError(
            'Invalid package file {0!r} -- wrong number of batches '
            '({1} != {2})'.format(
                package_path.name, len(batches_json), len(manifest_tasks)
            )
        )

    # Capture from task definition:
    # - source_code: 0;
    # - target_code: 1;
    # - tasks: 4.
    task_data_from_manifest = set(((x[0], x[1], x[4]) for x in manifest_tasks))
    print(task_data_from_manifest)

    # TODO:
    #
    # 1. Loop over all batch JSON files;
    # 2. Validate batch JSON data;
    # 3. Extract source_code, target_code, tasks

    return True


class CampaignTeam(BaseMetadata):
    """
    Models a campaign team.
    """

    teamName = models.CharField(
        max_length=MAX_TEAMNAME_LENGTH,
        verbose_name=_('Team name'),
        help_text=_(f('(max. {value} characters)', value=MAX_TEAMNAME_LENGTH)),
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
        help_text=_(f('(value in range=[1,{value}])', value=MAX_SMALLINTEGER_VALUE)),
    )

    requiredHours = models.PositiveSmallIntegerField(
        verbose_name=_('Required hours'),
        help_text=_(f('(value in range=[1,{value}])', value=MAX_SMALLINTEGER_VALUE)),
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

    teamMembers.short_description = '# of team members'  # type: ignore

    # TODO: make it to be the minimum of:
    # - # of completed annotations / # required annotations; and
    # - # of completed hours / # required hours.
    # pylint: disable=no-self-use
    def completionStatus(self):
        """
        Proxy method returning completion status in percent. This is defined as
        # of completed annotations / # of required annotations.

        """
        # Required annotations times the number of users excluding the owner
        count_all = self.requiredAnnotations * (self.members.count() - 1)

        count_done = 0
        for result_type in RESULT_TYPES:
            for user in self.members.all():
                if user == self.owner:  # Skip superuser
                    continue
                count_done += result_type.objects.filter(
                    createdBy=user, completed=True
                ).count()

        completion = 0.0
        if count_all != 0:
            completion = count_done / float(count_all)
        return '{:.2%}'.format(completion)

    completionStatus.short_description = 'Completion status'  # type: ignore


class CampaignData(BaseMetadata):
    """
    Models a batch of campaign data.
    """

    dataFile = models.FileField(verbose_name=_('Data file'), upload_to='Batches')

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
        help_text=_(f('(max. {value} characters)', value=MAX_CAMPAIGNNAME_LENGTH)),
    )

    # Field for task-specific options used by all tasks within this campaign
    campaignOptions = models.TextField(
        blank=True,
        null=True,
        verbose_name=_('Campaign task-specific options'),
    )

    teams = models.ManyToManyField(
        CampaignTeam,
        blank=True,
        related_name='%(app_label)s_%(class)s_teams',
        related_query_name="%(app_label)s_%(class)ss",
        verbose_name=_('Teams'),
    )

    batches = models.ManyToManyField(
        CampaignData,
        blank=True,
        related_name='%(app_label)s_%(class)s_batches',
        related_query_name="%(app_label)s_%(class)ss",
        verbose_name=_('Batches'),
    )

    packageFile = models.FileField(
        blank=True,
        null=True,
        verbose_name=_('Package file'),
        upload_to='Packages',
        validators=[_validate_package_file],
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

    campaign = models.ForeignKey(Campaign, models.PROTECT, verbose_name=_('Campaign'))

    # TODO: decide whether this needs to be optimized.
    def __str__(self):
        return 'trusted:{0}/{1}'.format(self.user.username, self.campaign.campaignName)
