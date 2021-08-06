from collections import defaultdict
from collections import OrderedDict
from json import dumps
from json import load

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.core.management.base import CommandError

from Campaign.models import Campaign
from EvalData.models import DirectAssessmentResult
from EvalData.models import DirectAssessmentTask

# pylint: disable=C0111,C0330,E1101
class Command(BaseCommand):
    help = 'Validates Direct Assessment JSON data files'

    def add_arguments(self, parser):
        parser.add_argument(
            'source_json',
            type=str,
            help='JSON file containing direct assessment data',
        )
        parser.add_argument(
            'segments_json',
            type=str,
            help='JSON file containing segments data',
        )
        parser.add_argument(
            'target_json',
            type=str,
            help='Defines path to JSON target file',
        )

    def handle(self, *args, **options):
        source_json = options['source_json']
        segments_json = options['segments_json']
        target_json = options['target_json']

        patchJson = None
        segment_ids_by_system = defaultdict(list)
        with open(source_json) as input_file:
            json_data = load(input_file)
            patchJson = json_data

            max_batches = len(json_data)
            for batch_no in range(max_batches):
                batch = json_data[batch_no]
                for item_no in range(len(batch['items'])):
                    item = batch['items'][item_no]
                    if item['itemType'] == 'BAD':
                        segmentID = int(item['itemID'])
                        systemIDs = item['targetID'].split('+')

                        for systemID in systemIDs:
                            segment_ids_by_system[systemID].append(segmentID)

        patches_by_system = {}
        for systemID in segment_ids_by_system.keys():
            patches_by_system[systemID] = defaultdict(list)

        with open(segments_json) as input_file:
            json_data = load(input_file)

            for md5_hash in json_data:
                json_item = json_data[md5_hash]

                systemIDs = json_item['systems']
                segmentID = int(json_item['segment_id'])
                patchData = json_item['segment_bad']

                for systemID in systemIDs:
                    if segmentID in segment_ids_by_system[systemID]:
                        if not patchData in patches_by_system[systemID][segmentID]:
                            patches_by_system[systemID][segmentID].append(patchData)

        for batch_no in range(len(patchJson)):
            batch = patchJson[batch_no]
            for item_no in range(len(batch['items'])):
                item = batch['items'][item_no]
                if item['itemType'] == 'BAD':
                    segmentID = int(item['itemID'])
                    systemIDs = item['targetID'].split('+')

                    patches = []
                    for systemID in systemIDs:
                        patchData = patches_by_system[systemID][segmentID]
                        if not patchData in patches:
                            patches.append(patchData)

                    if len(patches) > 1:
                        print("PATCH CONFLICT!!!")
                        print(patches)

                    item['targetTextOld'] = item['targetText']
                    item['targetText'] = patches[0][0]

        json_data = dumps(patchJson, indent=2, sort_keys=True)
        with open(options['target_json'], mode='w', encoding='utf8') as output_file:
            self.stdout.write(
                'Creating {0} ... '.format(options['target_json']),
                ending='',
            )
            output_file.write(str(json_data))
            self.stdout.write('OK')
