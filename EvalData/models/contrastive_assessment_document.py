"""
Appraise evaluation framework

See LICENSE for usage details
"""

# pylint: disable=C0103,C0330,no-member
import sys
from collections import defaultdict
from json import loads
from zipfile import is_zipfile
from zipfile import ZipFile

from django.contrib.auth.models import User
from django.db import models
from django.utils.text import format_lazy as f
from django.utils.translation import gettext_lazy as _

from Appraise.utils import _get_logger, _compute_user_total_annotation_time
from Dashboard.models import LANGUAGE_CODES_AND_NAMES
from EvalData.models.base_models import AnnotationTaskRegistry
from EvalData.models.base_models import BaseMetadata
from EvalData.models.base_models import MAX_REQUIREDANNOTATIONS_VALUE
from EvalData.models.base_models import MAX_SEGMENTID_LENGTH
from EvalData.models.base_models import TextSegment
from EvalData.models.base_models import seconds_to_timedelta

MAX_DOCUMENTID_LENGTH = 200

LOGGER = _get_logger(name=__name__)


class TextSegmentWithThreeTargetsWithContext(TextSegment):
    """
    Models a text segment with up to three target translations
    within a document context.
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

    target1ContextLeft = models.TextField(
        blank=True, null=True, verbose_name=_('Target context (1)')
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

    target2ContextLeft = models.TextField(
        blank=True, null=True, verbose_name=_('Target context (2)')
    )

    target3ID = models.CharField(
        null=True,
        max_length=MAX_SEGMENTID_LENGTH,
        verbose_name=_('Item ID (3)'),
        help_text=_(f('(max. {value} characters)', value=MAX_SEGMENTID_LENGTH)),
    )

    target3Text = models.TextField(
        blank=True,
        null=True,
        verbose_name=_('Text (3)'),
    )

    target3ContextLeft = models.TextField(
        blank=True, null=True, verbose_name=_('Target context (3)')
    )

    contextLeft = models.TextField(
        blank=True, null=True, verbose_name=_('Context (left)')
    )

    contextRight = models.TextField(
        blank=True, null=True, verbose_name=_('Context (right)')
    )

    documentID = models.CharField(
        max_length=MAX_DOCUMENTID_LENGTH,
        verbose_name=_('Document ID'),
        help_text=_(f('(max. {value} characters)', value=MAX_DOCUMENTID_LENGTH)),
    )

    isCompleteDocument = models.BooleanField(
        blank=True,
        db_index=True,
        default=False,
        verbose_name=_('Complete document?'),
    )

    def has_context(self):
        return self.contextLeft or self.contextRight

    def context_left(self, last=5, separator=' '):
        return (
            separator.join(self.contextLeft.split('\n')[-last:])
            if self.contextLeft
            else ''
        )

    def context_right(self, first=5, separator=' '):
        return (
            separator.join(self.contextRight.split('\n')[:first])
            if self.contextRight
            else ''
        )

    # pylint: disable=E1101
    def is_valid(self):
        return super(TextSegmentWithThreeTargetsWithContext, self).is_valid()

    def compute_pairwise_diff_maps(self, char_based=False):
        """
        Compute per-character diff maps for all 3 translation pairs.

        Returns a dict with 6 JSON-encoded diff map strings:
            "1vs2", "2vs1", "1vs3", "3vs1", "2vs3", "3vs2"
        Each value is a JSON array with one entry per character:
        null (no diff), "sub", "ins", or "del".
        """
        import json
        from EvalData.models.base_models import compute_char_diff_map

        t1 = self.target1Text or ''
        t2 = self.target2Text or ''
        t3 = self.target3Text or ''

        d1vs2, d2vs1 = compute_char_diff_map(t1, t2, char_based=char_based)
        d1vs3, d3vs1 = compute_char_diff_map(t1, t3, char_based=char_based)
        d2vs3, d3vs2 = compute_char_diff_map(t2, t3, char_based=char_based)

        return {
            'diff_1vs2': json.dumps(d1vs2),
            'diff_2vs1': json.dumps(d2vs1),
            'diff_1vs3': json.dumps(d1vs3),
            'diff_3vs1': json.dumps(d3vs1),
            'diff_2vs3': json.dumps(d2vs3),
            'diff_3vs2': json.dumps(d3vs2),
        }

@AnnotationTaskRegistry.register
class ContrastiveAssessmentDocumentTask(BaseMetadata):
    """
    Models a contrastive assessment document evaluation task
    supporting up to 3 system outputs at once.
    """

    campaign = models.ForeignKey(
        'Campaign.Campaign',
        db_index=True,
        on_delete=models.PROTECT,
        related_name='%(app_label)s_%(class)s_campaign',
        related_query_name="%(app_label)s_%(class)ss",
        verbose_name=_('Campaign'),
    )

    items = models.ManyToManyField(
        TextSegmentWithThreeTargetsWithContext,
        related_name='%(app_label)s_%(class)s_items',
        related_query_name="%(app_label)s_%(class)ss",
        verbose_name=_('Items'),
    )

    requiredAnnotations = models.PositiveSmallIntegerField(
        verbose_name=_('Required annotations'),
        help_text=_(
            f(
                '(value in range=[1,{value}])',
                value=MAX_REQUIREDANNOTATIONS_VALUE,
            )
        ),
    )

    assignedTo = models.ManyToManyField(
        User,
        blank=True,
        db_index=True,
        related_name='%(app_label)s_%(class)s_assignedTo',
        related_query_name="%(app_label)s_%(class)ss",
        verbose_name=_('Assigned to'),
        help_text=_('(users working on this task)'),
    )

    batchNo = models.PositiveIntegerField(
        verbose_name=_('Batch number'), help_text=_('(1-based)')
    )

    batchData = models.ForeignKey(
        'Campaign.CampaignData',
        on_delete=models.PROTECT,
        blank=True,
        db_index=True,
        null=True,
        related_name='%(app_label)s_%(class)s_batchData',
        related_query_name="%(app_label)s_%(class)ss",
        verbose_name=_('Batch data'),
    )

    def dataName(self):
        return str(self.batchData)

    def marketName(self):
        return str(self.items.first().metadata.market)

    def marketSourceLanguage(self):
        tokens = str(self.items.first().metadata.market).split('_')
        if len(tokens) == 3 and tokens[0] in LANGUAGE_CODES_AND_NAMES.keys():
            return LANGUAGE_CODES_AND_NAMES[tokens[0]]
        return None

    def marketSourceLanguageCode(self):
        tokens = str(self.items.first().metadata.market).split('_')
        if len(tokens) == 3 and tokens[0] in LANGUAGE_CODES_AND_NAMES.keys():
            return tokens[0]
        return None

    def marketTargetLanguage(self):
        tokens = str(self.items.first().metadata.market).split('_')
        if len(tokens) == 3 and tokens[1] in LANGUAGE_CODES_AND_NAMES.keys():
            return LANGUAGE_CODES_AND_NAMES[tokens[1]]
        return None

    def marketTargetLanguageCode(self):
        tokens = str(self.items.first().metadata.market).split('_')
        if len(tokens) == 3 and tokens[1] in LANGUAGE_CODES_AND_NAMES.keys():
            return tokens[1]
        return None

    def completed_items_for_user(self, user):
        results = ContrastiveAssessmentDocumentResult.objects.filter(
            task=self, activated=False, completed=True, createdBy=user
        ).values_list('item_id', flat=True)

        return len(set(results))

    def is_trusted_user(self, user):
        from Campaign.models import TrustedUser

        trusted_user = TrustedUser.objects.filter(user=user, campaign=self.campaign)
        return trusted_user.exists()

    def next_item_for_user(self, user, return_completed_items=False):
        trusted_user = self.is_trusted_user(user)

        next_item = None
        completed_items = 0
        for item in self.items.all().order_by('id'):
            result = ContrastiveAssessmentDocumentResult.objects.filter(
                item=item, activated=False, completed=True, createdBy=user
            )

            if not result.exists():
                print(
                    'Identified next item: {}/{} (itemID={}) for trusted={}'.format(
                        item.id, item.itemType, item.itemID, trusted_user
                    )
                )
                if not trusted_user or item.itemType == 'TGT':
                    next_item = item
                    break

            completed_items += 1

        if not next_item:
            LOGGER.info('No next item found for task {0}'.format(self.id))
            annotations = ContrastiveAssessmentDocumentResult.objects.filter(
                task=self, activated=False, completed=True
            ).values_list('item_id', flat=True)
            uniqueAnnotations = len(set(annotations))

            required_user_results = 100
            if trusted_user:
                required_user_results = 70

            _total_required = self.requiredAnnotations * required_user_results
            LOGGER.info(
                'Unique annotations={0}/{1}'.format(uniqueAnnotations, _total_required)
            )
            if uniqueAnnotations >= _total_required:
                LOGGER.info('Completing task {0}'.format(self.id))
                self.complete()
                self.save()

        if return_completed_items:
            return (next_item, completed_items)

        return next_item

    def next_document_for_user(self, user, return_statistics=True):
        """Returns the next item and all items from its document."""
        (
            next_item,
            completed_items,
        ) = self.next_item_for_user(user, return_completed_items=True)

        if not next_item:
            if not return_statistics:
                return (next_item, [], [])
            return (next_item, completed_items, 0, 0, [], [], 0)

        _items = self.items.filter(
            documentID=next_item.documentID,
        ).order_by('id')

        block_items = []
        current_block = False
        for item in _items:
            block_items.append(item)
            if item.id == next_item.id:
                current_block = True
            if item.isCompleteDocument:
                if current_block:
                    break
                block_items.clear()

        block_results = self.get_results_for_each_item(block_items, user)

        if not return_statistics:
            return (next_item, block_items, block_results)

        completed_items_in_block = len(
            [res for res in block_results if res is not None]
        )
        completed_blocks = ContrastiveAssessmentDocumentResult.objects.filter(
            task=self,
            item__isCompleteDocument=True,
            completed=True,
            createdBy=user,
        ).count()
        total_blocks = self.items.filter(isCompleteDocument=True).count()

        print(
            'Completed {}/{} documents, {}/{} items in the current document, completed {} items in total'.format(
                completed_blocks,
                total_blocks,
                completed_items_in_block,
                len(block_items),
                completed_items,
            )
        )

        return (
            next_item,
            completed_items,
            completed_blocks,
            completed_items_in_block,
            block_items,
            block_results,
            total_blocks,
        )

    def get_results_for_each_item(self, block_items, user):
        """Returns the latest result object for each item or none."""
        block_results = []

        for item in block_items:
            result = (
                ContrastiveAssessmentDocumentResult.objects.filter(
                    item__id=item.id,
                    completed=True,
                    createdBy=user,
                    task=self,
                )
                .order_by('item__id', 'dateModified')
                .first()
            )
            block_results.append(result)

        if len(block_items) != len(block_results):
            print('Warning: incorrect number of retrieved results!')
        for item, result in zip(block_items, block_results):
            if result and item.id != result.item.id:
                print('Warning: incorrect order of items and results!')

        return block_results

    @classmethod
    def get_task_for_user(cls, user):
        for active_task in cls.objects.filter(
            assignedTo=user, activated=True, completed=False
        ).order_by('-id'):
            next_item = active_task.next_item_for_user(user)
            if next_item is not None:
                return active_task

        return None

    @classmethod
    def get_next_free_task_for_language(cls, code, campaign=None, user=None):
        active_tasks = cls.objects.filter(
            activated=True,
            completed=False,
            items__metadata__market__targetLanguageCode=code,
        )

        if campaign:
            active_tasks = active_tasks.filter(campaign=campaign)

        for active_task in active_tasks.order_by('id'):
            active_users = active_task.assignedTo.count()
            if active_users < active_task.requiredAnnotations:
                if user and not user in active_task.assignedTo.all():
                    return active_task

        return None

    @classmethod
    def get_next_free_task_for_language_and_campaign(cls, code, campaign):
        return cls.get_next_free_task_for_language(code, campaign)

    @classmethod
    def import_from_json(cls, campaign, batch_user, batch_data, max_count):
        """
        Creates new ContrastiveAssessmentDocumentTask instances based on JSON input.
        """
        batch_meta = batch_data.metadata
        batch_name = batch_data.dataFile.name
        batch_file = batch_data.dataFile
        batch_json = None

        if batch_name.endswith('.zip'):
            if not is_zipfile(batch_file):
                _msg = 'Batch {0} not a valid ZIP archive'.format(batch_name)
                LOGGER.warn(_msg)
                return

            batch_zip = ZipFile(batch_file)
            batch_json_files = [x for x in batch_zip.namelist() if x.endswith('.json')]
            for batch_json_file in batch_json_files:
                batch_content = batch_zip.read(batch_json_file).decode('utf-8')
                if sys.version_info >= (3, 9, 0):
                    batch_json = loads(batch_content)
                else:
                    batch_json = loads(batch_content, encoding='utf-8')

        else:
            batch_json = loads(str(batch_file.read(), encoding='utf-8'))

        from datetime import datetime

        t1 = datetime.now()

        current_count = 0
        max_length_id = 0
        max_length_text = 0
        for batch_task in batch_json:
            if max_count > 0 and current_count >= max_count:
                _msg = 'Stopping after max_count={0} iterations'.format(max_count)
                LOGGER.info(_msg)

                t2 = datetime.now()
                print(t2 - t1)
                return

            print('Loading batch:', batch_name, batch_task['task']['batchNo'])

            doc_items = 0
            new_items = []
            count_items = 0
            for item in batch_task['items']:
                count_items += 1

                current_length_id = len(item['segmentID'])
                current_length_text = len(item['segmentText'])

                if current_length_id > max_length_id:
                    print(f"New max segmentID length, max={current_length_id}, id={item['segmentID']}")
                    max_length_id = current_length_id

                if current_length_text > max_length_text:
                    print(f"New max segmentText length, max={current_length_text}, id={item['segmentID']}")
                    max_length_text = current_length_text

                item_targets = item['targets']

                item_tgt1_idx = item_targets[0]['targetID']
                item_tgt1_txt = item_targets[0]['targetText']
                item_tgt1_ctx = item_targets[0].get('targetContextLeft', '')

                item_tgt2_idx = None
                item_tgt2_txt = None
                item_tgt2_ctx = None
                if len(item_targets) > 1:
                    item_tgt2_idx = item_targets[1]['targetID']
                    item_tgt2_txt = item_targets[1]['targetText']
                    item_tgt2_ctx = item_targets[1].get('targetContextLeft', '')

                item_tgt3_idx = None
                item_tgt3_txt = None
                item_tgt3_ctx = None
                if len(item_targets) > 2:
                    item_tgt3_idx = item_targets[2]['targetID']
                    item_tgt3_txt = item_targets[2]['targetText']
                    item_tgt3_ctx = item_targets[2].get('targetContextLeft', '')

                new_item = TextSegmentWithThreeTargetsWithContext(
                    segmentID=item['segmentID'],
                    segmentText=item['segmentText'],
                    contextLeft=item.get('segmentContextLeft', ''),
                    target1ID=item_tgt1_idx,
                    target1Text=item_tgt1_txt,
                    target1ContextLeft=item_tgt1_ctx,
                    target2ID=item_tgt2_idx,
                    target2Text=item_tgt2_txt,
                    target2ContextLeft=item_tgt2_ctx,
                    target3ID=item_tgt3_idx,
                    target3Text=item_tgt3_txt,
                    target3ContextLeft=item_tgt3_ctx,
                    createdBy=batch_user,
                    itemID=item['itemID'],
                    itemType=item['itemType'],
                    documentID=item['documentID'],
                    isCompleteDocument=item['isCompleteDocument'],
                )
                new_items.append(new_item)
                if item['isCompleteDocument']:
                    doc_items += 1

            LOGGER.info(f'The task has {len(new_items)} items')
            current_count += 1

            for new_item in new_items:
                new_item.metadata = batch_meta
                new_item.save()

            new_task = ContrastiveAssessmentDocumentTask(
                campaign=campaign,
                requiredAnnotations=batch_task['task']['requiredAnnotations'],
                batchNo=batch_task['task']['batchNo'],
                batchData=batch_data,
                createdBy=batch_user,
            )
            new_task.save()

            new_task.items.add(*new_items)
            new_task.save()

            _msg = 'Success processing batch {0}, task {1}'.format(
                str(batch_data), batch_task['task']['batchNo']
            )
            LOGGER.info(_msg)

        print(f"Max length ID={max_length_id}, text={max_length_text}")

        t2 = datetime.now()
        print(f"Total processing time: {t2 - t1}")

    # pylint: disable=E1101
    def is_valid(self):
        if not hasattr(self, 'campaign') or not self.campaign.is_valid():
            return False

        if not hasattr(self, 'items'):
            return False

        for item in self.items:
            if not item.is_valid():
                return False

        return True

    def _generate_str_name(self):
        return '{0}.{1}[{2}]'.format(self.__class__.__name__, self.campaign, self.id)


class ContrastiveAssessmentDocumentResult(BaseMetadata):
    """
    Models a contrastive assessment document evaluation result
    supporting up to 3 system outputs.
    """

    score1 = models.PositiveSmallIntegerField(
        verbose_name=_('Score (1)'),
        help_text=_('(value in range=[1,100])'),
    )

    score2 = models.PositiveSmallIntegerField(
        blank=True,
        null=True,
        verbose_name=_('Score (2)'),
        help_text=_('(value in range=[1,100])'),
    )

    score3 = models.PositiveSmallIntegerField(
        blank=True,
        null=True,
        verbose_name=_('Score (3)'),
        help_text=_('(value in range=[1,100])'),
    )

    mqm1 = models.TextField(
        verbose_name=_('MQM (1)'), help_text=_('MQM JSON string'), default="[]"
    )

    mqm2 = models.TextField(
        verbose_name=_('MQM (2)'), help_text=_('MQM JSON string'), default="[]"
    )

    mqm3 = models.TextField(
        verbose_name=_('MQM (3)'), help_text=_('MQM JSON string'), default="[]"
    )

    sourceErrors = models.TextField(
        blank=True,
        max_length=2000,
        null=True,
        verbose_name=_('Source errors'),
    )

    errors1 = models.TextField(
        blank=True,
        max_length=2000,
        null=True,
        verbose_name=_('Errors (1)'),
    )

    errors2 = models.TextField(
        blank=True,
        max_length=2000,
        null=True,
        verbose_name=_('Errors (2)'),
    )

    errors3 = models.TextField(
        blank=True,
        max_length=2000,
        null=True,
        verbose_name=_('Errors (3)'),
    )

    comment = models.TextField(
        verbose_name=_('Comment'),
        help_text=_('Annotator comment'),
        blank=True,
        default='',
    )

    start_time = models.FloatField(
        verbose_name=_('Start time'), help_text=_('(in seconds)')
    )

    end_time = models.FloatField(
        verbose_name=_('End time'), help_text=_('(in seconds)')
    )

    browser_info = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name=_('Browser info'),
        help_text=_('(browser type and version when available)'),
    )

    item = models.ForeignKey(
        TextSegmentWithThreeTargetsWithContext,
        db_index=True,
        on_delete=models.PROTECT,
        related_name='%(app_label)s_%(class)s_item',
        related_query_name="%(app_label)s_%(class)ss",
        verbose_name=_('Item'),
    )

    task = models.ForeignKey(
        ContrastiveAssessmentDocumentTask,
        blank=True,
        db_index=True,
        null=True,
        on_delete=models.PROTECT,
        related_name='%(app_label)s_%(class)s_task',
        related_query_name="%(app_label)s_%(class)ss",
        verbose_name=_('Task'),
    )

    # pylint: disable=E1136
    def _generate_str_name(self):
        return '{0}.{1}={2}+{3}+{4}'.format(
            self.__class__.__name__,
            self.item,
            self.score1,
            self.score2,
            self.score3,
        )

    def duration(self):
        d = self.end_time - self.start_time
        return round(d, 1)

    def item_type(self):
        return self.item.itemType

    @classmethod
    def get_completed_for_user(cls, user, unique_only=True):
        _query = cls.objects.filter(createdBy=user, activated=False, completed=True)
        if unique_only:
            return _query.values_list('item__id').distinct().count()
        return _query.count()

    @classmethod
    def get_hit_status_for_user(cls, user):
        user_data = defaultdict(int)

        for user_item in cls.objects.filter(
            createdBy=user, activated=False, completed=True
        ).values_list('task__id', 'item__itemType'):
            if user_item[1].lower() != 'tgt':
                continue

            user_data[user_item[0]] += 1

        total_hits = len(user_data.keys())
        completed_hits = len([x for x in user_data.values() if x >= 70])

        return (completed_hits, total_hits)

    @classmethod
    def get_time_for_user(cls, user):
        results = cls.objects.filter(createdBy=user, activated=False, completed=True)

        timestamps = []
        for result in results:
            timestamps.append((result.start_time, result.end_time))

        return seconds_to_timedelta(_compute_user_total_annotation_time(timestamps))

    @classmethod
    def get_system_annotations(cls):
        system_scores = defaultdict(list)

        value_types = ('TGT', 'CHK')
        qs = cls.objects.filter(completed=True, item__itemType__in=value_types)

        value_names = (
            'item__target1ID',
            'score1',
            'item__target2ID',
            'score2',
            'item__target3ID',
            'score3',
            'createdBy',
            'item__itemID',
            'item__metadata__market__sourceLanguageCode',
            'item__metadata__market__targetLanguageCode',
        )
        for result in qs.values_list(*value_names):
            systemID = result[0]
            score1 = result[1]
            score2 = result[3]
            score3 = result[5]
            annotatorID = result[6]
            segmentID = result[7]
            marketID = '{0}-{1}'.format(result[8], result[9])
            system_scores[marketID].append(
                (systemID, annotatorID, segmentID, score1, score2, score3)
            )

        return system_scores

    @classmethod
    def compute_accurate_group_status(cls):
        from Dashboard.models import LANGUAGE_CODES_AND_NAMES

        user_status = defaultdict(list)
        qs = cls.objects.filter(completed=True)

        value_names = ('createdBy', 'item__itemType', 'task__id')
        for result in qs.values_list(*value_names):
            if result[1].lower() != 'tgt':
                continue

            annotatorID = result[0]
            taskID = result[2]
            user_status[annotatorID].append(taskID)

        group_status = defaultdict(list)
        for annotatorID in user_status:
            user = User.objects.get(pk=annotatorID)
            usergroups = ';'.join(
                [
                    x.name
                    for x in user.groups.all()
                    if not x.name in LANGUAGE_CODES_AND_NAMES.keys()
                ]
            )
            if not usergroups:
                usergroups = 'NoGroupInfo'

            group_status[usergroups].extend(user_status[annotatorID])

        group_hits = {}
        for group_name in group_status:
            task_ids = set(group_status[group_name])
            completed_tasks = 0
            for task_id in task_ids:
                if group_status[group_name].count(task_id) >= 70:
                    completed_tasks += 1

            group_hits[group_name] = (completed_tasks, len(task_ids))

        return group_hits

    @classmethod
    def get_system_data(
        cls,
        campaign_id,
        extended_csv=False,
        expand_multi_sys=True,
        include_inactive=False,
        add_batch_info=False,
    ):
        system_data = []

        item_types = ('TGT', 'CHK')
        if extended_csv:
            item_types += ('BAD', 'REF')

        qs = cls.objects.filter(completed=True, item__itemType__in=item_types)

        if campaign_id:
            qs = qs.filter(task__campaign__id=campaign_id)

        if not include_inactive:
            qs = qs.filter(createdBy__is_active=True)

        attributes_to_extract = (
            'createdBy__username',       # 0 User ID
            'item__target1ID',           # 1 System ID 1
            'item__target2ID',           # 2 System ID 2
            'item__target3ID',           # 3 System ID 3
            'item__itemID',              # 4 Segment ID
            'item__itemType',            # 5 Item type
            'item__metadata__market__sourceLanguageCode',  # 6
            'item__metadata__market__targetLanguageCode',  # 7
            'score1',                    # 8
            'score2',                    # 9
            'score3',                    # 10
            'item__documentID',          # 11
            'item__isCompleteDocument',   # 12
            'mqm1',                      # 13
            'mqm2',                      # 14
            'mqm3',                      # 15
        )

        if extended_csv:
            attributes_to_extract = attributes_to_extract + (
                'start_time',
                'end_time',
            )

        if add_batch_info:
            attributes_to_extract = attributes_to_extract + (
                'task__batchNo',
                'item_id',
            )

        for _result in qs.values_list(*attributes_to_extract):
            results = [
                (
                    _result[0],   # user
                    _result[1],   # target1ID
                    _result[4],   # itemID
                    _result[5],   # itemType
                    _result[6],   # sourceLanguageCode
                    _result[7],   # targetLanguageCode
                    _result[8],   # score1
                    _result[11],  # documentID
                    _result[12],  # isCompleteDocument
                    _result[13],  # mqm1
                    *_result[16:],
                ),
                (
                    _result[0],   # user
                    _result[2],   # target2ID
                    _result[4],   # itemID
                    _result[5],   # itemType
                    _result[6],   # sourceLanguageCode
                    _result[7],   # targetLanguageCode
                    _result[9],   # score2
                    _result[11],  # documentID
                    _result[12],  # isCompleteDocument
                    _result[14],  # mqm2
                    *_result[16:],
                ),
                (
                    _result[0],   # user
                    _result[3],   # target3ID
                    _result[4],   # itemID
                    _result[5],   # itemType
                    _result[6],   # sourceLanguageCode
                    _result[7],   # targetLanguageCode
                    _result[10],  # score3
                    _result[11],  # documentID
                    _result[12],  # isCompleteDocument
                    _result[15],  # mqm3
                    *_result[16:],
                ),
            ]

            if add_batch_info:
                results[0] = (*results[0], 0)
                results[1] = (*results[1], 1)
                results[2] = (*results[2], 2)

            for result in results:
                if result[1] is None:
                    continue

                user_id = result[0]
                sys_ids = result[1]

                if expand_multi_sys:
                    system_ids = sys_ids.split('+')
                    for system_id in system_ids:
                        data = (user_id,) + (system_id,) + result[2:]
                        system_data.append(data)
                else:
                    data = (user_id,) + (sys_ids,) + result[2:]
                    system_data.append(data)

        return system_data

    @classmethod
    def dump_all_results_to_csv_file(cls, csv_file):
        from Dashboard.models import LANGUAGE_CODES_AND_NAMES

        system_scores = defaultdict(list)
        user_data = {}
        qs = cls.objects.filter(completed=True)

        value_names = (
            'item__target1ID',
            'score1',
            'item__target2ID',
            'score2',
            'item__target3ID',
            'score3',
            'start_time',
            'end_time',
            'createdBy',
            'item__itemID',
            'item__metadata__market__sourceLanguageCode',
            'item__metadata__market__targetLanguageCode',
            'item__metadata__market__domainName',
            'item__itemType',
            'task__id',
            'task__campaign__campaignName',
            'item__documentID',
            'item__isCompleteDocument',
        )
        for result in qs.values_list(*value_names):
            system1ID = result[0]
            score1 = result[1]
            system2ID = result[2]
            score2 = result[3]
            system3ID = result[4]
            score3 = result[5]
            start_time = result[6]
            end_time = result[7]
            duration = round(float(end_time) - float(start_time), 1)
            annotatorID = result[8]
            segmentID = result[9]
            marketID = '{0}-{1}'.format(result[10], result[11])
            domainName = result[12]
            itemType = result[13]
            taskID = result[14]
            campaignName = result[15]
            documentID = result[16]
            isCompleteDocument = result[17]

            if annotatorID in user_data:
                username = user_data[annotatorID][0]
                useremail = user_data[annotatorID][1]
                usergroups = user_data[annotatorID][2]

            else:
                user = User.objects.get(pk=annotatorID)
                username = user.username
                useremail = user.email
                usergroups = ';'.join(
                    [
                        x.name
                        for x in user.groups.all()
                        if not x.name in LANGUAGE_CODES_AND_NAMES.keys()
                    ]
                )
                if not usergroups:
                    usergroups = 'NoGroupInfo'

                user_data[annotatorID] = (username, useremail, usergroups)

            system_scores[marketID + '-' + domainName].append(
                (
                    taskID,
                    segmentID,
                    username,
                    useremail,
                    usergroups,
                    system1ID,
                    score1,
                    system2ID,
                    score2,
                    system3ID,
                    score3,
                    start_time,
                    end_time,
                    duration,
                    itemType,
                    campaignName,
                    documentID,
                    isCompleteDocument,
                )
            )

        x = system_scores
        s = [
            'taskID,segmentID,username,email,groups,system1ID,score1,system2ID,score2,system3ID,score3,startTime,endTime,durationInSeconds,itemType,campaignName,documentID,isCompleteDocument'
        ]
        for l in x:
            for i in x[l]:
                s.append(','.join([str(a) for a in i]))

        from os.path import join
        from Appraise.settings import BASE_DIR

        media_file_path = join(BASE_DIR, 'media', csv_file)
        with open(media_file_path, 'w') as outfile:
            for line in s:
                outfile.write(line)
                outfile.write('\n')
