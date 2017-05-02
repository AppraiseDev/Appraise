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
          'source_text', type=str,
          help='Path to source text file'
        )
        parser.add_argument(
          'reference_text', type=str,
          help='Path to reference text file'
        )
        parser.add_argument(
          'system_text', type=str,
          help='Path to system text file'
        )
        parser.add_argument(
          'json_file', type=str,
          help='Path to JSON output file'
        )
        parser.add_argument(
          '--ids-file', type=str, # required=False,
          help='Path to ids file'
        )
        parser.add_argument(
          '--annotations', type=int, default=1,
          help='Number of required annotations per work item'
        )
        parser.add_argument(
          '--redundant', type=int, default=0, # required=False,
          help='Number of redundant items'
        )
        parser.add_argument(
          '--refs', type=int, default=0, # required=False,
          help='Number of reference items'
        )
        parser.add_argument(
          '--bad-refs', type=int, default=0, # required=False,
          help='Number of bad reference items'
        )
        parser.add_argument(
          '--random-seed', type=int, # required=False,
          help='Random generator seed value'
        )
        parser.add_argument(
          '--randomize', required=False, action='store_true',
          help='Randomize extracted work items'
        )
        # TODO: add optional parameters to set source, reference and system IDs

        # TODO: add exclude argument which prevents creation of redundant data?

    def handle(self, *args, **options):
        # Initialize random number generator
        # Extract batch size number of pairs, randomizing order if requested
        # Serialize pairs into JSON format
        # Write out JSON output file

        # TODO: implement support for ids file
        if options['ids_file'] is not None:
            print("WOOHOO")

        # TODO: add parameter to set encoding
        # TODO: need to use OrderedDict to preserve segment IDs' order!
        source_text = Command._load_text_from_file(options['source_text'], 'utf8')
        print('Loaded {0} source segments'.format(len(source_text.keys())))

        reference_text = Command._load_text_from_file(options['reference_text'], 'utf8')
        print('Loaded {0} reference segments'.format(len(reference_text.keys())))

        system_text = Command._load_text_from_file(options['system_text'], 'utf8')
        print('Loaded {0} system segments'.format(len(system_text.keys())))

        try:
            assert(
                 len(source_text.keys())
              == len(reference_text.keys())
              == len(system_text.keys())
            )

            # TODO: add check for ids

        except AssertionError:
            raise CommandError(
              'Segment counts for input files do not match'
            )

        segment_ids = [segment_id for segment_id in source_text.keys()]
        if options['random_seed'] is not None:
            seed(options['random_seed'])
            self.stdout.write(
              'Seeded random number generator with seed={0}'.format(
                options['random_seed'])
            )
        
        if options['randomize']:
            shuffle(segment_ids)
            self.stdout.write('Randomized work items')
        
        sourceID = basename(options['source_text'])

        taskData = OrderedDict({
          'batchSize': options['batch_size'],
          'sourceLanguage': options['source_language'],
          'targetLanguage': options['target_language'],
          'requiredAnnotations': options['annotations'],
          'randomized': options['randomize'],
          'randomSeed': options['random_seed']
        })
        itemsData = []

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
                targetID = basename(options['reference_text'])
                targetText = reference_text[segment_id]
                
            elif segment_type =='BAD':
                targetID = basename(options['reference_text'])
                targetText = reference_text[segment_id]
                
            elif segment_type =='CHK':
                shuffle(targetIDs)
                segment_id = targetIDs[0]
                targetID = basename(options['system_text'])
                targetText = system_text[segment_id]
            
            assert(targetText is not None)

            obj = OrderedDict()
            obj['sourceID'] = sourceID
            obj['sourceText'] = source_text[segment_id]
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
        self.stdout.write(options['source_text'])
        self.stdout.write(options['reference_text'])
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
