from django.core.management.base import BaseCommand, CommandError

from Campaign.models import Campaign
from EvalData.models import (
    DirectAssessmentResult, DirectAssessmentTask,
    DirectAssessmentContextResult, DirectAssessmentContextTask,
    MultiModalAssessmentResult, MultiModalAssessmentTask,
)

CAMPAIGN_TASK_TYPES = (
    (DirectAssessmentTask, DirectAssessmentResult),
    (DirectAssessmentContextTask, DirectAssessmentContextResult),
    (MultiModalAssessmentTask, MultiModalAssessmentResult),
)

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
            _msg = f'Failure to identify campaign {campaign_name}'
            raise CommandError(_msg)

        system_scores = []
        for task_cls, result_cls in CAMPAIGN_TASK_TYPES:
            qs_name = task_cls.__name__.lower()
            qs_attr = f'evaldata_{qs_name}_campaign'
            qs_obj = getattr(campaign, qs_attr, None)

            if completed_only:
                qs_obj = qs_obj.filter(completed=True)

            if qs_obj and qs_obj.exists():
                _scores = result_cls.get_system_data(
                    campaign.id, extended_csv=True)
                system_scores.extend(_scores)

        for system_score in system_scores:
            print(','.join([str(x) for x in system_score]))
