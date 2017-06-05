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
        # TODO: add argument to specify batch user

    def handle(self, *args, **options):
        campaign_name = options['campaign_name']

        # Identify Campaign instance for given name
        campaign = Campaign.objects.filter(campaignName=campaign_name).first()
        if not campaign:
            _msg = 'Failure to identify campaign {0}'.format(campaign_name)
            self.stdout.write(_msg)
            return

        normalized_scores = OrderedDict()
        for task in DirectAssessmentTask.objects.filter(campaign=campaign):
            system_scores = DirectAssessmentResult.get_system_scores()

            for key, value in system_scores.items():
                normalized_score = float(sum(value) / len(value))
                normalized_scores[normalized_score] = (key, len(value), normalized_score)

        for key in sorted(normalized_scores, reverse=True):
            value = normalized_scores[key]
            print('{0:03.2f} {1}'.format(key, value))
