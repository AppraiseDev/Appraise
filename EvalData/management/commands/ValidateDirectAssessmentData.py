"""
Appraise evaluation framework

See LICENSE for usage details
"""
# pylint: disable=W0611
from collections import defaultdict
from json import load

from django.core.management.base import BaseCommand
from django.core.management.base import CommandError

# pylint: disable=E0401,W0611


class Command(BaseCommand):
    """
    Validates Direct Assessment JSON data files.

    Checks that the given JSON batch file contains the defined number
    of required systems and flags segment IDs for this is not the case.

    Specify --max-batches N to only load data from the first N batches.
    """

    help = 'Validates Direct Assessment JSON data files'

    # pylint: disable=C0330,no-self-use
    def add_arguments(self, parser):
        parser.add_argument(
            'json_file',
            type=str,
            help='JSON file containing direct assessment data',
        )
        parser.add_argument(
            'required_systems',
            type=int,
            help='Defines the required number of systems per segment',
        )
        parser.add_argument(
            '--max-batches',
            type=int,
            default=-1,
            help='Specifies max number of batches to create',
        )

    def handle(self, *args, **options):
        del args  # Unused.

        # Load system IDs and organise by segment ID.
        system_ids_by_segment = Command._load_ids_from_json_file(
            options['json_file'], options['max_batches']
        )

        # Loop over all segments and identify those where less than the
        # number of required systems are available.
        errors = []
        all_systems = []
        for segment_id, system_ids in system_ids_by_segment.items():
            if len(system_ids) != options['required_systems']:
                errors.append(segment_id)
                print(segment_id, len(system_ids), sorted(system_ids))

                for system_id in all_systems:
                    if not system_id in system_ids:
                        print("Missing {0}".format(system_id))

            else:
                all_systems = system_ids

        print(
            "Encountered {0} validation errors for {1} segments".format(
                len(errors), len(system_ids_by_segment.keys())
            )
        )

    @staticmethod
    def _load_ids_from_json_file(json_file, max_batches):
        """
        Loads all system IDs from the given JSON batch file.

        Creates defaultdict(list) and organises by segment ID.
        This is constrained to only 'TGT' segments, as these
        are the only "real" system segments.

        Multi system IDs (containing +) will be split.

        Use max_batches to constrain how many JSON batches to process.
        """
        ids_data = defaultdict(list)

        with open(json_file) as input_file:
            json_data = load(input_file)

            # If there is no constraint given, process all batches.
            if max_batches < 0:
                max_batches = len(json_data)

            for batch_no in range(max_batches):
                batch = json_data[batch_no]
                for item in batch['items']:
                    if item['itemType'] == 'TGT':
                        segment_id = int(item['itemID'])
                        system_ids = item['targetID'].split('+')

                        for system_id in system_ids:
                            if not system_id in ids_data[segment_id]:
                                ids_data[segment_id].append(system_id)

        return ids_data
