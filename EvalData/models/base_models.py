"""
Appraise evaluation framework

See LICENSE for usage details
"""
# pylint: disable=C0103,C0330,no-member
from datetime import datetime
from datetime import timedelta
from difflib import SequenceMatcher
from traceback import format_exc
from typing import Set

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.html import escape
from django.utils.text import format_lazy as f
from django.utils.timezone import utc
from django.utils.translation import gettext_lazy as _

from Appraise.utils import _get_logger

# TODO: Unclear if these are needed?
# from Appraise.settings import STATIC_URL, BASE_CONTEXT

MAX_DOMAINNAME_LENGTH = 20
MAX_LANGUAGECODE_LENGTH = 10
MAX_CORPUSNAME_LENGTH = 100
MAX_VERSIONINFO_LENGTH = 20
MAX_SOURCE_LENGTH = 2000
MAX_SEGMENTTEXT_LENGTH = 2000
MAX_SEGMENTID_LENGTH = 1000
MAX_ITEMTYPE_LENGTH = 5
MAX_REQUIREDANNOTATIONS_VALUE = 50
MAX_TYPENAME_LENGTH = 100
MAX_PRIMARYID_LENGTH = 50

SET_ITEMTYPE_CHOICES = (
    ('SRC', 'Source text'),
    ('TGT', 'Target text'),
    ('REF', 'Reference text'),
    ('BAD', 'Bad reference'),
    ('CHK', 'Redundant check'),
)

LOGGER = _get_logger(name=__name__)


