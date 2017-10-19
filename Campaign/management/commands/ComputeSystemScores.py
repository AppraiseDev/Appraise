from collections import defaultdict, OrderedDict
from json import loads
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError

from Campaign.models import Campaign
from EvalData.models import DirectAssessmentTask, DirectAssessmentResult

# pylint: disable=C0111,C0330,E1101
class Command(BaseCommand):
    help = 'Computes system scores over all results'

    def add_arguments(self, parser):
        parser.add_argument(
          'campaign_name', type=str,
          help='Name of the campaign you want to process data for'
        )
        parser.add_argument(
          '--completed-only', action='store_true',
          help='Include completed tasks only in the computation'
        )
        # TODO: add argument to specify batch user

    def handle(self, *args, **options):
        campaign_name = options['campaign_name']
        completed_only = options['completed_only']

        # Identify Campaign instance for given name
        campaign = Campaign.objects.filter(campaignName=campaign_name).first()
        if not campaign:
            _msg = 'Failure to identify campaign {0}'.format(campaign_name)
            self.stdout.write(_msg)
            return

        normalized_scores = OrderedDict()
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
            normalized_scores[normalized_score] = (key, len(value), normalized_score)

        for key in sorted(normalized_scores, reverse=True):
            value = normalized_scores[key]
            print('{0:03.2f} {1}'.format(key, value))

        # Non-segment level average
        #normalized_scores = defaultdict(list)
        #for key, value in system_scores.items():
        #    normalized_score = float(sum([x[1] for x in value]) / (len(value) or 1))
        #    normalized_scores[normalized_score] = (key, len(value), normalized_score)
        #
        #for key in sorted(normalized_scores, reverse=True):
        #    value = normalized_scores[key]
        #    print('{0:03.2f} {1}'.format(key, value))
