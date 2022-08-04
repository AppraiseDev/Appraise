"""
Appraise evaluation framework

See LICENSE for usage details
"""
from collections import defaultdict
from collections import OrderedDict
from glob import iglob
from os.path import basename
from os.path import sep as path_sep
from sys import exit as sys_exit

from django.core.management.base import BaseCommand
from django.core.management.base import CommandError

# pylint: disable=E0401,W0611

INFO_MSG = 'INFO: '

# pylint: disable=C0111
class Command(BaseCommand):
    help = 'Creates combined subset text file based on given CSV file'

    # pylint: disable=C0330,no-self-use
    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='Path to combination CSV file')
        parser.add_argument(
            'systems_path', type=str, help='Path to systems text folder'
        )
        parser.add_argument('target_path', type=str, help='Path to target file')
        parser.add_argument(
            '--unicode',
            action='store_true',
            help='Expects text files in Unicode encoding',
        )
        parser.add_argument(
            '--ignore-ids',
            type=str,
            help='Defines comma separated list of segment IDs to ignore',
        )

    def handle(self, *args, **options):
        del args  # Unused.

        csv_file = options['csv_file']
        systems_path = options['systems_path']
        target_path = options['target_path']
        unicode_enc = options['unicode']
        ignore_ids = options['ignore_ids']

        segment_ids_to_ignore = []
        if ignore_ids:
            for segment_id in ignore_ids.split(','):
                segment_ids_to_ignore.append(int(segment_id))

        _msg = '\n[{0}]\n\n'.format(basename(__file__))
        self.stdout.write(_msg)

        self.stdout.write('    csv_file: {0}'.format(csv_file))
        self.stdout.write('systems_path: {0}'.format(systems_path))
        self.stdout.write(' target_path: {0}'.format(target_path))
        self.stdout.write('   --unicode: {0}'.format(unicode_enc))
        self.stdout.write('--ignore-ids: {0}'.format(ignore_ids))

        self.stdout.write('\n[INIT]\n\n')

        encoding = 'utf16' if unicode_enc else 'utf8'
        source_data = defaultdict(OrderedDict)
        systems_files = []
        systems_glob = '{0}{1}{2}'.format(systems_path, path_sep, "*.txt")

        for system_file in iglob(systems_glob):
            if '+' in basename(system_file):
                print(
                    'Cannot use system files with + in names '
                    'as this breaks multi-system meta systems:\n'
                    '{0}'.format(system_file)
                )
                sys_exit(-1)
            systems_files.append(system_file)

        for system_file in systems_files:
            system_data = Command._load_text_from_file(system_file, encoding)
            source_data[basename(system_file)] = system_data

        filtered_data = []
        with open(csv_file) as input_file:
            for line in input_file:
                _segment_id, system_id = line.strip().split(',')
                segment_id = int(_segment_id)
                filtered_data.append((segment_id, system_id))

        with open(target_path, mode='w', encoding=encoding) as output_file:
            for item in sorted(filtered_data, key=lambda x: x[0]):
                segment_id = item[0]
                system_id = item[1]

                if (
                    not system_id in source_data.keys()
                    or not segment_id in source_data[system_id].keys()
                ):
                    _msg = (
                        '{0}Segment ID {1} does not exist for system '
                        'ID {2}'.format(INFO_MSG, segment_id, system_id)
                    )
                    self.stdout.write(_msg)
                    continue

                if segment_id in segment_ids_to_ignore:
                    _msg = '{0}Ignoring segment_id={1}'.format(INFO_MSG, segment_id)
                    self.stdout.write(_msg)
                    continue

                line = source_data[system_id][segment_id]
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
