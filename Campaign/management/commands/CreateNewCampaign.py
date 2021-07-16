"""
Appraise evaluation framework

See LICENSE for usage details
"""
from datetime import datetime

from django.core.management.base import BaseCommand, CommandError

from tablib import Dataset

from Campaign.management.commands.init_campaign import (
    _init_campaign,
    _export_credentials,
)

from Campaign.utils import (
    _create_uniform_task_map,
    _identify_super_users,
    _load_campaign_manifest,
    _process_campaign_agendas,
    _process_campaign_teams,
    _process_market_and_metadata,
    _process_users,
    _validate_language_codes,
    CAMPAIGN_TASK_TYPES,
)

from Dashboard.utils import generate_confirmation_token

# pylint: disable=C0111,C0330,E1101
class Command(BaseCommand):
    help = 'Creates a new campaign based on manifest file'

    def add_arguments(self, parser):
        parser.add_argument(
            'manifest_json',
            metavar='manifest-json',
            type=str,
            help='Path to manifest file in JSON format.',
        )

        parser.add_argument(
            '--csv-output',
            type=str,
            default=None,
            metavar='--csv',
            help='Path used to create CSV file containing credentials.',
        )

        parser.add_argument(
            '--xlsx-output',
            type=str,
            default=None,
            metavar='--xlsx',
            help='Path used to create Excel file containing credentials.',
        )

        parser.add_argument(
            '--include-completed',
            action='store_true',
            default=False,
            help='Include completed tasks in task agenda re-assignment.',
        )

        parser.add_argument(
            '--task-confirmation-tokens',
            action='store_true',
            default=False,
            help='Generate valid task confirmation tokens needed for integration with external crowd sourcing apps.',
        )

    def handle(self, *args, **options):
        manifest_json = options['manifest_json']
        self.stdout.write(
            'JSON manifest path: {0!r}'.format(manifest_json)
        )

        csv_output = options['csv_output']
        self.stdout.write('CSV output path: {0!r}'.format(csv_output))
        if csv_output and not csv_output.lower().endswith('.csv'):
            raise CommandError(
                'csv_output {0!r} does not point to .csv file'.format(
                    csv_output
                )
            )

        xlsx_output = options['xlsx_output']
        self.stdout.write('Excel output path: {0!r}'.format(xlsx_output))
        if xlsx_output and not xlsx_output.lower().endswith('.xlsx'):
            raise CommandError(
                'xlsx_output {0!r} does not point to .xlsx file'.format(
                    xlsx_output
                )
            )

        # Load manifest data, this may raise CommandError
        manifest_data = _load_campaign_manifest(manifest_json)

        # By default, we only include activated tasks into agenda creation.
        # Compute Boolean flag based on negation of --include-completed state.
        only_activated = not options['include_completed']
        confirmation_tokens = options['task_confirmation_tokens']

        # Initialise campaign based on manifest data
        _init_campaign(
            self.stdout,
            manifest_data, csv_output, xlsx_output, only_activated,
            confirmation_tokens,
            # When run for the first time, do not process campaign agendas,
            # because the campaign does not exist yet
            skip_agendas=True
        )



