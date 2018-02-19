"""
Appraise evaluation framework
"""
# pylint: disable=W0611
from collections import defaultdict, OrderedDict
from datetime import datetime
from glob import iglob
from json import load
from os import makedirs, path
from os.path import basename
from random import seed, shuffle
from shutil import copyfile
from sys import exit as sys_exit
from traceback import format_exc
from django.core.management.base import BaseCommand, CommandError

INFO_MSG = 'INFO: '

EXTENSION_FOR_BAD_FILES = 'bad'
EXTENSION_FOR_IDS_FILES = 'ids'

# pylint: disable=C0111
class Command(BaseCommand):
    help = 'Creates subset text files based on given JSON batch file'

    # pylint: disable=C0330
    def add_arguments(self, parser):
        parser.add_argument(
          'source_file', type=str,
          help='Path to source text file'
        )
        parser.add_argument(
          'json_file', type=str,
          help='Path to JSON batch file'
        )
        parser.add_argument(
          'target_path', type=str,
          help='Path to bad reference text folder'
        )
        parser.add_argument(
          '--unicode', action='store_true',
          help='Expects text files in Unicode encoding'
        )
        parser.add_argument(
          '--ignore-ids', type=str,
          help='Defines comma separated list of segment IDs to ignore'
        )

    def handle(self, *args, **options):
        # Initialize random number generator
        source_file = options['source_file']
        json_file = options['json_file']
        target_path = options['target_path']
        unicode_enc = options['unicode']
        ignore_ids = options['ignore_ids']

        segment_ids_to_ignore = []
        if ignore_ids:
            for x in ignore_ids.split(','):
                segment_ids_to_ignore.append(int(x))

        _msg = '\n[{0}]\n\n'.format(path.basename(__file__))
        self.stdout.write(_msg)

        self.stdout.write('source_file: {0}'.format(source_file))
        self.stdout.write('json_file: {0}'.format(json_file))

        self.stdout.write('\n[INIT]\n\n')

        if not path.exists(target_path):
            try:
                _msg = '{0}Creating target path {1} ... '.format(
                  INFO_MSG, target_path
                )
                self.stdout.write(_msg, ending='')
                makedirs(target_path)
                self.stdout.write('OK')

            # pylint: disable=W0702
            except:
                self.stdout.write('FAIL')
                self.stdout.write(format_exc())

        encoding = 'utf16' if unicode_enc else 'utf8'
        source_data = Command._load_text_from_file(source_file, encoding)

        ids_data = defaultdict(list)
        with open(json_file) as input_file:
            json_data = load(input_file)

            for batch_no in range(len(json_data)):
                batch = json_data[batch_no]
                for item_no in range(len(batch['items'])):
                    item = batch['items'][item_no]
                    if item['itemType'] == 'TGT':
                        segmentID = int(item['itemID'])
                        systemIDs = item['targetID'].split('+')

                        for systemID in systemIDs:
                            ids_data[systemID].append(segmentID)

        systemID = basename(source_file)
        filteredData = []
        if systemID in ids_data.keys():
            for segmentID in sorted(ids_data[systemID]):
                if segmentID in segment_ids_to_ignore:
                    print('Ignoring segmentID={0}'.format(segmentID))
                    continue

                filteredData.append(source_data[segmentID])

        target_file = path.join(target_path, basename(source_file) + '.filtered.txt')
        with open(target_file, mode='w', encoding=encoding) as output_file:
            for line in filteredData:
                output_file.write(line)
                output_file.write('\r\n')

        self.stdout.write('\n[DONE]\n\n')


    @staticmethod
    def _load_text_from_file(file_path, encoding='utf8'):
        segment_id = 0
        file_text = OrderedDict()

        with open(file_path, encoding=encoding) as input_file:
            for current_line in input_file:
                segment_id += 1
                file_text[segment_id] = current_line.strip()

        return file_text
