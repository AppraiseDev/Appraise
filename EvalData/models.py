"""
EvalData models.py

###
# DESIGN/ARCHITECTURE
#
# EvalData
# - Market
# - Metadata
# - EvalItem
#  + TextSegment
#  + TextPair
#  + TextSet
#
###

"""
# pylint: disable=C0103,C0330
from datetime import datetime
from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils.text import format_lazy as f
from django.utils.translation import ugettext_lazy as _

MAX_DOMAINNAME_LENGTH = 20
MAX_LANGUAGECODE_LENGTH = 10
MAX_CORPUSNAME_LENGTH = 100
MAX_VERSIONINFO_LENGTH = 20
MAX_SOURCE_LENGTH = 5000
MAX_SEGMENTTEXT_LENGTH = 5000
MAX_SEGMENTID_LENGTH = 50
MAX_ITEMTYPE_LENGTH = 5
MAX_REQUIREDANNOTATIONS_VALUE = 50

SET_ITEMTYPE_CHOICES = (
  ('SRC', 'Source text'),
  ('TGT', 'Target text'),
  ('REF', 'Reference text'),
  ('BAD', 'Bad reference'),
  ('CHK', 'Redundant check')
)

# pylint: disable=C0103,R0903
class BaseMetadata(models.Model):
    """
    Abstract base metadata for all object models.
    """
    dateCreated = models.DateTimeField(
      auto_now_add=True,
      editable=False,
      verbose_name=_('Date created')
    )

    dateActivated = models.DateTimeField(
      blank=True,
      null=True,
      verbose_name=_('Date activated')
    )

    dateCompleted = models.DateTimeField(
      blank=True,
      null=True,
      verbose_name=_('Date completed')
    )

    dateRetired = models.DateTimeField(
      blank=True,
      null=True,
      verbose_name=_('Date retired')
    )

    dateModified = models.DateTimeField(
      blank=True,
      null=True,
      verbose_name=_('Date modified')
    )

    activated = models.BooleanField(
      blank=True,
      default=False,
      verbose_name=_('Activated?')
    )

    completed = models.BooleanField(
      blank=True,
      default=False,
      verbose_name=_('Completed?')
    )

    retired = models.BooleanField(
      blank=True,
      default=False,
      verbose_name=_('Retired?')
    )

    createdBy = models.ForeignKey(
      User,
      on_delete=models.PROTECT,
      editable=False,
      related_name='%(app_label)s_%(class)s_created_by',
      related_query_name="%(app_label)s_%(class)ss",
      verbose_name=_('Created by')
    )

    activatedBy = models.ForeignKey(
      User,
      blank=True,
      on_delete=models.PROTECT,
      editable=False,
      null=True,
      related_name='%(app_label)s_%(class)s_activated_by',
      related_query_name="%(app_label)s_%(class)ss",
      verbose_name=_('Activated by')
    )

    completedBy = models.ForeignKey(
      User,
      blank=True,
      on_delete=models.PROTECT,
      editable=False,
      null=True,
      related_name='%(app_label)s_%(class)s_completed_by',
      related_query_name="%(app_label)s_%(class)ss",
      verbose_name=_('Completed by')
    )

    retiredBy = models.ForeignKey(
      User,
      blank=True,
      on_delete=models.PROTECT,
      editable=False,
      null=True,
      related_name='%(app_label)s_%(class)s_retired_by',
      related_query_name="%(app_label)s_%(class)ss",
      verbose_name=_('Retired by')
    )

    modifiedBy = models.ForeignKey(
      User,
      blank=True,
      on_delete=models.PROTECT,
      editable=False,
      null=True,
      related_name='%(app_label)s_%(class)s_modified_by',
      related_query_name="%(app_label)s_%(class)ss",
      verbose_name=_('Modified by')
    )

    rawData = models.TextField(
      blank=True,
      editable=False,
      verbose_name=_('Raw data')
    )

    # pylint: disable=C0111
    class Meta:
        abstract = True

    def _set_boolean_states(self, activated, completed, retired):
        """
        Sets boolean states for current model instance.
        Also sets respective dates for all three states.
        """
        self.activated = activated
        self.dateActivated = datetime.now() if activated else None

        self.completed = completed
        self.dateCompleted = datetime.now() if completed else None

        self.retired = retired
        self.dateRetired = datetime.now() if retired else None

        self.save()

    def activate(self):
        """
        Sets activated=True for current model instance.
        This implies completed=False and retired=False.
        """
        self._set_boolean_states(True, False, False)

    def complete(self):
        """
        Sets completed=True for current model instance.
        This implies activated=False and retired=False.
        """
        self._set_boolean_states(False, True, False)

    def retire(self):
        """
        Sets retired=True for current model instance.

        This implies activated=False and completed=False.
        """
        self._set_boolean_states(False, False, True)

    def is_valid(self):
        """
        Validates the current model instance.
        """
        try:
            self.full_clean()
            return True

        except ValidationError:
            return False


