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
from EvalData.models.base_models import seconds_to_timedelta
from EvalData.models.base_models import TextSegmentWithTwoTargets

# TODO: Unclear if these are needed?
# from Appraise.settings import STATIC_URL, BASE_CONTEXT

MAX_DOCUMENTID_LENGTH = 100

LOGGER = _get_logger(name=__name__)


class TextSegmentWithTwoTargetsWithContext(TextSegmentWithTwoTargets):
    """
    Models a pair of two text segments within a document context.
    """

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

    # pylint: disable=E1101
    def is_valid(self):
        """
        Validates the current TextSegmentWithTwoTargetsWithContext instance.
        """
        return super(TextSegmentWithTwoTargetsWithContext, self).is_valid()


@AnnotationTaskRegistry.register
class PairwiseAssessmentDocumentTask(BaseMetadata):
    """
    Models a pairwise assessment document evaluation task.

    Note: this task is, similarily to other models, a shameless copy of
    DirectAssessmentContextTask, with one additional method for retrieving all
    items belonging to the same document in the task called
    `next_document_for_user`, and a helper method `get_results_for_each_item`.
    The underlying model is the same as for
    DirectAssessmentContextTask.
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
        TextSegmentWithTwoTargetsWithContext,
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
        results = PairwiseAssessmentDocumentResult.objects.filter(
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
            result = PairwiseAssessmentDocumentResult.objects.filter(
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
            annotations = PairwiseAssessmentDocumentResult.objects.filter(
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

                # Not sure why I would complete the batch here?
                # self.batchData.complete()
                # self.batchData.save()

        if return_completed_items:
            return (next_item, completed_items)

        return next_item

    def next_document_for_user(self, user, return_statistics=True):
        """Returns the next item and all items from its document."""
        # Find the next not annotated item
        (
            next_item,
            completed_items,
        ) = self.next_item_for_user(user, return_completed_items=True)

        if not next_item:
            if not return_statistics:
                return (next_item, [], [])
            return (next_item, completed_items, 0, 0, [], [], 0)

        # Retrieve all items from the document which next_item belongs to
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

        # Get results for completed items in this block
        block_results = self.get_results_for_each_item(block_items, user)

        if not return_statistics:
            return (next_item, block_items, block_results)

        # Collect statistics
        completed_items_in_block = len(
            [res for res in block_results if res is not None]
        )
        completed_blocks = PairwiseAssessmentDocumentResult.objects.filter(
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
            next_item,  # the first unannotated item for the user
            completed_items,  # the number of completed items in the task
            completed_blocks,  # the number of completed documents in the task
            completed_items_in_block,  # the number of completed items in the current document
            block_items,  # all items from the current document
            block_results,  # all score results from the current document
            total_blocks,  # the total number of documents in the task
        )

    def get_results_for_each_item(self, block_items, user):
        """Returns the latest result object for each item or none."""
        # TODO: optimize, this possibly makes too many individual queries
        block_results = []

        for item in block_items:
            result = (
                PairwiseAssessmentDocumentResult.objects.filter(
                    item__id=item.id,
                    completed=True,
                    createdBy=user,  # TODO: is passing user as an argument needed?
                    task=self,
                )
                .order_by('item__id', 'dateModified')
                .first()
            )
            block_results.append(result)

        # Sanity checks for items and results
        if len(block_items) != len(block_results):
            print('Warning: incorrect number of retrieved results!')
        for item, result in zip(block_items, block_results):
            # print(f'  >> item={item} result={result}')
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

        # It seems that assignedTo is converted to an integer count.
        active_tasks = active_tasks.order_by('id').values_list(
            'id', 'requiredAnnotations', 'assignedTo'
        )

        for active_task in active_tasks:
            print(active_task)
            active_users = active_task[2] or 0
            if active_users < active_task[1]:
                return cls.objects.get(pk=active_task[0])

        return None

        # TODO: this needs to be removed.
        for active_task in active_tasks:
            market = active_task.items.first().metadata.market
            if not market.targetLanguageCode == code:
                continue

            active_users = active_task.assignedTo.count()
            if active_users < active_task.requiredAnnotations:
                return active_task

        return None

    @classmethod
    def get_next_free_task_for_language_and_campaign(cls, code, campaign):
        return cls.get_next_free_task_for_language(code, campaign)

    @classmethod
    def import_from_json(cls, campaign, batch_user, batch_data, max_count):
        """
        Creates new PairwiseAssessmentDocumentTask instances based on JSON input.
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
            # TODO: implement proper support for multiple json files in archive.
            for batch_json_file in batch_json_files:
                batch_content = batch_zip.read(batch_json_file).decode('utf-8')
                # Python 3.9 removed 'encoding' from json.loads
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
                    print('New max length ID:', current_length_id, item['segmentID'])
                    max_length_id = current_length_id

                if current_length_text > max_length_text:
                    print(
                        'New max length text:',
                        current_length_text,
                        item['segmentText'].encode('utf-8'),
                    )
                    max_length_text = current_length_text

                item_targets = item['targets']
                # TODO: check if 'targets' is empty or has more elements than 2
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

                new_item = TextSegmentWithTwoTargetsWithContext(
                    segmentID=item['segmentID'],
                    segmentText=item['segmentText'],
                    contextLeft=item.get('segmentContextLeft', ''),
                    target1ID=item_tgt1_idx,
                    target1Text=item_tgt1_txt,
                    target1ContextLeft=item_tgt1_ctx,
                    target2ID=item_tgt2_idx,
                    target2Text=item_tgt2_txt,
                    target2ContextLeft=item_tgt2_ctx,
                    createdBy=batch_user,
                    itemID=item['itemID'],
                    itemType=item['itemType'],
                    documentID=item['documentID'],
                    isCompleteDocument=item['isCompleteDocument'],
                )
                new_items.append(new_item)
                if item['isCompleteDocument']:
                    doc_items += 1

            current_count += 1

            for new_item in new_items:
                new_item.metadata = batch_meta
                new_item.save()
            # batch_meta.textpairwithcontext_set.add(*new_items, bulk=False)
            # batch_meta.save()

            new_task = PairwiseAssessmentDocumentTask(
                campaign=campaign,
                requiredAnnotations=batch_task['task']['requiredAnnotations'],
                batchNo=batch_task['task']['batchNo'],
                batchData=batch_data,
                createdBy=batch_user,
            )
            new_task.save()

            # for new_item in new_items:
            #    new_task.items.add(new_item)
            new_task.items.add(*new_items)
            new_task.save()

            _msg = 'Success processing batch {0}, task {1}'.format(
                str(batch_data), batch_task['task']['batchNo']
            )
            LOGGER.info(_msg)

        _msg = 'Max length ID={0}, text={1}'.format(max_length_id, max_length_text)
        LOGGER.info(_msg)

        t2 = datetime.now()
        print(t2 - t1)

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

    def _generate_str_name(self):
        return '{0}.{1}[{2}]'.format(self.__class__.__name__, self.campaign, self.id)


