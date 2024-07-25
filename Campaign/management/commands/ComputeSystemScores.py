from collections import defaultdict
from collections import OrderedDict
from json import loads

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.core.management.base import CommandError

from Campaign.models import Campaign
from EvalData.models import DirectAssessmentResult
from EvalData.models import DirectAssessmentTask

# pylint: disable=C0111,C0330,E1101
class Command(BaseCommand):
    help = 'Computes system scores over all results'

    def add_arguments(self, parser):
        parser.add_argument(
            'campaign_name',
            type=str,
            help='Name of the campaign you want to process data for',
        )
        parser.add_argument(
            '--completed-only',
            action='store_true',
            help='Include completed tasks only in the computation',
        )
        parser.add_argument(
            '--csv-file',
            type=str,
            help='CSV file containing annotation data',
        )
        parser.add_argument(
            '--exclude-ids',
            type=str,
            help='User IDs which should be ignored',
        )
        # TODO: add argument to specify batch user

    def handle(self, *args, **options):
        campaign_name = options['campaign_name']
        completed_only = options['completed_only']
        csv_file = options['csv_file']
        exclude_ids = (
            (x.lower() for x in options['exclude_ids'].split(','))
            if options['exclude_ids']
            else ()
        )

        normalized_scores = OrderedDict()
        if csv_file:
            _msg = 'Processing annotations in file {0}\n\n'.format(csv_file)
            self.stdout.write(_msg)

            # Need to load data from CSV file and bring into same
            # format as would have been produced by the call to
            # get_system_scores().
            #
            # CSV has this format
            # zhoeng0802,GOOG_WMT2009_Test.chs-enu.txt,678,CHK,zho,eng,76,1511470503.271,1511470509.224
            system_scores = defaultdict(list)

            import csv
            from collections import namedtuple

            AnnotationResult = namedtuple(
                'AnnotationResult',
                (
                    'user_id',
                    'system_id',
                    'segment_id',
                    'type_id',
                    'source_language',
                    'target_language',
                    'score',
                ),
            )

            with open(csv_file) as input_file:
                csv_reader = csv.reader(input_file)
                for csv_line in csv_reader:
                    # This may contain more than seven fields -- ignore those
                    csv_data = AnnotationResult._make(csv_line[:7])

                    if csv_data.user_id.lower() in exclude_ids:
                        continue

                    _key = '{0}-{1}-{2}'.format(
                        csv_data.source_language,
                        csv_data.target_language,
                        csv_data.system_id,
                    )

                    if csv_data.type_id.upper() not in ('TGT', 'CHK'):
                        continue

                    system_scores[_key].append(
                        (csv_data.segment_id, int(csv_data.score))
                    )

        else:
            # Identify Campaign instance for given name
            campaign = Campaign.objects.filter(campaignName=campaign_name).first()
            if not campaign:
                _msg = 'Failure to identify campaign {0}'.format(campaign_name)
                self.stdout.write(_msg)
                return

            system_scores = DirectAssessmentResult.get_system_scores(campaign.id)

        # TODO: this should consider the chosen campaign, otherwise
        #   we will show systems across all possible campaigns...
        #
        # This requires us to identify results which belong to the
        # current campaign. Depending on settings for --completed-only
        # we should also constrain this to fully completed tasks.
        #
        # The current implementation of get_system_scores() is not
        # sufficiently prepared for these use cases --> replace it!

        for key, value in system_scores.items():
            scores_by_segment = defaultdict(list)
            for segment_id, score in value:
                scores_by_segment[segment_id].append(score)

            averaged_scores = []
            for segment_id, scores in scores_by_segment.items():
                averaged_score = sum(scores) / float(len(scores) or 1)
                averaged_scores.append(averaged_score)

            normalized_score = float(sum(averaged_scores) / len(averaged_scores) or 1)
            normalized_scores[normalized_score] = (
                key,
                len(value),
                normalized_score,
            )

        for key in sorted(normalized_scores, reverse=True):
            value = normalized_scores[key]
            print('{0:03.2f} {1}'.format(key, value))

        print('\nExcluded IDs: {0}\n'.format(', '.join(exclude_ids)))

        # Non-segment level average
        # normalized_scores = defaultdict(list)
        # for key, value in system_scores.items():
        #    normalized_score = float(sum([x[1] for x in value]) / (len(value) or 1))
        #    normalized_scores[normalized_score] = (key, len(value), normalized_score)
        #
        # for key in sorted(normalized_scores, reverse=True):
        #    value = normalized_scores[key]
        #    print('{0:03.2f} {1}'.format(key, value))