def seconds_to_timedelta(value):
    """
    Converst the given value in secodns to datetime.timedelta.
    """
    _days = value // 86400
    _hours = (value // 3600) % 24
    _mins = (value // 60) % 60
    _secs = value % 60
    return timedelta(days=_days, hours=_hours, minutes=_mins, seconds=_secs)


class ObjectID(models.Model):
    """
    Encodes an object type and ID for retrieval.
    """

    typeName = models.CharField(
        db_index=True,
        max_length=MAX_TYPENAME_LENGTH,
        verbose_name=_('Type name'),
        help_text=_(f('(max. {value} characters)', value=MAX_TYPENAME_LENGTH)),
    )

    primaryID = models.CharField(
        db_index=True,
        max_length=MAX_PRIMARYID_LENGTH,
        verbose_name=_('Primary ID'),
        help_text=_(f('(max. {value} characters)', value=MAX_PRIMARYID_LENGTH)),
    )

    def get_object_instance(self):
        """
        Returns actual object instance for current ObjectID instance.
        """
        instance = None
        try:
            # TODO: add registry of type names to models.py and ensure only
            #   those are used for typeName. Furthermore, verify that the
            #   given primaryID does not contain ')'.

            _code = '{0}.objects.get(id={1})'.format(self.typeName, self.primaryID)

            # Hack for Python 3.5.2
            from EvalData.models import (
                DataAssessmentTask,
                DirectAssessmentTask,
                DirectAssessmentContextTask,
                DirectAssessmentDocumentTask,
                MultiModalAssessmentTask,
                PairwiseAssessmentDocumentTask,
                PairwiseAssessmentTask,
            )

            instance = eval(_code)

        except:
            _msg = 'ObjectID {0}.{1} invalid'.format(self.typeName, self.primaryID)
            LOGGER.warn(_msg)
            LOGGER.warn(format_exc())

        finally:
            return instance

    def __str__(self):
        return str(self.id) + '.' + self.typeName + '.' + self.primaryID


class AnnotationTaskRegistry:
    """
    Keeps a registry of known annotation task types.

    Use @AnnotationTaskRegistry.register decorator to register class.
    """

    _ANNOTATION_TASK_REGISTRY = set()  # type: Set[str]

    @staticmethod
    def register(obj):
        """
        Add annotation task type to registry.
        """
        _name = obj.__name__
        AnnotationTaskRegistry._ANNOTATION_TASK_REGISTRY.add(_name)
        return obj

    @staticmethod
    def get_types():
        """
        Get annotation task types in registry.
        """
        return AnnotationTaskRegistry._ANNOTATION_TASK_REGISTRY


# pylint: disable=C0103,R0903
class BaseMetadata(models.Model):
    """
    Abstract base metadata for all object models.
    """

    dateCreated = models.DateTimeField(
        auto_now_add=True, editable=False, verbose_name=_('Date created')
    )

    dateActivated = models.DateTimeField(
        blank=True, null=True, verbose_name=_('Date activated')
    )

    dateCompleted = models.DateTimeField(
        blank=True, null=True, verbose_name=_('Date completed')
    )

    dateRetired = models.DateTimeField(
        blank=True, null=True, verbose_name=_('Date retired')
    )

    dateModified = models.DateTimeField(
        blank=True, null=True, verbose_name=_('Date modified')
    )

    activated = models.BooleanField(
        blank=True,
        db_index=True,
        default=False,
        verbose_name=_('Activated?'),
    )

    completed = models.BooleanField(
        blank=True,
        db_index=True,
        default=False,
        verbose_name=_('Completed?'),
    )

    retired = models.BooleanField(
        blank=True,
        db_index=True,
        default=False,
        verbose_name=_('Retired?'),
    )

    createdBy = models.ForeignKey(
        User,
        db_index=True,
        on_delete=models.PROTECT,
        editable=False,
        related_name='%(app_label)s_%(class)s_created_by',
        related_query_name="%(app_label)s_%(class)ss",
        verbose_name=_('Created by'),
    )

    activatedBy = models.ForeignKey(
        User,
        blank=True,
        db_index=True,
        on_delete=models.PROTECT,
        editable=False,
        null=True,
        related_name='%(app_label)s_%(class)s_activated_by',
        related_query_name="%(app_label)s_%(class)ss",
        verbose_name=_('Activated by'),
    )

    completedBy = models.ForeignKey(
        User,
        blank=True,
        db_index=True,
        on_delete=models.PROTECT,
        editable=False,
        null=True,
        related_name='%(app_label)s_%(class)s_completed_by',
        related_query_name="%(app_label)s_%(class)ss",
        verbose_name=_('Completed by'),
    )

    retiredBy = models.ForeignKey(
        User,
        blank=True,
        db_index=True,
        on_delete=models.PROTECT,
        editable=False,
        null=True,
        related_name='%(app_label)s_%(class)s_retired_by',
        related_query_name="%(app_label)s_%(class)ss",
        verbose_name=_('Retired by'),
    )

    modifiedBy = models.ForeignKey(
        User,
        blank=True,
        db_index=True,
        on_delete=models.PROTECT,
        editable=False,
        null=True,
        related_name='%(app_label)s_%(class)s_modified_by',
        related_query_name="%(app_label)s_%(class)ss",
        verbose_name=_('Modified by'),
    )

    rawData = models.TextField(blank=True, editable=False, verbose_name=_('Raw data'))

    _str_name = models.TextField(blank=True, default="", editable=False)

    # pylint: disable=C0111
    class Meta:
        abstract = True
        ordering = ['_str_name']

    def _set_boolean_states(self, activated, completed, retired):
        """
        Sets boolean states for current model instance.
        Also sets respective dates for all three states.
        """
        utc_now = datetime.utcnow().replace(tzinfo=utc)

        self.activated = activated
        self.dateActivated = utc_now if activated else None

        self.completed = completed
        self.dateCompleted = utc_now if completed else None

        self.retired = retired
        self.dateRetired = utc_now if retired else None

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

    def _generate_str_name(self):
        """
        Generate human readable name for use with __str__().
        """
        return '{0}[{1}]'.format(self.__class__.__name__, self.id)

    def save(self, *args, **kwargs):
        """
        For object instances with an ID, we precompute the _str_name
        attribute so that future __str__() lookups are efficient.

        Also, we ensure that a matching ObjectID binding is created.
        """
        if self.id:
            _new_name = self._generate_str_name()
            if self._str_name != _new_name:
                self._str_name = _new_name

            qs = ObjectID.objects.filter(
                typeName=self.__class__.__name__, primaryID=self.id
            )
            if not qs.exists():
                _serialized = ObjectID.objects.create(
                    typeName=self.__class__.__name__, primaryID=self.id
                )
                _msg = 'Created serialized ObjectID:{0}'.format(_serialized.id)
                LOGGER.info(_msg)

        super(BaseMetadata, self).save(*args, **kwargs)

    # pylint: disable=E1136
    def __str__(self):
        if self._str_name == "":
            # This will populate self._str_name
            self.save()

        return self._str_name


class BaseAssessmentResult(BaseMetadata):
    """
    Abstract base class for assessment result.
    """

    sourceErrors = models.TextField(
        blank=True,
        help_text=_(f('(max. {value} characters)', value=MAX_SEGMENTTEXT_LENGTH)),
        max_length=MAX_SEGMENTTEXT_LENGTH,
        null=True,
        verbose_name=_('Source errors'),
    )

    errors = models.TextField(
        blank=True,
        help_text=_(f('(max. {value} characters)', value=MAX_SEGMENTTEXT_LENGTH)),
        max_length=MAX_SEGMENTTEXT_LENGTH,
        null=True,
        verbose_name=_('Errors'),
    )

    class Meta:
        abstract = True


class BasePairwiseAssessmentResult(BaseMetadata):
    """
    Abstract base class for pairwise assessment result.
    """

    sourceErrors = models.TextField(
        blank=True,
        help_text=_(f('(max. {value} characters)', value=MAX_SEGMENTTEXT_LENGTH)),
        max_length=MAX_SEGMENTTEXT_LENGTH,
        null=True,
        verbose_name=_('Source errors'),
    )

    errors1 = models.TextField(
        blank=True,
        help_text=_(f('(max. {value} characters)', value=MAX_SEGMENTTEXT_LENGTH)),
        max_length=MAX_SEGMENTTEXT_LENGTH,
        null=True,
        verbose_name=_('Errors (1)'),
    )

    errors2 = models.TextField(
        blank=True,
        help_text=_(f('(max. {value} characters)', value=MAX_SEGMENTTEXT_LENGTH)),
        max_length=MAX_SEGMENTTEXT_LENGTH,
        null=True,
        verbose_name=_('Errors (2)'),
    )

    class Meta:
        abstract = True


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
        unique=True,
    )

    sourceLanguageCode = models.CharField(
        max_length=MAX_LANGUAGECODE_LENGTH,
        verbose_name=_('Source language'),
        help_text=_(f('(max. {value} characters)', value=MAX_LANGUAGECODE_LENGTH)),
    )

    targetLanguageCode = models.CharField(
        max_length=MAX_LANGUAGECODE_LENGTH,
        verbose_name=_('Target language'),
        help_text=_(f('(max. {value} characters)', value=MAX_LANGUAGECODE_LENGTH)),
    )

    domainName = models.CharField(
        max_length=MAX_DOMAINNAME_LENGTH,
        verbose_name=_('Domain name'),
        help_text=_(f('(max. {value} characters)', value=MAX_DOMAINNAME_LENGTH)),
    )

    def clean_fields(self, exclude=None):
        """
        Verifies that desired marketID is still available.
        """
        _new_marketID = '{0}_{1}_{2}'.format(
            self.sourceLanguageCode,
            self.targetLanguageCode,
            self.domainName,
        )

        _market_instance = Market.objects.filter(marketID=_new_marketID)
        if _market_instance.exists():
            raise ValidationError(
                _(
                    f(
                        'Market with identical marketID ("{mID}") already exists.',
                        mID=_new_marketID,
                    )
                )
            )

        super(Market, self).clean_fields(exclude)

    def save(self, *args, **kwargs):
        _new_marketID = '{0}_{1}_{2}'.format(
            self.sourceLanguageCode,
            self.targetLanguageCode,
            self.domainName,
        )
        self.marketID = _new_marketID

        super(Market, self).save(*args, **kwargs)

    # TODO: what is this used for? Candidate for deprecation/removal.
    #
    # pylint: disable=E1101
    def my_is_valid(self):
        """
        Validates the current Market instance, checking marketID uniqueness.
        """
        _expected_marketID = '{0}_{1}_{2}'.format(
            self.sourceLanguageCode,
            self.targetLanguageCode,
            self.domainName,
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

    def _generate_str_name(self):
        return self.marketID


class Metadata(BaseMetadata):
    """
    Models metadata associated to tasks.
    """

    market = models.ForeignKey(Market, db_index=True, on_delete=models.PROTECT)

    corpusName = models.CharField(
        max_length=MAX_CORPUSNAME_LENGTH,
        verbose_name=_('Corpus name'),
        help_text=_(f('(max. {value} characters)', value=MAX_CORPUSNAME_LENGTH)),
    )

    versionInfo = models.CharField(
        max_length=MAX_VERSIONINFO_LENGTH,
        verbose_name=_('Version info'),
        help_text=_(f('(max. {value} characters)', value=MAX_VERSIONINFO_LENGTH)),
    )

    source = models.CharField(
        max_length=MAX_SOURCE_LENGTH,
        verbose_name=_('Source'),
        help_text=_(f('(max. {value} characters)', value=MAX_SOURCE_LENGTH)),
    )

    class Meta:
        ordering = ['_str_name']
        verbose_name = 'Metadata record'

    def _generate_str_name(self):
        return '{0}->{1}/{2}["{3}"]'.format(
            self.market.sourceLanguageCode,
            self.market.targetLanguageCode,
            self.corpusName,
            self.versionInfo,
        )


class EvalItem(BaseMetadata):
    """
    Abstract base class for evaluation data items.

    Models corresponding, 1-based, integer ID and metadata.
    """

    itemID = models.PositiveIntegerField(
        verbose_name=_('Item ID'), help_text=_('(1-based)')
    )

    itemType = models.CharField(
        choices=SET_ITEMTYPE_CHOICES,
        db_index=True,
        max_length=MAX_ITEMTYPE_LENGTH,
        verbose_name=_('Item type'),
    )

    metadata = models.ForeignKey(Metadata, db_index=True, on_delete=models.PROTECT)

    # pylint: disable=C0111,R0903
    class Meta:
        abstract = True
        ordering = ['_str_name']

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

    def _generate_str_name(self):
        return '{0}.{1}[{2}]'.format(
            self.__class__.__name__, self.metadata, self.itemID
        )


class TextSegment(EvalItem):
    """
    Models a single text segment.
    """

    segmentID = models.CharField(
        max_length=MAX_SEGMENTID_LENGTH,
        verbose_name=_('Segment ID'),
        help_text=_(f('(max. {value} characters)', value=MAX_SEGMENTID_LENGTH)),
    )

    segmentText = models.TextField(
        max_length=MAX_SEGMENTTEXT_LENGTH,
        verbose_name=_('Segment text'),
        help_text=_(f('(max. {value} characters)', value=MAX_SEGMENTTEXT_LENGTH)),
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
        help_text=_(f('(max. {value} characters)', value=MAX_SEGMENTID_LENGTH)),
    )

    sourceText = models.TextField(
        blank=True,
        verbose_name=_('Source text'),
    )

    targetID = models.CharField(
        max_length=MAX_SEGMENTID_LENGTH,
        verbose_name=_('Target ID'),
        help_text=_(f('(max. {value} characters)', value=MAX_SEGMENTID_LENGTH)),
    )

    targetText = models.TextField(
        blank=True,
        verbose_name=_('Target text'),
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


class TextSegmentWithTwoTargets(TextSegment):
    """
    Models a text segment with one or two sub-segments.
    """

    target1ID = models.CharField(
        max_length=MAX_SEGMENTID_LENGTH,
        verbose_name=_('Item ID (1)'),
        help_text=_(f('(max. {value} characters)', value=MAX_SEGMENTID_LENGTH)),
    )

    target1Text = models.TextField(
        blank=True,
        verbose_name=_('Text (1)'),
    )

    target2ID = models.CharField(
        null=True,
        max_length=MAX_SEGMENTID_LENGTH,
        verbose_name=_('Item ID (2)'),
        help_text=_(f('(max. {value} characters)', value=MAX_SEGMENTID_LENGTH)),
    )

    target2Text = models.TextField(
        blank=True,
        null=True,
        verbose_name=_('Text (2)'),
    )

    # Source sentence context
    contextLeft = models.TextField(
        blank=True, null=True, verbose_name=_('Context (left)')
    )

    contextRight = models.TextField(
        blank=True, null=True, verbose_name=_('Context (right)')
    )

    target1ContextLeft = models.TextField(
        blank=True, null=True, verbose_name=_('Target context (1)')
    )

    target2ContextLeft = models.TextField(
        blank=True, null=True, verbose_name=_('Target context (2)')
    )

    def has_context(self):
        """Checks if the current segment has context provided."""
        return self.contextLeft or self.contextRight

    def context_left(self, last=5, separator=' '):
        """
        Returns formatted last 5 sentences from the left context.
        Use separator='<br>' to show one sentence per line.
        """
        return (
            separator.join(self.contextLeft.split('\n')[-last:])
            if self.contextLeft
            else ''
        )

    def context_right(self, first=5, separator=' '):
        """
        Returns formatted first 5 sentences from the right context.
        Use separator='<br>' to show one sentence per line.
        """
        return (
            separator.join(self.contextRight.split('\n')[:first])
            if self.contextRight
            else ''
        )

    def target_texts_with_diffs(self):
        """
        Returns the pair of texts with HTML tags highlighting token differences.
        Both texts must be non empty.
        HTML tags in both texts will be escaped automatically.

        For example,
            'a b c d e' and 'a B c e f'
        will become:
            'a <span class="diff diff-sub">b</span> c <span class="diff diff-del">d</span> e',
            'a <span class="diff diff-sub">B</span> c e <span class="diff diff-ins">f</span>'
        """
        if not self.target1Text or not self.target2Text:
            return (self.target1Text, self.target2Text)

        toks1 = escape(self.target1Text).split()
        toks2 = escape(self.target2Text).split()
        matcher = SequenceMatcher(None, toks1, toks2)

        text1 = ''
        text2 = ''
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == 'equal':
                text1 += ' ' + ' '.join(toks1[i1:i2])
                text2 += ' ' + ' '.join(toks2[j1:j2])
            elif tag == 'replace':
                text1 += (
                    ' <span class="diff diff-sub">' + ' '.join(toks1[i1:i2]) + '</span>'
                )
                text2 += (
                    ' <span class="diff diff-sub">' + ' '.join(toks2[j1:j2]) + '</span>'
                )
            elif tag == 'insert':
                text2 += (
                    ' <span class="diff diff-ins">' + ' '.join(toks2[j1:j2]) + '</span>'
                )
            elif tag == 'delete':
                text1 += (
                    ' <span class="diff diff-del">' + ' '.join(toks1[i1:i2]) + '</span>'
                )
        return (text1.strip(), text2.strip())

    # pylint: disable=E1101
    def is_valid(self):
        """
        Validates the current TextSegmentWithTwoTargets instance, checking
        text.
        """
        if isinstance(self.target1Text, type('This is a test sentence.')):
            return False

        _len = len(self.target1Text)
        if _len < 1 or _len > MAX_SEGMENTTEXT_LENGTH:
            return False

        if target2Text and len(target2Text) > 0:
            if isinstance(self.target2Text, type('This is a test sentence.')):
                return False

            _len = len(self.target2Text)
            if _len < 1 or _len > MAX_SEGMENTTEXT_LENGTH:
                return False

            # Texts must be different
            if self.target1Text == self.target2Text:
                return False

        return super(TextSegmentWithTwoTargets, self).is_valid()