class PairwiseAssessmentDocumentResult(BaseMetadata):
    """
    Models a direct assessment document evaluation result.
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

    start_time = models.FloatField(
        verbose_name=_('Start time'), help_text=_('(in seconds)')
    )

    end_time = models.FloatField(
        verbose_name=_('End time'), help_text=_('(in seconds)')
    )

    item = models.ForeignKey(
        TextSegmentWithTwoTargetsWithContext,
        db_index=True,
        on_delete=models.PROTECT,
        related_name='%(app_label)s_%(class)s_item',
        related_query_name="%(app_label)s_%(class)ss",
        verbose_name=_('Item'),
    )

    task = models.ForeignKey(
        PairwiseAssessmentDocumentTask,
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
        return '{0}.{1}={2}+{3}'.format(
            self.__class__.__name__,
            self.item,
            self.score1,
            self.score2,
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
            'target2ID',
            'score2',
            'createdBy',
            'item__itemID',
            'item__metadata__market__sourceLanguageCode',
            'item__metadata__market__targetLanguageCode',
        )
        for result in qs.values_list(*value_names):
            systemID = result[0]
            score1 = result[1]
            score2 = result[2]
            annotatorID = result[3]
            segmentID = result[4]
            marketID = '{0}-{1}'.format(result[5], result[6])
            system_scores[marketID].append(
                (systemID, annotatorID, segmentID, score1, score2)
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
    def dump_all_results_to_csv_file(cls, csv_file):
        from Dashboard.models import LANGUAGE_CODES_AND_NAMES

        system_scores = defaultdict(list)
        user_data = {}
        qs = cls.objects.filter(completed=True)

        value_names = (
            'item__targetID',
            'score1',
            'item__target2ID',
            'score2',
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
            start_time = result[4]
            end_time = result[5]
            duration = round(float(end_time) - float(start_time), 1)
            annotatorID = result[6]
            segmentID = result[7]
            marketID = '{0}-{1}'.format(result[8], result[9])
            domainName = result[10]
            itemType = result[11]
            taskID = result[12]
            campaignName = result[13]
            documentID = result[14]
            isCompleteDocument = result[15]

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
                    start_time,
                    end_time,
                    duration,
                    itemType,
                    campaignName,
                    documentID,
                    isCompleteDocument,
                )
            )

        # TODO: this is very intransparent... and needs to be fixed!
        x = system_scores
        s = [
            'taskID,segmentID,username,email,groups,system1ID,score1,system2ID,score2,startTime,endTime,durationInSeconds,itemType,campaignName,documentID,isCompleteDocument'
        ]
        for l in x:
            for i in x[l]:
                s.append(','.join([str(a) for a in i]))

        from os.path import join
        from Appraise.settings import BASE_DIR

        media_file_path = join(BASE_DIR, 'media', csv_file)
        with open(media_file_path, 'w') as outfile:
            for c in s:
                outfile.write(c)
                outfile.write('\n')

    @classmethod
    def get_csv(cls, srcCode, tgtCode, domain):
        system_scores = defaultdict(list)
        qs = cls.objects.filter(completed=True)

        value_names = (
            'item__target1ID',
            'score1',
            'item__target2ID',
            'score2',
            'start_time',
            'end_time',
            'createdBy',
            'item__itemID',
            'item__metadata__market__sourceLanguageCode',
            'item__metadata__market__targetLanguageCode',
            'item__metadata__market__domainName',
            'item__itemType',
            'item__documentID',
            'item__isCompleteDocument',
        )
        for result in qs.values_list(*value_names):

            if (
                not domain == result[10]
                or not srcCode == result[8]
                or not tgtCode == result[9]
            ):
                continue

            system1ID = result[0]
            score1 = result[1]
            system2ID = result[2]
            score2 = result[3]
            start_time = result[4]
            end_time = result[5]
            duration = round(float(end_time) - float(start_time), 1)
            annotatorID = result[6]
            segmentID = result[7]
            marketID = '{0}-{1}'.format(result[8], result[9])
            domainName = result[10]
            itemType = result[11]
            documentID = result[12]
            isCompleteDocument = result[13]
            user = User.objects.get(pk=annotatorID)
            username = user.username
            useremail = user.email
            system_scores[marketID + '-' + domainName].append(
                (
                    segmentID,
                    username,
                    useremail,
                    system1ID,
                    score1,
                    system2ID,
                    score2,
                    duration,
                    itemType,
                    documentID,
                    isCompleteDocument,
                )
            )

        return system_scores

    @classmethod
    def write_csv(cls, srcCode, tgtCode, domain, csvFile, allData=False):
        x = cls.get_csv(srcCode, tgtCode, domain)
        s = [
            'username,email,segmentID,score1,score2,durationInSeconds,itemType,documentID,isCompleteDocument'
        ]
        if allData:
            s[0] = 'systemID,' + s[0]

        for l in x:
            for i in x[l]:
                e = i[1:] if not allData else i
                s.append(','.join([str(a) for a in e]))

        from os.path import join
        from Appraise.settings import BASE_DIR

        media_file_path = join(BASE_DIR, 'media', csvFile)
        with open(media_file_path, 'w') as outfile:
            for c in s:
                outfile.write(c)
                outfile.write('\n')

    @classmethod
    def get_system_scores(cls, campaign_id):
        system_scores = defaultdict(list)

        value_types = ('TGT', 'CHK')
        qs = cls.objects.filter(completed=True, item__itemType__in=value_types)

        # If campaign ID is given, only return results for this campaign.
        if campaign_id:
            qs = qs.filter(task__campaign__id=campaign_id)

        value_names = (
            'item__target1ID',
            'item__target2ID',
            'item__itemID',
            'score1',
            'score2',
            'item__documentID',
            'item__isCompleteDocument',
        )
        for result in qs.values_list(*value_names):
            # if not result.completed or result.item.itemType not in ('TGT', 'CHK'):
            #    continue

            system1_ids = result[0].split('+')  # result.item.targetID.split('+')
            system2_ids = result[1].split('+')  # result.item.targetID.split('+')
            segment_id = result[1]
            segment_id = result[2]
            score1 = result[3]  # .score
            score2 = result[4]  # .score
            documentID = result[5]
            isCompleteDocument = result[6]

            for system_id in system1_ids:
                system_scores[system_id].append(
                    (segment_id, score1, documentID, isCompleteDocument)
                )
            for system_id in system2_ids:
                system_scores[system_id].append(
                    (segment_id, score2, documentID, isCompleteDocument)
                )

        return system_scores

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

        # If campaign ID is given, only return results for this campaign.
        if campaign_id:
            qs = qs.filter(task__campaign__id=campaign_id)

        if not include_inactive:
            qs = qs.filter(createdBy__is_active=True)

        attributes_to_extract = (
            'createdBy__username',  # User ID
            'item__target1ID',  # System ID
            'item__target2ID',  # System ID
            'item__itemID',  # Segment ID
            'item__itemType',  # Item type
            'item__metadata__market__sourceLanguageCode',  # Source language
            'item__metadata__market__targetLanguageCode',  # Target language
            'score1',  # Score
            'score2',  # Score
            'item__documentID',  # Document ID
            'item__isCompleteDocument',  # isCompleteDocument
        )

        if extended_csv:
            attributes_to_extract = attributes_to_extract + (
                'start_time',  # Start time
                'end_time',  # End time
            )

        if add_batch_info:
            attributes_to_extract = attributes_to_extract + (
                'task__batchNo',  # Batch number
                'item_id',  # Real item ID
            )

        for _result in qs.values_list(*attributes_to_extract):
            results = [
                (
                    _result[0],
                    _result[1],
                    _result[3],
                    _result[4],
                    _result[5],
                    _result[6],
                    _result[7],
                    _result[9],
                    _result[10],
                    *_result[11:],
                ),
                (
                    _result[0],
                    _result[2],
                    _result[3],
                    _result[4],
                    _result[5],
                    _result[6],
                    _result[8],
                    _result[9],
                    _result[10],
                    *_result[11:],
                ),
            ]

            if add_batch_info:  # Add index of the target segment
                results[0] = (*results[0], 0)
                results[1] = (*results[1], 1)

            for result in results:
                if (
                    result[1] is None
                ):  # Ignore if this was an item with only one target segment
                    continue

                user_id = result[0]
                sys_ids = result[1]

                if expand_multi_sys:
                    system_ids = sys_ids.split('+')

                    for system_id in system_ids:
                        data = (user_id,) + (system_id,) + result[2:]
                        system_data.append(data)

                else:
                    system_id = sys_ids
                    data = (user_id,) + (system_id,) + result[2:]
                    system_data.append(data)

        return system_data

    @classmethod
    def get_system_status(cls, campaign_id=None, sort_index=3):
        system_scores = cls.get_system_scores(campaign_id=None)
        non_english_codes = (
            'cs',
            'de',
            'fi',
            'lv',
            'tr',
            'tr',
            'ru',
            'zh',
        )

        codes = ['en-{0}'.format(x) for x in non_english_codes] + [
            '{0}-en'.format(x) for x in non_english_codes
        ]

        data = {}
        for code in codes:
            data[code] = {}
            for key in [x for x in system_scores if code in x]:
                data[code][key] = system_scores[key]

        output_data = {}
        for code in codes:
            total_annotations = sum([len(x) for x in data[code].values()])
            output_local = []
            for key in data[code]:
                x = data[code][key]
                z = sum(x) / total_annotations
                output_local.append((key, len(x), sum(x) / len(x), z))

            output_data[code] = list(
                sorted(output_local, key=lambda x: x[sort_index], reverse=True)
            )

        return output_data

    @classmethod
    def completed_results_for_user_and_campaign(cls, user, campaign):
        results = cls.objects.filter(
            activated=False,
            completed=True,
            createdBy=user,
            task__campaign=campaign,
        ).values_list('item_id', flat=True)

        return len(set(results))
