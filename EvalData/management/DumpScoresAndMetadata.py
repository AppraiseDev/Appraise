"""
Appraise evaluation framework

See LICENSE for usage details
"""
from os.path import basename

# pylint: disable=E0401,W0611
from django.core.management.base import (
    BaseCommand,
    CommandError,
)

from EvalData.models import DirectAssessmentResult


INFO_MSG = 'INFO: '
WARNING_MSG = 'WARN: '

# pylint: disable=C0111,C0330
class Command(BaseCommand):
    help = 'Dumps all DirectAssessmentResult scores and associated metadata'

    def add_arguments(self, parser):
        parser.add_argument(
          'target_file', type=str,
          help='Path to target text file'
        )


    def handle(self, *args, **options):
        _msg = '\n[{0}]\n\n'.format(path.basename(__file__))
        self.stdout.write(_msg)

        self.stdout.write('target_file: {0}'.format(options['target_file']))

        self.stdout.write('\n[INIT]\n\n')

        labels = DirectAssessmentResult.objects.filter(activated=True)

        blocks = 0
        total_blocks = labels.count() // 1000 + 1
        output = []
        batch_size = 1000
        out_file = open(options['target_file'], 'a', encoding='utf-8')

        for label in labels.order_by('-id').iterator():
            result_id = label.id
            date_created = label.dateCreated
            campaign_name = label.task.campaign.campaignName
            item_id = label.item.itemID
            item_type = label.item.itemType
            source_text = label.item.sourceText
            source_id = label.item.sourceID
            target_text = label.item.targetText
            target_id = label.item.targetID
            item_score = label.score
            source_language_code = label.item.metadata.market.sourceLanguageCode
            target_language_code = label.item.metadata.market.targetLanguageCode

            data = (
                result_id,
                date_created,
                campaign_name,
                item_id,
                item_type,
                source_text, #.encode('utf-8'),
                source_id,
                target_text, #.encode('utf-8'),
                target_id,
                item_score,
                source_language_code,
                target_language_code,
            )
            output.append(
                data
            )
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
                print('{0}/{1} blocks written, {2:.2}% completed'.format(blocks, total_blocks, 100.0 * float(blocks)/float(total_blocks)))

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
        print('{0}/{1} blocks written, {2:.2}% completed'.format(blocks, total_blocks, 100.0 * float(blocks)/float(total_blocks)))

        self.stdout.write('\n[DONE]\n\n')
