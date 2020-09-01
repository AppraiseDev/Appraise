# pylint: disable=C0103,C0111,C0330,E1101
from django.core.management.base import BaseCommand, CommandError

from Campaign.models import Campaign
from EvalData.models import (
    DirectAssessmentResult,
    DirectAssessmentTask,
    DirectAssessmentContextResult,
    DirectAssessmentContextTask,
    MultiModalAssessmentResult,
    MultiModalAssessmentTask,
    PairwiseAssessmentResult,
    PairwiseAssessmentTask,
)

CAMPAIGN_TASK_TYPES = (
    (DirectAssessmentTask, DirectAssessmentResult),
    (DirectAssessmentContextTask, DirectAssessmentContextResult),
    (MultiModalAssessmentTask, MultiModalAssessmentResult),
    (PairwiseAssessmentTask, PairwiseAssessmentResult),
)


class Command(BaseCommand):
    help = 'Exports system scores over all results to CSV format'

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
        # TODO: add argument to specify batch user

    def handle(self, *args, **options):
        # Identify Campaign instance for given name.
        try:
            campaign = Campaign.get_campaign_or_raise(
                options['campaign_name']
            )

        except LookupError as error:
            raise CommandError(error)

        system_scores = []
        for task_cls, result_cls in CAMPAIGN_TASK_TYPES:
            qs_name = task_cls.__name__.lower()
            qs_attr = 'evaldata_{0}_campaign'.format(qs_name)
            qs_obj = getattr(campaign, qs_attr, None)

            # Constrain to only completed tasks, if requested.
            if options['completed_only']:
                qs_obj = qs_obj.filter(completed=True)

            if qs_obj and qs_obj.exists():
                _scores = result_cls.get_system_data(
                    campaign.id, extended_csv=True
                )
                system_scores.extend(_scores)

        for system_score in system_scores:
            print(','.join([str(x) for x in system_score]))
