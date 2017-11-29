from collections import defaultdict, OrderedDict
from json import loads
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError

from Campaign.models import Campaign
from EvalData.models import DirectAssessmentTask, DirectAssessmentResult

# pylint: disable=C0111,C0330,E1101
class Command(BaseCommand):
    help = 'Exports system scores over all results to CSV format'

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

        system_scores = DirectAssessmentResult.get_system_data(campaign.id, extended_csv=True)

        for system_score in system_scores:
            print(','.join([str(x) for x in system_score]))