class Market(BaseMetadata):
    """
    Models a language/locale market.
    """
    ###
    # Each market has a unique ID composed of source, target language codes
    # and application domain name. This also acts as primary lookup key.
    #
    # By assumption, source language content has been produced natively.
    # For monolingual content, source and target codes are identical.
    ###
    marketID = models.CharField(
        max_length=2 * MAX_LANGUAGECODE_LENGTH + MAX_DOMAINNAME_LENGTH + 2,
        editable=False,
        unique=True
    )

    sourceLanguageCode = models.CharField(
      max_length=MAX_LANGUAGECODE_LENGTH,
      verbose_name=_('Source language'),
      help_text=_(f('(max. {value} characters)',
        value=MAX_LANGUAGECODE_LENGTH))
    )

    targetLanguageCode = models.CharField(
      max_length=MAX_LANGUAGECODE_LENGTH,
      verbose_name=_('Target language'),
      help_text=_(f('(max. {value} characters)',
        value=MAX_LANGUAGECODE_LENGTH))
    )

    domainName = models.CharField(
      max_length=MAX_DOMAINNAME_LENGTH,
      verbose_name=_('Domain name'),
      help_text=_(f('(max. {value} characters)',
        value=MAX_DOMAINNAME_LENGTH))
    )

    def clean_fields(self, exclude=None):
        """
        Verifies that desired marketID is still available.
        """
        _new_marketID = '{0}_{1}_{2}'.format(
            self.sourceLanguageCode,
            self.targetLanguageCode,
            self.domainName
        )

        _market_instance = Market.objects.filter(marketID=_new_marketID)
        if _market_instance.exists():
            raise ValidationError(
              _(f('Market with identical marketID ("{mID}") already exists.',
                mID=_new_marketID))
            )

        super(Market, self).clean_fields(exclude)

    def save(self, *args, **kwargs):
        _new_marketID = '{0}_{1}_{2}'.format(
            self.sourceLanguageCode,
            self.targetLanguageCode,
            self.domainName
        )
        self.marketID = _new_marketID

        super(Market, self).save(*args, **kwargs)

    # pylint: disable=E1101
    def my_is_valid(self):
        """
        Validates the current Market instance, checking marketID uniqueness.
        """
        _expected_marketID = '{0}_{1}_{2}'.format(
            self.sourceLanguageCode,
            self.targetLanguageCode,
            self.domainName
        )

        _market_instance = Market.objects.filter(marketID=_expected_marketID)
        if not hasattr(self, "marketID") or self.marketID == '':
            if _market_instance.exists():
                return False

        else:
            _market_instance_obj = _market_instance.get()
            if _market_instance_obj is not None and self.id != _market_instance_obj.id:
                return False

        return super(Market, self).is_valid()

    def __str__(self):
        return self.marketID


