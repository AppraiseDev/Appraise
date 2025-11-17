# pylint: disable=C0103,C0111,C0330,E1101
import json
import sys

from django.core.management.base import BaseCommand
from django.core.management.base import CommandError

from Campaign.models import Campaign
from EvalData.models import (
    DirectAssessmentDocumentTask,
    DirectAssessmentDocumentResult,
    PairwiseAssessmentDocumentTask,
    PairwiseAssessmentDocumentResult,
)


class Command(BaseCommand):
    help = 'Exports system scores to JSONL format for Document, PairwiseDocument, and ContrastiveESA tasks'

    def add_arguments(self, parser):
        parser.add_argument(
            'campaign_name',
            type=str,
            help='Name of the campaign you want to process data for',
        )
        parser.add_argument(
            '--completed-only',
            action='store_true',
            help='Include completed tasks only in the computation',
        )
        parser.add_argument(
            '--include-inactive',
            action='store_true',
            help='Include inactive users in the export',
        )
        parser.add_argument(
            '--include-context',
            action='store_true',
            help='Include context fields (source/target context left/right)',
        )

    def handle(self, *args, **options):
        # Identify Campaign instance for given name.
        try:
            campaign = Campaign.get_campaign_or_raise(options['campaign_name'])
        except LookupError as error:
            raise CommandError(error)

        # Check if campaign has DirectAssessmentDocument tasks
        doc_tasks = DirectAssessmentDocumentTask.objects.filter(campaign=campaign)
        if options['completed_only']:
            doc_tasks = doc_tasks.filter(completed=True)

        if doc_tasks.exists():
            self._export_document_results(
                campaign,
                doc_tasks,
                options['include_inactive'],
                options['include_context'],
            )

        # Check if campaign has PairwiseAssessmentDocument tasks
        pairwise_tasks = PairwiseAssessmentDocumentTask.objects.filter(
            campaign=campaign
        )
        if options['completed_only']:
            pairwise_tasks = pairwise_tasks.filter(completed=True)

        if pairwise_tasks.exists():
            self._export_pairwise_results(
                campaign,
                pairwise_tasks,
                options['include_inactive'],
                options['include_context'],
            )

    def _export_document_results(self, campaign, tasks, include_inactive, include_context):
        """Export DirectAssessmentDocument results to JSONL."""
        task_ids = list(tasks.values_list('id', flat=True))

        # Get campaign options to check for ContrastiveESA
        campaign_opts = str(campaign.campaignOptions).lower().split(";")
        is_contrastive_esa = "contrastiveesa" in campaign_opts

        if is_contrastive_esa:
            # ContrastiveESA needs special handling to group targets
            self._export_contrastive_esa_results(
                tasks, task_ids, include_inactive, include_context
            )
            return

        # Query results for regular Document tasks
        qs = DirectAssessmentDocumentResult.objects.filter(
            task__id__in=task_ids,
            completed=True,
            item__itemType__in=('TGT', 'CHK', 'BAD', 'REF'),
        )

        if not include_inactive:
            qs = qs.filter(createdBy__is_active=True)

        # Extract needed attributes for regular Document tasks
        attributes = [
            'createdBy__username',  # annotator
            'item__targetID',  # system_id
            'item__sourceID',  # source_id
            'item__sourceText',  # source_text
            'item__targetID',  # target_id
            'item__targetText',  # target_text
            'item__itemID',  # segment_id
            'item__itemType',  # item_type
            'item__metadata__market__sourceLanguageCode',  # source_language
            'item__metadata__market__targetLanguageCode',  # target_language
            'score',  # score
            'mqm',  # mqm_annotations
            'item__documentID',  # document_id
            'item__isCompleteDocument',  # is_complete_document
            'start_time',  # start_time
            'end_time',  # end_time
            'task__batchNo',  # batch_number
            'item_id',  # item_database_id
            'task__campaign__campaignName',  # campaign_name
        ]
        
        if include_context:
            attributes.extend([
                'item__sourceContextLeft',  # source_context_left
                'item__sourceContextRight',  # source_context_right
                'item__targetContextLeft',  # target_context_left
                'item__targetContextRight',  # target_context_right
            ])
        
        attributes = tuple(attributes)

        for result in qs.values_list(*attributes):
            json_obj = {
                'annotator': result[0],
                'system_id': result[1],
                'source_id': result[2],
                'source_text': result[3],
                'target_id': result[4],
                'target_text': result[5],
                'segment_id': result[6],
                'item_type': result[7],
                'source_language': result[8],
                'target_language': result[9],
                'score': result[10],
                'mqm_annotations': result[11],
                'document_id': result[12],
                'is_complete_document': result[13],
                'start_time': result[14],
                'end_time': result[15],
                'duration': round(result[15] - result[14], 1) if result[14] and result[15] else None,
                'batch_number': result[16],
                'item_database_id': result[17],
                'campaign_name': result[18],
                'task_type': 'Document',
            }
            
            # Add context fields if requested
            if include_context:
                json_obj['source_context_left'] = result[19]
                json_obj['source_context_right'] = result[20]
                json_obj['target_context_left'] = result[21]
                json_obj['target_context_right'] = result[22]
            
            sys.stdout.write(json.dumps(json_obj, ensure_ascii=False) + '\n')

    def _export_contrastive_esa_results(self, tasks, task_ids, include_inactive, include_context):
        """Export ContrastiveESA results to JSONL, grouping targets by document and annotator."""
        # Query results
        qs = DirectAssessmentDocumentResult.objects.filter(
            task__id__in=task_ids,
            completed=True,
            item__itemType__in=('TGT', 'CHK', 'BAD', 'REF'),
        )

        if not include_inactive:
            qs = qs.filter(createdBy__is_active=True)

        # Extract needed attributes
        attributes = [
            'createdBy__username',  # annotator
            'item__sourceID',  # system_id (for ContrastiveESA, this identifies the variant)
            'item__sourceText',  # source_text
            'item__targetID',  # target_id (same for all in document)
            'item__targetText',  # target_text
            'item__itemID',  # segment_id
            'item__itemType',  # item_type
            'item__metadata__market__sourceLanguageCode',  # source_language
            'item__metadata__market__targetLanguageCode',  # target_language
            'score',  # score
            'mqm',  # mqm_annotations
            'item__documentID',  # document_id
            'item__isCompleteDocument',  # is_complete_document
            'start_time',  # start_time
            'end_time',  # end_time
            'task__batchNo',  # batch_number
            'item_id',  # item_database_id
            'task__campaign__campaignName',  # campaign_name
        ]
        
        if include_context:
            attributes.extend([
                'item__sourceContextLeft',  # source_context_left
                'item__sourceContextRight',  # source_context_right
                'item__targetContextLeft',  # target_context_left
                'item__targetContextRight',  # target_context_right
            ])
        
        attributes = tuple(attributes)

        # Order by annotator, document_id, and segment_id to group related items
        qs = qs.order_by('createdBy__username', 'item__documentID', 'item__itemID')

        # Group results by (annotator, document_id)
        # In ContrastiveESA, all items with same documentID share the same source but have different targets
        from collections import defaultdict
        grouped_results = defaultdict(list)
        
        for result in qs.values_list(*attributes):
            # Key: (annotator, document_id)
            # This groups all target variants of the same source document for the same annotator
            key = (result[0], result[11])  # annotator, document_id
            grouped_results[key].append(result)

        # Export each group as a single JSONL line
        for (annotator, document_id), results in grouped_results.items():
            # Use first result for shared fields
            first = results[0]
            
            json_obj = {
                'annotator': annotator,
                'source_id': first[1],  # sourceID (should be same for all in group)
                'source_text': first[2],  # Source text (same for all targets in group)
                'targets': [],
                'item_type': first[6],
                'source_language': first[7],
                'target_language': first[8],
                'document_id': document_id,
                'is_complete_document': first[12],
                'batch_number': first[15],
                'campaign_name': first[17],
                'task_type': 'ContrastiveESA',
            }
            
            # Add each target variant
            for result in results:
                target_obj = {
                    'target_id': result[3],  # targetID identifies the variant
                    'target_text': result[4],  # Target text
                    'segment_id': result[5],  # itemID
                    'score': result[9],
                    'mqm_annotations': result[10],
                    'start_time': result[13],
                    'end_time': result[14],
                    'duration': round(result[14] - result[13], 1) if result[13] and result[14] else None,
                    'item_database_id': result[16],
                }
                
                # Add context fields if requested
                if include_context:
                    target_obj['source_context_left'] = result[18]
                    target_obj['source_context_right'] = result[19]
                    target_obj['target_context_left'] = result[20]
                    target_obj['target_context_right'] = result[21]
                
                json_obj['targets'].append(target_obj)
            
            sys.stdout.write(json.dumps(json_obj, ensure_ascii=False) + '\n')

    def _export_pairwise_results(self, campaign, tasks, include_inactive, include_context):
        """Export PairwiseAssessmentDocument results to JSONL."""
        task_ids = list(tasks.values_list('id', flat=True))

        # Get campaign options to check for PairwiseESA
        campaign_opts = str(campaign.campaignOptions).lower().split(";")
        is_pairwise_esa = "pairwiseesa" in campaign_opts

        # Query results
        qs = PairwiseAssessmentDocumentResult.objects.filter(
            task__id__in=task_ids,
            completed=True,
            item__itemType__in=('TGT', 'CHK', 'BAD', 'REF'),
        )

        if not include_inactive:
            qs = qs.filter(createdBy__is_active=True)

        # Extract needed attributes
        attributes = [
            'createdBy__username',  # annotator
            'item__segmentID',  # segment_id
            'item__segmentText',  # source_text
            'item__target1ID',  # target1_system_id
            'item__target1Text',  # target1_text
            'item__target2ID',  # target2_system_id
            'item__target2Text',  # target2_text
            'score1',  # score1
            'score2',  # score2
            'item__itemID',  # item_id
            'item__itemType',  # item_type
            'item__metadata__market__sourceLanguageCode',  # source_language
            'item__metadata__market__targetLanguageCode',  # target_language
            'item__documentID',  # document_id
            'item__isCompleteDocument',  # is_complete_document
            'start_time',  # start_time
            'end_time',  # end_time
            'task__batchNo',  # batch_number
            'item_id',  # item_database_id
            'task__campaign__campaignName',  # campaign_name
        ]
        
        # Add MQM fields if PairwiseESA is enabled
        if is_pairwise_esa:
            attributes.extend([
                'mqm1',  # mqm_annotations_1
                'mqm2',  # mqm_annotations_2
            ])
        
        if include_context:
            attributes.extend([
                'item__contextLeft',  # context_left
                'item__contextRight',  # context_right
                'item__target1ContextLeft',  # target1_context_left
                'item__target2ContextLeft',  # target2_context_left
            ])
        
        attributes = tuple(attributes)

        for result in qs.values_list(*attributes):
            # Base indices
            target1_score_idx = 7
            target2_id_idx = 5
            target2_text_idx = 6
            target2_score_idx = 8
            item_id_idx = 9
            item_type_idx = 10
            source_lang_idx = 11
            target_lang_idx = 12
            doc_id_idx = 13
            is_complete_idx = 14
            start_time_idx = 15
            end_time_idx = 16
            batch_no_idx = 17
            item_db_id_idx = 18
            campaign_name_idx = 19
            
            # MQM indices if enabled
            mqm1_idx = 20 if is_pairwise_esa else None
            mqm2_idx = 21 if is_pairwise_esa else None
            
            # Context indices (after MQM if both are present)
            context_offset = 20 + (2 if is_pairwise_esa else 0)
            
            json_obj = {
                'annotator': result[0],
                'source_id': result[1],
                'source_text': result[2],
                'targets': [
                    {
                        'target_id': result[3],
                        'target_text': result[4],
                        'score': result[target1_score_idx],
                    },
                ],
                'item_id': result[item_id_idx],
                'item_type': result[item_type_idx],
                'source_language': result[source_lang_idx],
                'target_language': result[target_lang_idx],
                'document_id': result[doc_id_idx],
                'is_complete_document': result[is_complete_idx],
                'start_time': result[start_time_idx],
                'end_time': result[end_time_idx],
                'duration': round(result[end_time_idx] - result[start_time_idx], 1) if result[start_time_idx] and result[end_time_idx] else None,
                'batch_number': result[batch_no_idx],
                'item_database_id': result[item_db_id_idx],
                'campaign_name': result[campaign_name_idx],
                'task_type': 'PairwiseESA' if is_pairwise_esa else 'PairwiseDocument',
            }
            
            # Add MQM annotations for target1 if PairwiseESA
            if is_pairwise_esa:
                json_obj['targets'][0]['mqm_annotations'] = result[mqm1_idx]

            # Add second target if it exists
            if result[target2_id_idx] is not None and result[target2_score_idx] is not None:
                target2_obj = {
                    'target_id': result[target2_id_idx],
                    'target_text': result[target2_text_idx],
                    'score': result[target2_score_idx],
                }
                # Add MQM annotations for target2 if PairwiseESA
                if is_pairwise_esa:
                    target2_obj['mqm_annotations'] = result[mqm2_idx]
                json_obj['targets'].append(target2_obj)
            
            # Add context fields if requested
            if include_context:
                json_obj['context_left'] = result[context_offset]
                json_obj['context_right'] = result[context_offset + 1]
                json_obj['targets'][0]['target_context_left'] = result[context_offset + 2]
                if len(json_obj['targets']) > 1:
                    json_obj['targets'][1]['target_context_left'] = result[context_offset + 3]

            sys.stdout.write(json.dumps(json_obj, ensure_ascii=False) + '\n')
