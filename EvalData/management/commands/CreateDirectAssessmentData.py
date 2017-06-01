"""
Appraise evaluation framework
"""
# pylint: disable=W0611
import json
from django.core.management.base import BaseCommand, CommandError
from collections import defaultdict, OrderedDict
from os.path import basename
from random import seed, shuffle

# pylint: disable=C0111
class Command(BaseCommand):
    help = 'Creates JSON file containing DirectAssessmentTask data'

    # pylint: disable=C0330
    def add_arguments(self, parser):
        parser.add_argument(
          'batch_size', type=int,
          help='Total batch size'
        )
        parser.add_argument(
          'source_language', type=str,
          help='Source language code'
        )
        parser.add_argument(
          'target_language', type=str,
          help='Target language code'
        )
        parser.add_argument(
          'source_file', type=str,
          help='Path to source text file'
        )
        parser.add_argument(
          'reference_file', type=str,
          help='Path to reference text file'
        )
        parser.add_argument(
          'systems_path', type=str,
          help='Path to systems text folder'
        )
        parser.add_argument(
          'output_json_file', type=str,
          help='Path to JSON output file'
        )
        parser.add_argument(
          '--block-definition', type=str, default="7:1:1:1",
          help='Defines (candidates, redundant, reference, bad reference) per block'
        )
        parser.add_argument(
          '--random-seed', type=int, # required=False,
          help='Random generator seed value'
        )
        parser.add_argument(
          '--randomize', required=False, action='store_true',
          help='Randomize extracted work items'
        )
        parser.add_argument(
          '--batch-no', type=int, default=1,
          help='Specifies desired batch no (default: 1)'
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
        # Initialize random number generator
        # Extract batch size number of pairs, randomizing order if requested
        # Serialize pairs into JSON format
        # Write out JSON output file

        batch_size = options['batch_size']

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
        source_file = Command._load_text_from_file(options['source_file'], 'utf8')
        print('Loaded {0} source segments'.format(len(source_file.keys())))

        reference_file = Command._load_text_from_file(options['reference_file'], 'utf8')
        print('Loaded {0} reference segments'.format(len(reference_file.keys())))

        systems_files = []
        systems_path = options['systems_path']
        from glob import iglob
        import os.path
        for system_file in iglob('{0}{1}{2}'.format(systems_path, os.path.sep, "*.txt")):
            systems_files.append(system_file)

        random_seed_value = 123456

        systems_files.sort()
        seed(random_seed_value)
        shuffle(systems_files)
        # ADD RANDOMIZED SHUFFLING HERE?

        import hashlib
        hashed_text = {}

        for system_path in systems_files:
            system_txt = Command._load_text_from_file(system_path, 'utf8')
            system_bad = Command._load_text_from_file(system_path.replace('.txt', '.bad'), 'utf8')
            system_ids = Command._load_text_from_file(system_path.replace('.txt', '.ids'), 'utf8')

            for segment_id, segment_text in system_txt.items():
                md5hash = hashlib.new('md5', segment_text.encode('utf8')).hexdigest()
                if not md5hash in hashed_text.keys():
                    hashed_text[md5hash] = {
                      'segment_id': segment_id,
                      'segment_text': segment_text,
                      'segment_bad': system_bad[segment_id],
                      'segment_ref': reference_file[segment_id],
                      'segment_src': source_file[segment_id],
                      'systems': [os.path.basename(system_path)]
                    }
                else:
                    hashed_text[md5hash]['systems'].append(os.path.basename(system_path))

            print('Loaded {0} system {1} segments'.format(len(system_txt.keys()), os.path.basename(system_path)))

        all_keys = list(hashed_text.keys())
        all_keys.sort()
        shuffle(all_keys)

        batch_no = options['batch_no']

        for batch_id in range(batch_no):
            block_data = []
            block_offset = batch_id * 10 * 7

            num_blocks = int(batch_size/block_size)
            for block_id in range(num_blocks):
                print('Creating block {0}'.format(block_id))

                # Get 7 random system outputs
                block_start = block_offset + 7 * (block_id)
                block_end = block_start + 7
                block_hashes = all_keys[block_start:block_end]

                current_block = {
                  'systems': block_hashes
                }

                block_data.append(current_block)

            # Compute redundant, reference, bad reference bits
            for block_id in range(num_blocks):
                check_id = int((block_id + (num_blocks/2)) % num_blocks)
                print('Add checks for block {0} to block {1}'.format(check_id, block_id))

                check_systems = block_data[check_id]['systems']
                check_systems.sort()
                shuffle(check_systems)

                block_data[block_id]['redundant'] = check_systems[0]
                block_data[block_id]['reference'] = check_systems[1]
                block_data[block_id]['badref'] = check_systems[2]

            # Direct assessment is reference-based for WMT17
            sourceID = basename(options['reference_file'])

            taskData = OrderedDict({
              'batchSize': options['batch_size'],
              'sourceLanguage': options['source_language'],
              'targetLanguage': options['target_language'],
              'requiredAnnotations': 1,
              'randomSeed': random_seed_value
            })
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

                    targetID = '+'.join(item_systems)
                    targetText = item_text
                    if current_type == 'REF':
                        targetID = basename(options['reference_file'])
                        targetText = item_ref
                    elif current_item == 'BAD':
                        targetText = item_bad

                    obj = OrderedDict()
                    obj['_item'] = _item
                    obj['_block'] = block_id + (10 * batch_no)
                    obj['sourceID'] = sourceID
                    obj['sourceText'] = item_ref
                    obj['targetID'] = targetID
                    obj['targetText'] = targetText
                    obj['itemID'] = item_id
                    obj['itemType'] = current_type

                    itemsData.append(obj)
                    _item += 1

            outputData = OrderedDict({
              'task': taskData,
              'items': itemsData
            })
            print(json.dumps(outputData, indent=2))
            json_data = json.dumps(outputData, indent=2)

            with open(options['output_json_file'], mode='w', encoding='utf8') as output_file:
                self.stdout.write('Creating {0} ... '.format(options['output_json_file']), ending='')
                output_file.write(str(json_data))
                self.stdout.write('OK')

        return

#        system_text = Command._load_text_from_file(, 'utf8')
#        print('Loaded {0} system segments'.format(len(system_text.keys())))

        try:
            pass
            # TODO: add check for ids

        except AssertionError:
            raise CommandError(
              'Segment counts for input files do not match'
            )

        segment_ids = [segment_id for segment_id in source_file.keys()]
        if options['random_seed'] is not None:
            seed(options['random_seed'])
            self.stdout.write(
              'Seeded random number generator with seed={0}'.format(
                options['random_seed'])
            )
        
        if options['randomize']:
            shuffle(segment_ids)
            self.stdout.write('Randomized work items')
        




        _ref = options['refs']
        _bad = options['bad_refs']
        _chk = options['redundant']
        _tgt = options['batch_size'] - (_ref + _bad + _chk)

        # Randomize segment type
        #
        # It can be one of the following:
        # - TGT: system translation output;
        # - REF: reference text;
        # - BAD: bad reference text;
        # - CHK: redundant system translation.
        itemTypes = ['TGT'] * _tgt \
          + ['REF'] * _ref \
          + ['BAD'] * _bad \
          + ['CHK'] * _chk
        
        targetIDs = []
        itemTypeID = 0
        shuffle(itemTypes)
        for segment_id in segment_ids[:options['batch_size']]:
            segment_type = itemTypes[itemTypeID]

            # TODO: this can fail for sequences where CHKs come before TGTs
            if segment_type == 'TGT':
                targetID = basename(options['system_text'])
                targetText = system_text[segment_id]
                targetIDs.append(segment_id)
            
            elif segment_type =='REF':
                targetID = basename(options['reference_file'])
                targetText = reference_file[segment_id]
                
            elif segment_type =='BAD':
                targetID = basename(options['reference_file'])
                targetText = reference_file[segment_id]
                
            elif segment_type =='CHK':
                shuffle(targetIDs)
                segment_id = targetIDs[0]
                targetID = basename(options['system_text'])
                targetText = system_text[segment_id]
            
            assert(targetText is not None)

            obj = OrderedDict()
            obj['sourceID'] = sourceID
            obj['sourceText'] = source_file[segment_id]
            obj['targetID'] = targetID
            obj['targetText'] = targetText
            obj['itemID'] = segment_id
            obj['itemType'] = segment_type

            itemTypeID += 1

            itemsData.append(obj)

        outputData = OrderedDict({
          'task': taskData,
          'items': itemsData
        })
        print(json.dumps(outputData, indent=2))


        self.stdout.write("I would do something now...")
        self.stdout.write(options['source_file'])
        self.stdout.write(options['reference_file'])
        self.stdout.write(str(options['annotations']))
        print(options['random_seed'])

    @staticmethod
    def _load_text_from_file(file_path, encoding='utf8'):
        segment_id = 0
        file_text = OrderedDict()

        with open(file_path, encoding=encoding) as input_file:
            for current_line in input_file:
                segment_id += 1
                file_text[segment_id] = current_line.strip()

        return file_text