class Metadata(BaseMetadata):
    """
    Models metadata associated to tasks.
    """
    market = models.ForeignKey(
      Market,
      on_delete=models.PROTECT
    )

    corpusName = models.CharField(
      max_length=MAX_CORPUSNAME_LENGTH,
      verbose_name=_('Corpus name'),
      help_text=_(f('(max. {value} characters)',
        value=MAX_CORPUSNAME_LENGTH))
    )

    versionInfo = models.CharField(
      max_length=MAX_VERSIONINFO_LENGTH,
      verbose_name=_('Version info'),
      help_text=_(f('(max. {value} characters)',
        value=MAX_VERSIONINFO_LENGTH))
    )

    source = models.CharField(
      max_length=MAX_SOURCE_LENGTH,
      verbose_name=_('Source'),
      help_text=_(f('(max. {value} characters)',
        value=MAX_SOURCE_LENGTH))
    )

    class Meta:
        verbose_name = 'Metadata record'

    def __str__(self):
        marketName = str(self.market)[:7].replace('_', '-')
        return '{0}/{1}["{2}"]'.format(
          marketName,
          self.corpusName,
          self.versionInfo
        )


class EvalItem(BaseMetadata):
    """
    Abstract base class for evaluation data items.

    Models corresponding, 1-based, integer ID and metadata.
    """
    itemID = models.PositiveIntegerField(
      verbose_name=_('Item ID'),
      help_text=_('(1-based)')
    )

    itemType = models.CharField(
      choices=SET_ITEMTYPE_CHOICES,
      max_length=MAX_ITEMTYPE_LENGTH,
      verbose_name=_('Item type')
    )

    metadata = models.ForeignKey(
      Metadata,
      on_delete=models.PROTECT
    )

    # pylint: disable=C0111,R0903
    class Meta:
        abstract = True

    # pylint: disable=E1101
    def is_valid(self):
        """
        Validates the current evaluation item, checking ID and metadata.
        """
        if not hasattr(self, "metadata") or not self.metadata.is_valid():
            return False

        if not isinstance(self.itemID, int):
            return False

        if self.itemID < 1:
            return False

        return super(EvalItem, self).is_valid()

    # pylint: disable=E1136
    def __str__(self):
        return '{0}.{1}[{2}]'.format(
          self.__class__.__name__,
          self.metadata,
          self.itemID
        )


class TextSegment(EvalItem):
    """
    Models a single text segment.
    """
    segmentID = models.CharField(
      max_length=MAX_SEGMENTID_LENGTH,
      verbose_name=_('Segment ID'),
      help_text=_(f('(max. {value} characters)',
        value=MAX_SEGMENTID_LENGTH))
    )

    segmentText = models.CharField(
      max_length=MAX_SEGMENTTEXT_LENGTH,
      verbose_name=_('Segment text'),
      help_text=_(f('(max. {value} characters)',
        value=MAX_SEGMENTTEXT_LENGTH))
    )

    # pylint: disable=E1101
    def is_valid(self):
        """
        Validates the current TextSegment instance, checking text.
        """
        if not isinstance(self.segmentText, type('This is a test sentence.')):
            return False

        _len = len(self.segmentText)
        if _len < 1 or _len > MAX_SEGMENTTEXT_LENGTH:
            return False

        return super(TextSegment, self).is_valid()


