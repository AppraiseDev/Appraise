"""
Appraise evaluation framework

See LICENSE for usage details
"""
# pylint: disable=W0611
from collections import defaultdict
from collections import OrderedDict
from json import load
from os import makedirs
from os import path
from os.path import basename
from traceback import format_exc

from django.core.management.base import BaseCommand
from django.core.management.base import CommandError

INFO_MSG = 'INFO: '


class Command(BaseCommand):
    """
    Creates subset text files based on given JSON batch file.

    Takes a source text file and a JSON batch file, containing segment IDs.
    Determines system ID Based on the basename of the source text file, then
    computes the filtered subset of segments referenced in the JSON file.

    Writes output to the given target path, into a file named after the
    original file name, with an appended '.filtered.txt'.

    Supports --unicode to specify UTF-16 as text encoding and --ignore-ids
    to specify a comma separated list of IDs to ignore during file creation.
    """

    help = 'Creates subset text files based on given JSON batch file'

    # pylint: disable=C0330
    def add_arguments(self, parser):
        parser.add_argument('source_file', type=str, help='Path to source text file')
        parser.add_argument('json_file', type=str, help='Path to JSON batch file')
        parser.add_argument(
            'target_path',
            type=str,
            help='Path to bad reference text folder',
        )
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
        parser.add_argument(
            '--ref-file',
            type=str,
            help='Path to corresponding reference file',
        )
        parser.add_argument(
            '--src-file',
            type=str,
            help='Path to corresponding source file',
        )

    def handle(self, *args, **options):
        _msg = '\n[{0}]\n\n'.format(path.basename(__file__))
        self.stdout.write(_msg)

        self.stdout.write(' source_file: {0}'.format(options['source_file']))
        self.stdout.write('   json_file: {0}'.format(options['json_file']))
        self.stdout.write(' target_path: {0}'.format(options['target_path']))
        self.stdout.write('   --unicode: {0}'.format(options['unicode']))
        self.stdout.write('--ignore-ids: {0}'.format(options['ignore_ids']))
        self.stdout.write('  --ref-file: {0}'.format(options['ref_file']))
        self.stdout.write('  --src-file: {0}'.format(options['src_file']))

        self.stdout.write('\n[INIT]\n\n')

        # Load segment IDs to ignore during text processing.
        segment_ids_to_ignore = Command._load_ids_to_ignore(options['ignore_ids'])

        # Create target path if it does not exist.
        self._create_target_path(options['target_path'])

        # Set encoding based on --unicode argument.
        encoding = 'utf16' if options['unicode'] else 'utf8'

        # Load text from source file into OrderedDict.
        source_data = Command._load_text_from_file(options['source_file'], encoding)

        # Load reference text from reference file, iff given.
        ref_data = None
        if options['ref_file']:
            ref_data = Command._load_text_from_file(options['ref_file'], encoding)

        # Load source text from source file, iff given.
        src_data = None
        if options['src_file']:
            src_data = Command._load_text_from_file(options['src_file'], encoding)

        # Load segment ids for all systems from JSON batch file.
        ids_data = Command._load_ids_from_json_file(options['json_file'])

        # Filter segments for current system ID, creating sorted output.
        system_id = basename(options['source_file'])
        filtered_data = Command._filter_segments_for_system_id(
            system_id, ids_data, segment_ids_to_ignore
        )

        # Get text for filtered segments.
        filtered_text = [source_data[segment_id] for segment_id in filtered_data]

        # Write filtered data into target file.
        target_file = path.join(options['target_path'], system_id + '.filtered.txt')

        self._save_text_into_file(target_file, filtered_text, encoding=encoding)

        if ref_data:
            # Get reference text for filtered segments.
            reference_text = [ref_data[segment_id] for segment_id in filtered_data]

            # Write filtered reference data into target file.
            target_file = path.join(
                options['target_path'], system_id + '.reference.txt'
            )

            self._save_text_into_file(target_file, reference_text, encoding=encoding)

        if src_data:
            # Get source text for filtered segments.
            source_text = [src_data[segment_id] for segment_id in filtered_data]

            # Write filtered source data into target file.
            target_file = path.join(options['target_path'], system_id + '.source.txt')

            self._save_text_into_file(target_file, source_text, encoding=encoding)

        self.stdout.write('\n[DONE]\n\n')

    @staticmethod
    def _load_ids_to_ignore(ignore_ids):
        """
        Returns list of segment IDs which should be ignored.
        """
        segment_ids_to_ignore = []

        if ignore_ids:
            for segment_id in ignore_ids.split(','):
                segment_ids_to_ignore.append(int(segment_id))

        return segment_ids_to_ignore

    @staticmethod
    def _filter_segments_for_system_id(system_id, ids_data, segment_ids_to_ignore):
        """
        Filters segments in ids_data based on the given system ID.

        Segment IDs in segment_ids_to_ignore will be ignored.
        Output is sorted by increasing segment IDs.
        """
        filtered_data = []

        if system_id in ids_data.keys():
            for segment_id in sorted(ids_data[system_id]):
                if segment_id in segment_ids_to_ignore:
                    print('Ignoring segment_id={0}'.format(segment_id))
                    continue

                filtered_data.append(segment_id)

        else:
            print('Unknown system ID={0}'.format(system_id))

        return filtered_data

    @staticmethod
    def _load_ids_from_json_file(json_file):
        """
        Loads all segment IDs from the given JSON batch file.

        Creates defaultdict(list) and organises by system ID.
        This is constrained to only 'TGT' segments, as these
        are the only "real" system segments.

        Multi system IDs (containing +) will be split.
        """
        ids_data = defaultdict(list)

        with open(json_file) as input_file:
            json_data = load(input_file)

            for batch in json_data:
                for item in batch['items']:
                    if item['itemType'] in ('TGT', 'REF'):
                        segment_id = int(item['itemID'])
                        system_ids = item['targetID'].split('+')

                        for system_id in system_ids:
                            ids_data[system_id].append(segment_id)

        return ids_data

    def _save_text_into_file(self, file_path, file_text, encoding='utf8'):
        """
        Saves text from iterable into file.
        """
        try:
            _msg = '{0}Writing text file {1} ... '.format(INFO_MSG, file_path)
            self.stdout.write(_msg, ending='')

            # We enforce Windows line breaks here.
            # Maybe should be configurable instead?
            with open(file_path, mode='w', encoding=encoding) as output_file:
                for line in file_text:
                    output_file.write(line)
                    output_file.write('\r\n')

            self.stdout.write('OK')

        # pylint: disable=W0702
        except:
            self.stdout.write('FAIL')
            self.stdout.write(format_exc())

    @staticmethod
    def _load_text_from_file(file_path, encoding='utf8'):
        """
        Loads text from file into OrderedDict.

        Maps segment text to segment IDs (1-based).
        """
        file_text = OrderedDict()

        with open(file_path, encoding=encoding) as input_file:
            for zero_based_id, current_line in enumerate(input_file):
                file_text[zero_based_id + 1] = current_line.strip()

        return file_text

    def _create_target_path(self, target_path):
        """
        Creates target path if it does not exist.
        """
        if not path.exists(target_path):
            try:
                _msg = '{0}Creating target path {1} ... '.format(INFO_MSG, target_path)
                self.stdout.write(_msg, ending='')
                makedirs(target_path)
                self.stdout.write('OK')

            # pylint: disable=W0702
            except:
                self.stdout.write('FAIL')
                self.stdout.write(format_exc())
