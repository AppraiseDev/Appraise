from collections import defaultdict, OrderedDict
from json import load
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError

from Campaign.models import Campaign
from EvalData.models import DirectAssessmentTask, DirectAssessmentResult

# pylint: disable=C0111,C0330,E1101
class Command(BaseCommand):
    help = 'Validates Direct Assessment JSON data files'

    def add_arguments(self, parser):
        parser.add_argument(
          'json_file', type=str,
          help='JSON file containing direct assessment data'
        )
        parser.add_argument(
          'required_systems', type=int,
          help='Defines the required number of systems per segment'
        )
        parser.add_argument(
          '--max-batches', type=int, default=-1,
          help='Specifies max number of batches to create'
        )

    def handle(self, *args, **options):
        json_file = options['json_file']
        required_systems = options['required_systems']

        system_ids_by_segment = defaultdict(list)
        with open(json_file) as input_file:
            json_data = load(input_file)

            max_batches = len(json_data)
            if options['max_batches'] > 0:
                max_batches = options['max_batches']

            for batch_no in range(max_batches):
                batch = json_data[batch_no]
                for item_no in range(len(batch['items'])):
                    item = batch['items'][item_no]
                    if item['itemType'] == 'TGT':
                        segmentID = item['itemID']
                        systemIDs = item['targetID'].split('+')

                        for systemID in systemIDs:
                            if not systemID in system_ids_by_segment[segmentID]:
                                system_ids_by_segment[segmentID].append(systemID)

        errors = []
        for segmentID, systemIDs in system_ids_by_segment.items():
            if len(systemIDs) != required_systems:
                errors.append(segmentID)
                print(segmentID, len(systemIDs), sorted(systemIDs))

        print("Encountered {0} validation errors for {1} segments".format(
          len(errors), len(system_ids_by_segment.keys()))
        )
