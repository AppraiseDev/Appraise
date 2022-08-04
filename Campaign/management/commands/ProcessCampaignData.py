# pylint: disable=C0103,C0111,C0330,E1101
from django.core.management.base import BaseCommand
from django.core.management.base import CommandError

from Campaign.models import Campaign
from Campaign.utils import _identify_super_users
from Campaign.utils import CAMPAIGN_TASK_TYPES


class Command(BaseCommand):
    help = 'Validates campaign data batches'

    def add_arguments(self, parser):
        parser.add_argument(
            'campaign_name',
            type=str,
            help='Name of the campaign you want to process data for',
        )
        _valid_task_types = ', '.join(CAMPAIGN_TASK_TYPES.keys())
        parser.add_argument(
            'campaign_type',
            type=str,
            help='Campaign type: {0}'.format(_valid_task_types),
        )
        parser.add_argument(
            '--max-count',
            type=int,
            default=-1,
            help='Defines maximum number of batches to be processed',
        )
        # TODO: add argument to specify batch user

    def handle(self, *args, **options):
        # Identify Campaign instance for given name.
        try:
            campaign = Campaign.get_campaign_or_raise(options['campaign_name'])
        except LookupError as error:
            raise CommandError(error)

        # Find super user
        superusers = _identify_super_users()
        self.stdout.write('Identified superuser: {0}'.format(superusers[0]))
        # Identify batch user who needs to be a superuser
        batch_user = superusers.first()

        campaign_type = options['campaign_type']
        max_count = options['max_count']

        _process_campaign_data(campaign, batch_user, campaign_type, max_count)


def _process_campaign_data(campaign, batch_user, campaign_type, max_count):
    """Process campaign data."""
    # Validate campaign type
    if not campaign_type in CAMPAIGN_TASK_TYPES.keys():
        raise CommandError('Bad campaign type {0}'.format(campaign_type))

    # TODO: add rollback in case of errors
    for batch_data in campaign.batches.filter(dataValid=True):
        # We have already verified that campaign_type is valid
        task_cls = CAMPAIGN_TASK_TYPES.get(campaign_type)

        try:
            task_cls.import_from_json(campaign, batch_user, batch_data, max_count)

        except Exception as e:
            raise CommandError(e)

        finally:
            batch_data.dataReady = True
            batch_data.activate()
            batch_data.save()

    print('Campaign activated')
    campaign.activate()
    campaign.save()
