"""
Appraise evaluation framework

See LICENSE for usage details
"""
# pylint: disable=W0611
import json
from collections import defaultdict
from collections import OrderedDict
from math import floor
from os.path import basename
from random import randrange
from random import seed
from random import shuffle
from sys import exit as sys_exit

from django.core.management.base import BaseCommand
from django.core.management.base import CommandError

from Dashboard.models import LANGUAGE_CODES_AND_NAMES

# pylint: disable=C0111
class Command(BaseCommand):
    help = 'Creates JSON file containing DirectAssessmentTask data'

    # pylint: disable=C0330
    def add_arguments(self, parser):
        parser.add_argument('batch_size', type=int, help='Total batch size')
        parser.add_argument('source_language', type=str, help='Source language code')
        parser.add_argument('target_language', type=str, help='Target language code')
        parser.add_argument('source_file', type=str, help='Path to source text file')
        parser.add_argument(
            'reference_file', type=str, help='Path to reference text file'
        )
        parser.add_argument(
            'systems_path', type=str, help='Path to systems text folder'
        )
        parser.add_argument(
            'output_json_file', type=str, help='Path to JSON output file'
        )
        parser.add_argument(
            '--block-definition',
            type=str,
            default="7:1:1:1",
            help='Defines (candidates, redundant, reference, bad reference) per block',
        )
        parser.add_argument(
            '--required-annotations',
            type=int,
            default=1,
            help='Specifies required annotations per batch (default: 1)',
        )
        parser.add_argument(
            '--random-seed',
            type=int,  # required=False,
            help='Random generator seed value',
        )
        parser.add_argument(
            '--randomize',
            action='store_false',
            help='Randomize extracted work items',
        )
        parser.add_argument(
            '--batch-no',
            type=int,
            default=1,
            help='Specifies desired batch no (default: 1)',
        )
        parser.add_argument(
            '--max-batches',
            type=int,
            help='Specifies max number of batches to create',
        )
        parser.add_argument(
            '--all-batches',
            action='store_true',
            help='Produces all possible batches at once',
        )
        parser.add_argument(
            '--source-based',
            action='store_true',
            help='Creates source-based work items',
        )
        parser.add_argument(
            '--unicode',
            action='store_true',
            help='Expects text files in Unicode encoding',
        )
        parser.add_argument(
            '--local-src',
            action='store_true',
            help='Loads source text from local .src files',
        )
        parser.add_argument(
            '--local-ref',
            action='store_true',
            help='Loads reference text from local .ref files',
        )
        parser.add_argument(
            '--create-ids',
            action='store_true',
            help='Creates segment ids without local .ids files',
        )
        parser.add_argument(
            '--full-coverage',
            action='store_true',
            help='Ensures segments are fully covered',
        )
        parser.add_argument(
            '--character-based',
            action='store_true',
            help='Enable character-based processing, default for Chinese and Japanese',
        )
        # TODO: add optional parameters to set source, reference and system IDs

        # TODO: add exclude argument which prevents creation of redundant data?

    ###
    #
    # Fake BAD REF generation
    # Simply insert "BAD" and "REF" somewhere into the reference text
    #
    # We end up having three folders:
    # 1) for candidate translations
    # 2) for bad references
    # 3) for segment ids
    #
    # We should think about using one folder, allowing two special files:
    # - $fileName.badRef
    # - $fileName.segmentIds
    #
    # We operate on k files, one per submitted system.
    #
    # When sampling data, we need to read in candidate translations in a stable order.
    # This works by creating a sorted list of file names and then shuffling it once.
    # Given the random seed value, this should be reproducible.
    #
    # For this to work, we have to ALWAYS seed the RNG. By default, we should use msec after midnight.
    # This also means that we have to expose/print the seed value every time so that users know it.
    #
    # Once the random order of file names has been created, we read in candidate translations.
    # For each, we compute the MD5 hash of the .strip()ed Unicode text, preserving case information.
    # The MD5 hash will act as unique key for the segment text. If multiple segments share the same
    # segment text, they will end up being mapped to the same key. In this case, the only difference
    # is (potentially) in the bad reference text. This should be identical for identical candidate
    # translations but there is no hard guarantee for this. Hence, we agree to always use the bad
    # reference text from the first system being mapped to the respective MD5 key. The segment ID
    # will always be the same and hence is not an issue. Should the segment ID not match, we have
    # an inconsistent state and should abort sampling. It is fine if files do not align wrt. the
    # number of translations contained within each of the files as long as identical candidate text
    # has identical segment IDs. There is a potential problem if multiple translations map to the
    # different source segments, thus ending up with different IDs. I have no idea what we can do
    # about this case.
    #
    # Number of blocks = d
    # distance for checks = (d/2)
    # default number d = 10
    #
    # Block defined as 10 items
    # Randomly ordered
    # 7 candidate translations
    # 2 reference translations
    # 1 bad reference (specific to candiate translation)
    #
    # 7,2,1 specification
    # Can be different for other scenarios
    # --block-spec="7S2R1B"
    #
    # Question for Yvette:
    #
    # DO BAD REFERENCES HAVE TO BE IDENTICAL FOR IDENTICAL SYSTEM TRANSLATIONS?
    #
    # Requirement for Christian:
    #
    # I WANT THE SAMPLING TO BE REPRODUCIBLE GIVEN THE SAME RANDOM SEED VALUE
    #
    ###

    def handle(self, *args, **options):
        # Validate source and target language codes
        _all = list(set([x.lower() for x in LANGUAGE_CODES_AND_NAMES.keys()]))
        _all.sort()
        _src = options['source_language'].lower()
        if not _src in _all:
            self.stdout.write('Unknown source language: {0}!'.format(_src))
            self.stdout.write('Known languages: {0}'.format(', '.join(_all)))
            return

        _tgt = options['target_language'].lower()
        if not _tgt in _all:
            self.stdout.write('Unknown target language: {0}!'.format(_tgt))
            self.stdout.write('Known languages: {0}'.format(', '.join(_all)))
            return

        # Initialize random number generator
        # Extract batch size number of pairs, randomizing order if requested
        # Serialize pairs into JSON format
        # Write out JSON output file

        batch_size = options['batch_size']
        unicode_enc = options['unicode']
        use_local_src = options['local_src']
        use_local_ref = options['local_ref']
        create_ids = options['create_ids']
        source_based = options['source_based']

        block_size = 10
        block_annotations = 7
        block_redundants = 1
        block_references = 1
        block_badrefs = 1

        # IF BLOCK DEF IS GIVEN, DO SOMETHING WITH IT
        if options['block_definition'] is not None:
            print("WOOHOO")

        if (batch_size % block_size) > 0:
            self.stdout.write('Batch size needs to be divisible by block size!')
            return

        # CHECK THAT WE END UP WITH EVEN NUMBER OF BLOCKS

        print('We will create {0} blocks'.format(int(batch_size / block_size)))

        # TODO: add parameter to set encoding
        # TODO: need to use OrderedDict to preserve segment IDs' order!
        encoding = 'utf16' if unicode_enc else 'utf8'

        source_file = []
        if not use_local_src:
            source_file = Command._load_text_from_file(options['source_file'], encoding)
            print('Loaded {0} source segments'.format(len(source_file.keys())))

        reference_file = []
        if not use_local_ref:
            reference_file = Command._load_text_from_file(
                options['reference_file'], encoding
            )
            print('Loaded {0} reference segments'.format(len(reference_file.keys())))

        systems_files = []
        systems_path = options['systems_path']
        from glob import iglob
        import os.path

        for system_file in iglob(
            '{0}{1}{2}'.format(systems_path, os.path.sep, "*.txt")
        ):
            if '+' in basename(system_file):
                print(
                    'Cannot use system files with + in names '
                    'as this breaks multi-system meta systems:\n'
                    '{0}'.format(system_file)
                )
                sys_exit(-1)
            systems_files.append(system_file)

        random_seed_value = 123456

        systems_files.sort()
        seed(random_seed_value)
        shuffle(systems_files)
        # ADD RANDOMIZED SHUFFLING HERE?

        import hashlib

        hashed_text = {}
        hashes_by_ids = defaultdict(list)

        character_based = _tgt == 'zho' or _tgt == 'jpn' or options['character_based']

        for system_path in systems_files:
            system_txt = Command._load_text_from_file(system_path, encoding)
            # Generate bad references on the fly
            #
            # To do so, we will load a random source segment to fill in a
            # randomly positioned phrase in the given candidate translation.
            #
            # system_bad = Command._load_text_from_file(system_path.replace('.txt', '.bad'), encoding)

            if not create_ids:
                system_ids = Command._load_text_from_file(
                    system_path.replace('.txt', '.ids'), encoding
                )
            else:
                system_ids = [x + 1 for x in range(len(system_txt))]
            # BASICALLY: add support for local system_src and system_ref files here.
            #   If such files are present, this will overwrite the global src/ref values.
            #   However, this does not fully resolve the issue as we still have to give
            #   a source text file, while is assumed to be shared...
            #
            # IN A SENSE, using these local files makes better sense. It is wasteful, though.
            #   MAYBE, it is better to simply generate a simple JSON config file?!
            local_src = []
            local_ref = []

            if use_local_src:
                local_src_path = system_path.replace('.txt', '.src')
                if os.path.exists(local_src_path):
                    local_src = Command._load_text_from_file(local_src_path, encoding)

            if use_local_ref:
                local_ref_path = system_path.replace('.txt', '.ref')
                if os.path.exists(local_ref_path):
                    local_ref = Command._load_text_from_file(local_src_path, encoding)

            for segment_id, segment_text in system_txt.items():
                _src = (
                    local_src[segment_id] if use_local_src else source_file[segment_id]
                )
                _ref = (
                    local_src[segment_id]
                    if use_local_ref
                    else reference_file[segment_id]
                )
                md5hash = hashlib.new(
                    'md5',
                    segment_text.encode(encoding)
                    + _src.encode(encoding)
                    + _ref.encode(encoding),
                ).hexdigest()

                # Determine length of bad phrase, relative to segment length
                #
                # This follows WMT17:
                # - http://statmt.org/wmt17/pdf/WMT17.pdf

                _bad_len = 1
                _tokens = segment_text if character_based else segment_text.split(' ')

                if len(_tokens) == 1:
                    _bad_len = 1
                elif len(_tokens) > 1 and len(_tokens) <= 5:
                    _bad_len = 2
                elif len(_tokens) > 5 and len(_tokens) <= 8:
                    _bad_len = 3
                elif len(_tokens) > 8 and len(_tokens) <= 15:
                    _bad_len = 4
                elif len(_tokens) > 15 and len(_tokens) <= 20:
                    _bad_len = 5
                else:
                    _bad_len = len(_tokens) // 4

                if character_based:
                    _bad_len = 2 * _bad_len

                # Choose random src/ref segment
                _bad_tokens = []
                while len(_bad_tokens) <= _bad_len:
                    _bad_id = (
                        randrange(0, len(local_ref)) + 1
                        if use_local_ref
                        else randrange(0, len(reference_file)) + 1
                    )

                    if source_based:
                        _bad_id = (
                            randrange(0, len(local_src)) + 1
                            if use_local_src
                            else randrange(0, len(source_file)) + 1
                        )

                    _bad_text = None
                    #                    if source_based:
                    #                        _bad_text = local_src[_bad_id] if use_local_src else source_file[_bad_id]
                    #                    else:
                    #
                    # We are currently forcing reference-based bad reference
                    # generation. If no reference is available, then a copy
                    # of the source file will work just fine.
                    #
                    if True:
                        _bad_text = (
                            local_ref[_bad_id]
                            if use_local_ref
                            else reference_file[_bad_id]
                        )

                    _bad_tokens = _bad_text if character_based else _bad_text.split(' ')

                # If dealing with Chinese or Japanese, use double the amount
                # of characters for the bad replacement phrase.
                _bad_phrase = None

                _index = (
                    randrange(0, len(_bad_tokens) - _bad_len)
                    if len(_bad_tokens) - _bad_len > 0
                    else 0
                )
                _bad_phrase = _bad_tokens[_index : _index + _bad_len]

                _index = (
                    randrange(0, len(_tokens) - _bad_len)
                    if len(_tokens) - _bad_len > 0
                    else 0
                )
                _bad = _tokens[:_index] + _bad_phrase + _tokens[_index + _bad_len :]

                segment_bad = ''.join(_bad) if character_based else ' '.join(_bad)

                if not md5hash in hashed_text.keys():
                    hashed_text[md5hash] = {
                        'segment_id': segment_id,
                        'segment_text': segment_text,
                        'segment_bad': segment_bad,
                        'segment_ref': _ref,
                        'segment_src': _src,
                        'systems': [os.path.basename(system_path)],
                    }

                    hashes_by_ids[segment_id].append(md5hash)
                else:
                    hashed_text[md5hash]['systems'].append(
                        os.path.basename(system_path)
                    )

            print(
                'Loaded {0} system {1} segments'.format(
                    len(system_txt.keys()), os.path.basename(system_path)
                )
            )

        # Dump deduplicated segment data to JSON file.
        json_data = json.dumps(hashed_text, indent=2, sort_keys=True)
        with open(
            options['output_json_file'] + '.segments',
            mode='w',
            encoding='utf8',
        ) as output_file:
            self.stdout.write(
                'Creating {0} ... '.format(options['output_json_file'] + '.segments'),
                ending='',
            )
            output_file.write(str(json_data))
            self.stdout.write('OK')

        all_keys = list(hashed_text.keys())
        all_keys.sort()
        shuffle(all_keys)

        # If --full-coverage is specified, we want to collect annotations for
        # all unique translations for any given segment ID. To do so, we loop
        # over the all_keys list and for each MD5 hash we have not consumed,
        # we add not only the MD5 hash itself but also all other MD5 hashes
        # matching the respective segment ID.
        full_coverage = options['full_coverage']
        if full_coverage:
            _sorted_keys = []
            for key in all_keys:
                if not key in _sorted_keys:
                    segment_id = hashed_text[key]['segment_id']
                    matching_keys = hashes_by_ids[segment_id]
                    matching_keys.sort()
                    _sorted_keys.extend(matching_keys)
            all_keys = _sorted_keys

        items_per_batch = 10 * 7

        missing_items = items_per_batch - len(all_keys) % items_per_batch
        print('Missing items is {0}/{1}'.format(missing_items, items_per_batch))

        all_keys.extend(all_keys[0:missing_items])
        print('Added {0} missing items rotating keys'.format(missing_items))

        total_batches = int(floor(len(all_keys) / items_per_batch))
        print('Total number of batches is {0}'.format(total_batches))

        batch_no = options['batch_no']
        max_batches = options['max_batches']
        all_batches = options['all_batches']

        # If we don't produce all batches, our batch_id will be batch_no-1.
        # This is because batch numbers are one-based, ids zero-indexed.
        #
        # If we produce all batches, we just use range(total_batches).
        # This implicitly gives us zero-indexed ids already.
        batch_nos = [batch_no - 1] if not all_batches else list(range(total_batches))
        if max_batches:
            batch_nos = batch_nos[:max_batches]

        json_data = []
        for batch_id in batch_nos:  # range(batch_no):
            block_data = []
            block_offset = batch_id * 10 * 7

            num_blocks = int(batch_size / block_size)
            for block_id in range(num_blocks):
                # Human readable ids are one-based, hence +1
                print(
                    'Creating batch {0:05}/{1:05}, block {2:02}'.format(
                        batch_id + 1, total_batches, block_id + 1
                    )
                )

                # Get 7 random system outputs
                block_start = block_offset + 7 * (block_id)
                block_end = block_start + 7
                block_hashes = all_keys[block_start:block_end]

                current_block = {'systems': block_hashes}

                block_data.append(current_block)

            # Compute redundant, reference, bad reference bits
            for block_id in range(num_blocks):
                check_id = int((block_id + (num_blocks / 2)) % num_blocks)
                # Human readable ids are one-based, hence +1
                print(
                    'Add checks for batch {0:05}/{1:05}, '
                    'block {2:02} to block {3:02}'.format(
                        batch_id + 1,
                        total_batches,
                        check_id + 1,
                        block_id + 1,
                    )
                )

                check_systems = block_data[check_id]['systems']
                check_systems.sort()
                shuffle(check_systems)

                block_data[block_id]['redundant'] = check_systems[0]
                block_data[block_id]['reference'] = check_systems[1]
                block_data[block_id]['badref'] = check_systems[2]

            # Direct assessment is reference-based for WMT17
            if source_based:
                sourceID = (
                    'LOCAL_SRC' if use_local_src else basename(options['source_file'])
                )
            else:
                sourceID = (
                    'LOCAL_REF'
                    if use_local_ref
                    else basename(options['reference_file'])
                )

            # Remember, batch numbers are one-based
            taskData = OrderedDict(
                {
                    'batchNo': batch_id + 1,
                    'batchSize': options['batch_size'],
                    'sourceLanguage': options['source_language'],
                    'targetLanguage': options['target_language'],
                    'requiredAnnotations': options['required_annotations'],
                    'randomSeed': random_seed_value,
                }
            )
            itemsData = []
            _item = 0

            for block_id in range(num_blocks):
                all_items = [(x, 'TGT') for x in block_data[block_id]['systems']]
                all_items.append((block_data[block_id]['redundant'], 'CHK'))
                all_items.append((block_data[block_id]['reference'], 'REF'))
                all_items.append((block_data[block_id]['badref'], 'BAD'))
                shuffle(all_items)

                for current_item, current_type in all_items:
                    item_data = hashed_text[current_item]

                    item_id = item_data['segment_id']
                    item_text = item_data['segment_text']
                    item_bad = item_data['segment_bad']
                    item_ref = item_data['segment_ref']
                    item_src = item_data['segment_src']
                    item_systems = item_data['systems']

                    targetID = '+'.join(sorted(set(item_systems)))
                    targetText = item_text
                    if current_type == 'REF':
                        targetID = basename(options['reference_file'])
                        targetText = item_ref

                    elif current_type == 'BAD':
                        targetText = item_bad

                    obj = OrderedDict()
                    obj['_item'] = _item
                    obj['_block'] = block_id + (10 * batch_id)
                    obj['sourceID'] = sourceID
                    obj['sourceText'] = item_ref if not source_based else item_src
                    obj['targetID'] = targetID
                    obj['targetText'] = targetText
                    obj['itemID'] = item_id
                    obj['itemType'] = current_type

                    itemsData.append(obj)
                    _item += 1

            outputData = OrderedDict({'task': taskData, 'items': itemsData})

            json_data.append(outputData)

        json_data = json.dumps(json_data, indent=2, sort_keys=True)
        print(json_data)

        with open(
            options['output_json_file'], mode='w', encoding='utf8'
        ) as output_file:
            self.stdout.write(
                'Creating {0} ... '.format(options['output_json_file']),
                ending='',
            )
            output_file.write(str(json_data))
            self.stdout.write('OK')

    @staticmethod
    def _load_text_from_file(file_path, encoding='utf8'):
        segment_id = 0
        file_text = OrderedDict()

        with open(file_path, encoding=encoding) as input_file:
            for current_line in input_file:
                segment_id += 1
                file_text[segment_id] = current_line.strip()

        return file_text
