"""
Appraise evaluation framework

See LICENSE for usage details
"""
import hashlib
import json
from collections import defaultdict
from collections import OrderedDict
from glob import iglob
from math import floor
from os.path import basename
from os.path import exists
from os.path import sep as path_sep
from random import randint
from random import randrange
from random import seed
from random import shuffle
from sys import exit as sys_exit

from django.core.management.base import BaseCommand
from django.core.management.base import CommandError

from Dashboard.models import LANGUAGE_CODES_AND_NAMES

# pylint: disable=E0401,W0611

# pylint: disable=C0111
class Command(BaseCommand):
    help = 'Creates JSON file containing DirectAssessmentTask data'

    # pylint: disable=C0330,no-self-use
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
            '--urls-file',
            type=str,
            default=None,
            help='Path to optional image URLs file',
        )
        parser.add_argument(
            '--task-definition',
            type=str,
            default="80:5:5:10",
            help='Defines (candidates, repeats, reference, bad refs) per task',
        )
        parser.add_argument(
            '--required-annotations',
            type=int,
            default=1,
            help='Specifies required annotations per batch (default: 1)',
        )
        parser.add_argument(
            '--random-seed',
            type=int,
            default=123456,
            help='Random generator seed value',
        )
        parser.add_argument(
            '--randomize',
            action='store_false',
            help='Randomize extracted work items',
        )
        parser.add_argument(
            '--pad-batches',
            action='store_true',
            help='Adds redundant batches to reach requested --max_batches',
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
            help='Enable character-based mode, default for Chinese and Japanese',
        )
        parser.add_argument(
            '--no-redundancy',
            action='store_true',
            help='Disable redundant quality control, maximising data collection',
        )
        parser.add_argument(
            '--ignore-empty',
            action='store_true',
            help='Replaces empty lines with "EMPTY_LINE"',
        )
        # TODO: add optional parameters to set source, reference and system IDs

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
    # When sampling data, we need to read in candidate translations in a stable
    # order. This works by creating a sorted list of file names and then shuffling
    # it once. Given the random seed value, this should be reproducible.
    #
    # For this to work, we have to ALWAYS seed the RNG. By default, we should use
    # msec after midnight. This also means that we have to expose/print the seed
    # value every time so that users know it.
    #
    # Once the random order of file names has been created, we read in candidate
    # translations. For each, we compute the MD5 hash of the .strip()ed Unicode
    # text, preserving case information. The MD5 hash will act as unique key for
    # the segment text. If multiple segments share the same segment text, they
    # will end up being mapped to the same key. In this case, the only difference
    # is (potentially) in the bad reference text. This should be identical for
    # identical candidate translations but there is no hard guarantee for this.
    # Hence, we agree to always use the bad reference text from the first system
    # being mapped to the respective MD5 key. The segment ID will always be the
    # same and hence is not an issue. Should the segment ID not match, we have
    # an inconsistent state and should abort sampling. It is fine if files do not
    # align wrt. the number of translations contained within each of the files as
    # long as identical candidate text has identical segment IDs. There is a
    # potential problem if multiple translations map to the different source
    # segments, thus ending up with different IDs. I have no idea what we can do
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
        del args  # Unused

        # Validate source and target language codes
        _all = list(set([x.lower() for x in LANGUAGE_CODES_AND_NAMES]))
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

        unicode_enc = options['unicode']
        use_local_src = options['local_src']
        use_local_ref = options['local_ref']
        create_ids = options['create_ids']
        source_based = options['source_based']
        no_redundancy = options['no_redundancy']

        # If no redundancy is specified, we will use 100 candidates instead.
        if no_redundancy:
            self.stdout.write('No redundancy set.')
            items_per_batch = (100, 0, 0, 0)

        # Otherwise, we will now parse the task definition parameter.
        else:
            try:
                # Extract task definition which is defined as:
                #
                # 1. number of candidates;
                # 2. number repeats;
                # 3. number of references; and
                # 4. number of bad references.
                task_def = [int(x) for x in options['task_definition'].split(':')]

                # At least half of the tasks items have to be candidates.
                if sum(task_def) == 100 and task_def[0] >= 50:
                    items_per_batch = tuple(task_def)

            except ValueError:
                self.stdout.write(
                    'Bad task definition value: {0!r}'.format(
                        options['task_definition']
                    )
                )

                # Fall back to default task definition.
                items_per_batch = (80, 5, 5, 10)

            finally:
                self.stdout.write('Using task definition: {0}'.format(items_per_batch))

        encoding = 'utf16' if unicode_enc else 'utf8'
        ignore_empty = options['ignore_empty']

        source_file = []
        if not use_local_src:
            source_file = Command._load_text_from_file(
                options['source_file'], encoding, ignore_empty
            )
            print('Loaded {0} source segments'.format(len(source_file.keys())))

        reference_file = []
        if not use_local_ref:
            reference_file = Command._load_text_from_file(
                options['reference_file'], encoding, ignore_empty
            )
            print('Loaded {0} reference segments'.format(len(reference_file.keys())))

        urls_file = []
        if options['urls_file'] is not None:
            urls_file = Command._load_text_from_file(
                options['urls_file'], encoding, ignore_empty
            )
            print('Loaded {0} image URLs'.format(len(urls_file.keys())))

        systems_files = []
        systems_path = options['systems_path']
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

        random_seed_value = options['random_seed']

        systems_files.sort()
        seed(random_seed_value)
        shuffle(systems_files)

        hashed_text = {}
        hashes_by_ids = defaultdict(list)

        # Not sure of this should rather be used...
        # or ((_tgt == 'zho' or _tgt == 'jpn') and not source_based) \
        #
        character_based = (
            _tgt == 'zho'
            or _tgt == 'jpn'
            or ((_src == 'zho' or _src == 'jpn') and source_based)
            or options['character_based']
        )
        print(f'character_based = {character_based}')

        for system_path in systems_files:
            system_txt = Command._load_text_from_file(
                system_path, encoding, ignore_empty
            )
            # Generate bad references on the fly
            #
            # To do so, we will load a random source segment to fill in a
            # randomly positioned phrase in the given candidate translation.
            #
            # system_bad = Command._load_text_from_file(
            #     system_path.replace('.txt', '.bad'), encoding, ignore_empty)

            # TODO: decide whether to drop use of system_ids.
            # pylint: disable=W0612
            if not create_ids:
                system_ids = Command._load_text_from_file(
                    system_path.replace('.txt', '.ids'),
                    encoding,
                    ignore_empty,
                )
            else:
                system_ids = [x + 1 for x in range(len(system_txt))]
            # BASICALLY: add support for local system_src and system_ref files
            # here. If such files are present, this will overwrite the global
            # src/ref values. However, this does not fully resolve the issue
            # as we still have to give a source text file, while is assumed to
            # be shared...
            #
            # IN A SENSE, using these local files makes better sense. It is
            # wasteful, though.
            #
            # MAYBE, it is better to simply generate a simple JSON config?!
            local_src = []
            local_ref = []

            if use_local_src:
                local_src_path = system_path.replace('.txt', '.src')
                if exists(local_src_path):
                    local_src = Command._load_text_from_file(
                        local_src_path, encoding, ignore_empty
                    )

            if use_local_ref:
                local_ref_path = system_path.replace('.txt', '.ref')
                if exists(local_ref_path):
                    local_ref = Command._load_text_from_file(
                        local_src_path, encoding, ignore_empty
                    )

            for segment_id, segment_text in system_txt.items():
                # TODO: fix long lines.
                _src = (
                    local_src[segment_id] if use_local_src else source_file[segment_id]
                )
                _ref = (
                    local_ref[segment_id]
                    if use_local_ref
                    else reference_file[segment_id]
                )

                md5hash = hashlib.new(
                    'md5',
                    segment_text.encode(encoding)
                    + _src.encode(encoding)
                    + _ref.encode(encoding),
                ).hexdigest()

                _url = urls_file[segment_id] if urls_file else None

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
                    _bad_len = 6  # len(_tokens) // 4

                if character_based:
                    _bad_len = 2 * _bad_len

                # Choose random src/ref segment
                _bad_tokens = []
                while len(_bad_tokens) <= _bad_len:
                    # TODO: fix long lines.
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
                    # if source_based:
                    #     _bad_text = source_file[_bad_id]
                    #     if use_local_src:
                    #         _bad_text = local_src[_bad_id]
                    #
                    # We are currently forcing reference-based bad reference
                    # generation. If no reference is available, then a copy
                    # of the source file will work just fine.
                    #
                    # pylint: disable=using-constant-test

                    _bad_text = reference_file[_bad_id]
                    if use_local_ref:
                        _bad_text = local_ref[_bad_id]

                    _bad_tokens = _bad_text.split(' ')
                    if character_based:
                        _bad_tokens = _bad_text

                # If dealing with Chinese or Japanese, use double the amount
                # of characters for the bad replacement phrase.
                _bad_phrase = None

                # TODO: fix long lines.
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

                segment_bad = ' '.join(_bad)
                if character_based:
                    segment_bad = ''.join(_bad)

                if not md5hash in hashed_text.keys():
                    hashed_text[md5hash] = {
                        'segment_id': segment_id,
                        'segment_text': segment_text,
                        'segment_bad': segment_bad,
                        'segment_ref': _ref,
                        'segment_src': _src,
                        'systems': [basename(system_path)],
                    }

                    if _url:
                        hashed_text[md5hash].update({'segment_url': _url})

                    hashes_by_ids[segment_id].append(md5hash)

                else:
                    hashed_text[md5hash]['systems'].append(basename(system_path))

            print(
                'Loaded {0} system {1} segments'.format(
                    len(system_txt.keys()), basename(system_path)
                )
            )

        # Dump deduplicated segment data to JSON file.
        json_data = json.dumps(hashed_text, indent=2, sort_keys=True)
        segments_file_name = options['output_json_file'] + '.segments'
        with open(segments_file_name, mode='w', encoding='utf8') as out_file:
            self.stdout.write('Creating {0} ... '.format(segments_file_name), ending='')
            out_file.write(str(json_data))
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

        # Number of candidates in first position of items_per_batch tuple.
        batch_items = items_per_batch[0]
        missing_items = batch_items - len(all_keys) % batch_items
        print(
            'Missing items is {0}/{1}/{2}'.format(
                missing_items, batch_items, len(all_keys)
            )
        )

        all_keys.extend(all_keys[0:missing_items])
        print('Added {0} missing items rotating keys'.format(missing_items))

        total_batches = int(floor(len(all_keys) / batch_items))
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
        for batch_id in batch_nos:
            block_data = []

            block_start = batch_id * items_per_batch[0]
            block_end = block_start + items_per_batch[0]
            block_hashes = all_keys[block_start:block_end]

            block_hashes.sort()
            shuffle(block_hashes)

            check_ids = list(range(50))
            shuffle(check_ids)

            # Determine segment ids for redundant quality controls.
            chk_items, ref_items, bad_items = items_per_batch[1:]
            print(chk_items, ref_items, bad_items)

            start_index = 0
            end_index = chk_items
            chk_ids = check_ids[start_index:end_index]

            start_index = end_index
            end_index += ref_items
            ref_ids = check_ids[start_index:end_index]

            start_index = end_index
            end_index += bad_items
            bad_ids = check_ids[start_index:end_index]

            print(chk_ids, ref_ids, bad_ids)
            batch_items = [None for _ in range(100)]
            for index, item_hash in enumerate(block_hashes[:50]):
                batch_items[index] = (item_hash, 'TGT')

                item_type = None
                if index in chk_ids:
                    item_type = 'CHK'

                elif index in ref_ids:
                    item_type = 'REF'

                elif index in bad_ids:
                    item_type = 'BAD'

                if item_type is not None:
                    batch_items[index + 50] = (item_hash, item_type)

            emtpy_slots = []
            for index in range(50):
                if batch_items[index + 50] is None:
                    emtpy_slots.append(index + 50)
            print('empty_slots', emtpy_slots)
            for index, item_hash in zip(emtpy_slots, block_hashes[50:]):
                batch_items[index] = (item_hash, 'TGT')

            print(len(batch_items))
            print(len([x for x in batch_items if x is None]))

            # Ensure randomness of TGT, CHK, REF, BAD items.
            # We do this by randomly swapping pairs at positions (x, x+50).
            for index in range(50):
                random_swap = randint(0, 1)
                if random_swap == 1:
                    temp_value = batch_items[index]
                    batch_items[index] = batch_items[index + 50]
                    batch_items[index + 50] = temp_value

            num_blocks = 10
            for block_id in range(num_blocks):
                block_start = 10 * block_id
                block_end = 10 * (block_id + 1)
                block_items = batch_items[block_start:block_end]

                current_block = {'block_items': block_items}

                block_data.append(current_block)

            # Direct assessment is reference-based for WMT17
            if source_based:
                source_id = basename(options['source_file'])
                if use_local_src:
                    source_id = 'LOCAL_SRC'

            else:
                source_id = basename(options['reference_file'])
                if use_local_ref:
                    source_id = 'LOCAL_REF'

            # Remember, batch numbers are one-based
            task_data = OrderedDict(
                {
                    'batchNo': batch_id + 1,
                    'batchSize': options['batch_size'],
                    'sourceLanguage': options['source_language'],
                    'targetLanguage': options['target_language'],
                    'requiredAnnotations': options['required_annotations'],
                    'randomSeed': random_seed_value,
                }
            )
            items_data = []
            _item = 0

            for block_id in range(num_blocks):
                block_items = block_data[block_id]['block_items']

                for current_item, current_type in block_items:
                    item_data = hashed_text[current_item]

                    item_id = item_data['segment_id']
                    item_text = item_data['segment_text']
                    item_bad = item_data['segment_bad']
                    item_ref = item_data['segment_ref']
                    item_src = item_data['segment_src']
                    item_url = item_data.get('segment_url')
                    item_systems = item_data['systems']

                    target_id = '+'.join(sorted(set(item_systems)))
                    target_text = item_text
                    if current_type == 'REF':
                        target_id = basename(options['reference_file'])
                        target_text = item_ref

                    elif current_type == 'BAD':
                        target_text = item_bad

                    obj = OrderedDict()
                    obj['_item'] = _item
                    obj['_block'] = block_id + (10 * batch_id)
                    obj['sourceID'] = source_id
                    obj['sourceText'] = item_ref
                    if source_based:
                        obj['sourceText'] = item_src
                    obj['targetID'] = target_id
                    obj['targetText'] = target_text
                    obj['itemID'] = item_id
                    obj['itemType'] = current_type

                    if item_url is not None:
                        obj['imageURL'] = item_url

                    items_data.append(obj)
                    _item += 1

            output_data = OrderedDict({'task': task_data, 'items': items_data})

            json_data.append(output_data)

        if options['pad_batches'] and max_batches is not None:
            pad_size = max_batches - len(json_data)
            print('pad_size = {0}'.format(pad_size))
            for pad_index in range(pad_size):
                json_data.append(json_data[pad_index])

        json_data = json.dumps(json_data, indent=2, sort_keys=True)
        # print(json_data)

        json_file_name = options['output_json_file']
        with open(json_file_name, mode='w', encoding='utf8') as out_file:
            self.stdout.write(
                'Creating {0} ... '.format(options['output_json_file']),
                ending='',
            )
            out_file.write(str(json_data))
            self.stdout.write('OK')

    # TODO: use module-level function instead, moving to different file.
    @staticmethod
    def _load_text_from_file(file_path, encoding='utf8', ignore_empty=False):
        segment_id = 0
        file_text = OrderedDict()

        with open(file_path, encoding=encoding) as input_file:
            for current_line in input_file:
                segment_id += 1
                cleaned_line = current_line.strip()
                if not cleaned_line:
                    if not ignore_empty:
                        _msg = (
                            f'Empty segment id={segment_id}! Use '
                            '--ignore-empty to replace with "EMPTY_LINE".'
                        )
                        raise ValueError(_msg)

                    else:
                        _msg = (
                            f'Empty segment id={segment_id}! '
                            'Replaced with "EMPTY_LINE".'
                        )
                        cleaned_line = 'EMPTY_LINE'
                        print(_msg)

                file_text[segment_id] = cleaned_line

        return file_text
