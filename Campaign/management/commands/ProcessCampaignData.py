# pylint: disable=C0103,C0111,C0330,E1101
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError

from Campaign.models import Campaign
from EvalData.models import (
    DirectAssessmentTask,
    DirectAssessmentContextTask,
    MultiModalAssessmentTask,
)

CAMPAIGN_TASK_TYPES = {
    'Direct': DirectAssessmentTask,
    'DocLevelDA': DirectAssessmentContextTask,
    'MultiModal': MultiModalAssessmentTask,
}

class Command(BaseCommand):
    help = 'Validates campaign data batches'

    def add_arguments(self, parser):
        parser.add_argument(
          'campaign_name', type=str,
          help='Name of the campaign you want to process data for'
        )
        _valid_task_types = ', '.join(CAMPAIGN_TASK_TYPES.keys())
        parser.add_argument(
          'campaign_type', type=str,
          help=f'Campaign type: {_valid_task_types}'
        )
        parser.add_argument(
          '--max-count', type=int, default=-1,
          help='Defines maximum number of batches to be processed'
        )
        # TODO: add argument to specify batch user

    def handle(self, *args, **options):
        # Identify Campaign instance for given name.
        try:
            campaign = Campaign.get_campaign_or_raise(
                options['campaign_name'])

        except LookupError as error:
            raise CommandError(error)

        campaign_type = options['campaign_type']
        max_count = options['max_count']

        # Identify batch user who needs to be a superuser
        batch_user = User.objects.filter(is_superuser=True).first()
        if not batch_user:
            _msg = 'Failure to identify batch user'
            self.stdout.write(_msg)
            return

        # Validate campaign type
        if not campaign_type in ('Direct', 'DocLevelDA', 'MultiModal'):
            _msg = 'Bad campaign type {0}'.format(campaign_type)
            self.stdout.write(_msg)
            return

        # TODO: add rollback in case of errors
        for batch_data in campaign.batches.filter(dataValid=True):
            task_cls = CAMPAIGN_TASK_TYPES.get(campaign_type, None)

            if not task_cls:
                _msg = f'Invalid campaign type {campaign_type}'
                raise CommandError(_msg)

            try:
                task_cls.import_from_json(
                    campaign, batch_user, batch_data, max_count
                )

            except Exception as e:
                raise CommandError(e)

            finally:
                batch_data.dataReady = True
                batch_data.activate()
                batch_data.save()

        campaign.activate()
        campaign.save()
