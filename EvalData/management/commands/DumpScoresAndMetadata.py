"""
Appraise evaluation framework

See LICENSE for usage details
"""
from gzip import open as gz_open
from os.path import basename

from django.core.management.base import BaseCommand
from django.core.management.base import CommandError

from EvalData.models import DirectAssessmentResult

# pylint: disable=E0401,W0611


INFO_MSG = 'INFO: '
WARNING_MSG = 'WARN: '

# pylint: disable=C0111,C0330
class Command(BaseCommand):
    help = 'Dumps all DirectAssessmentResult scores and associated metadata'

    def add_arguments(self, parser):
        parser.add_argument('target_file', type=str, help='Path to target text file')

    def handle(self, *args, **options):
        _msg = '\n[{0}]\n\n'.format(basename(__file__))
        self.stdout.write(_msg)

        target_file = options['target_file']
        self.stdout.write('target_file: {0}'.format(target_file))

        self.stdout.write('\n[INIT]\n\n')

        labels = DirectAssessmentResult.objects.filter(completed=True)

        blocks = 0
        total_blocks = labels.count() // 1000 + 1
        output = []
        batch_size = 1000

        _open = open
        if target_file.lower().endswith('.gz'):
            _open = gz_open
        out_file = _open(target_file, 'a', encoding='utf-8')

        label_values = (
            'id',
            'dateCreated',
            'task__campaign__campaignName',
            'item__itemID',
            'item__itemType',
            'item__sourceText',
            'item__sourceID',
            'item__targetText',
            'item__targetID',
            'score',
            'item__metadata__market__sourceLanguageCode',
            'item__metadata__market__targetLanguageCode',
        )
        for label_data in labels.order_by('-id').values_list(*label_values):
            result_id = label_data[0]
            date_created = label_data[1]
            campaign_name = label_data[2]
            item_id = label_data[3]
            item_type = label_data[4]
            source_text = label_data[5]
            source_id = label_data[6]
            target_text = label_data[7]
            target_id = label_data[8]
            item_score = label_data[9]
            source_language_code = label_data[10]
            target_language_code = label_data[11]

            data = (
                result_id,
                date_created,
                campaign_name,
                item_id,
                item_type,
                source_text,  # .encode('utf-8'),
                source_id,
                target_text,  # .encode('utf-8'),
                target_id,
                item_score,
                source_language_code,
                target_language_code,
            )
            output.append(data)
            #
            if len(output) == batch_size:
                lines = []
                for data in output:
                    lines.append('RESULT_ID: {0}\n'.format(data[0]))
                    lines.append('DATE_CREATED: {0}\n'.format(data[1]))
                    lines.append('CAMPAIGN_NAME: {0}\n'.format(data[2]))
                    lines.append('ITEM_ID: {0}\n'.format(data[3]))
                    lines.append('ITEM_TYPE: {0}\n'.format(data[4]))
                    lines.append('SOURCE_TEXT: {0}\n'.format(data[5]))
                    lines.append('SOURCE_ID: {0}\n'.format(data[6]))
                    lines.append('TARGET_TEXT: {0}\n'.format(data[7]))
                    lines.append('TARGET_ID: {0}\n'.format(data[8]))
                    lines.append('ITEM_SCORE: {0}\n'.format(data[9]))
                    lines.append('SOURCE_LANGUAGE_CODE: {0}\n'.format(data[10]))
                    lines.append('TARGET_LANGUAGE_CODE: {0}\n'.format(data[11]))
                    lines.append('-' * 10 + '\n')
                out_file.writelines(lines)
                output = []
                lines = []
                blocks += 1
                print(
                    '{0}/{1} blocks written, {2:05.1f}% completed'.format(
                        blocks,
                        total_blocks,
                        100.0 * float(blocks) / float(total_blocks),
                    )
                )

        lines = []
        for data in output:
            lines.append('RESULT_ID: {0}\n'.format(data[0]))
            lines.append('DATE_CREATED: {0}\n'.format(data[1]))
            lines.append('CAMPAIGN_NAME: {0}\n'.format(data[2]))
            lines.append('ITEM_ID: {0}\n'.format(data[3]))
            lines.append('ITEM_TYPE: {0}\n'.format(data[4]))
            lines.append('SOURCE_TEXT: {0}\n'.format(data[5]))
            lines.append('SOURCE_ID: {0}\n'.format(data[6]))
            lines.append('TARGET_TEXT: {0}\n'.format(data[7]))
            lines.append('TARGET_ID: {0}\n'.format(data[8]))
            lines.append('ITEM_SCORE: {0}\n'.format(data[9]))
            lines.append('SOURCE_LANGUAGE_CODE: {0}\n'.format(data[10]))
            lines.append('TARGET_LANGUAGE_CODE: {0}\n'.format(data[11]))
            lines.append('-' * 10 + '\n')
        out_file.writelines(lines)
        output = []
        lines = []
        blocks += 1
        print(
            '{0}/{1} blocks written, {2:05.1f}% completed'.format(
                blocks,
                total_blocks,
                100.0 * float(blocks) / float(total_blocks),
            )
        )

        self.stdout.write('\n[DONE]\n\n')