# TODO: chrife: source, target should be refactored into item1, item2.
#   For direct assessment, we will use candidate and reference.
class TextPair(EvalItem):
    """
    Models a pair of two text segments.
    """
    sourceID = models.CharField(
      max_length=MAX_SEGMENTID_LENGTH,
      verbose_name=_('Source ID'),
      help_text=_(f('(max. {value} characters)',
        value=MAX_SEGMENTID_LENGTH))
    )

    sourceText = models.CharField(
      max_length=MAX_SEGMENTTEXT_LENGTH,
      verbose_name=_('Source text'),
      help_text=_(f('(max. {value} characters)',
        value=MAX_SEGMENTTEXT_LENGTH))
    )

    targetID = models.CharField(
      max_length=MAX_SEGMENTID_LENGTH,
      verbose_name=_('Target ID'),
      help_text=_(f('(max. {value} characters)',
        value=MAX_SEGMENTID_LENGTH))
    )

    targetText = models.CharField(
      max_length=MAX_SEGMENTTEXT_LENGTH,
      verbose_name=_('Target text'),
      help_text=_(f('(max. {value} characters)',
        value=MAX_SEGMENTTEXT_LENGTH))
    )

    # pylint: disable=E1101
    def is_valid(self):
        """
        Validates the current TextPair instance, checking text.
        """
        if isinstance(self.sourceText, type('This is a test sentence.')):
            return False

        _len = len(self.sourceText)
        if _len < 1 or _len > MAX_SEGMENTTEXT_LENGTH:
            return False

        if isinstance(self.targetText, type('This is a test sentence.')):
            return False

        _len = len(self.targetText)
        if _len < 1 or _len > MAX_SEGMENTTEXT_LENGTH:
            return False

        return super(TextPair, self).is_valid()


class DirectAssessmentTask(BaseMetadata):
    """
    Models a direct assessment evaluation task.
    """
    campaign = models.ForeignKey(
      'Campaign.Campaign',
      on_delete=models.PROTECT,
      related_name='%(app_label)s_%(class)s_campaign',
      related_query_name="%(app_label)s_%(class)ss",
      verbose_name=_('Campaign')
    )

    items = models.ManyToManyField(
      TextPair,
      related_name='%(app_label)s_%(class)s_items',
      related_query_name="%(app_label)s_%(class)ss",
      verbose_name=_('Items')
    )

    requiredAnnotations = models.PositiveSmallIntegerField(
      verbose_name=_('Required annotations'),
      help_text=_(f('(value in range=[1,{value}])',
        value=MAX_REQUIREDANNOTATIONS_VALUE))
    )

    assignedTo = models.ForeignKey(
      User,
      on_delete=models.PROTECT,
      blank=True,
      null=True,
      related_name='%(app_label)s_%(class)s_assignedTo',
      related_query_name="%(app_label)s_%(class)ss",
      verbose_name=_('Assigned to'),
      help_text=_('(user working on this task)')
    )

    batchNo = models.PositiveIntegerField(
      verbose_name=_('Batch no'),
      help_text=_('(1-based)')
    )

    batchData = models.ForeignKey(
      'Campaign.CampaignData',
      on_delete=models.PROTECT,
      blank=True,
      null=True,
      related_name='%(app_label)s_%(class)s_batchData',
      related_query_name="%(app_label)s_%(class)ss",
      verbose_name=_('Batch data')
    )

    def dataName(self):
        return str(self.batchData)

    # pylint: disable=E1101
    def is_valid(self):
        """
        Validates the current DA task, checking campaign and items exist.
        """
        if not hasattr(self, 'campaign') or not self.campaign.is_valid():
            return False
        
        if not hasattr(self, 'items'):
            return False
        
        for item in self.items:
            if not item.is_valid():
                return False
        
        return True

    # pylint: disable=E1136
    def __str__(self):
        return '{0}.{1}[1..{2}]'.format(
          self.__class__.__name__,
          self.campaign,
          self.items.count()
        )


class DirectAssessmentResult(BaseMetadata):
    """
    Models a direct assessment evaluation result.
    """
    score = models.PositiveSmallIntegerField(
      verbose_name=_('Score'),
      help_text=_('(value in range=[1,100])')
    )

    ###
    # TODO: add duration, start and end time fields
    ###

    item = models.ForeignKey(
      TextPair,
      on_delete=models.PROTECT,
      related_name='%(app_label)s_%(class)s_item',
      related_query_name="%(app_label)s_%(class)ss",
      verbose_name=_('Item')
    )

    # pylint: disable=E1136
    def __str__(self):
        return '{0}.{1}={2}'.format(
          self.__class__.__name__,
          self.item,
          self.score
        )
