"""
Appraise evaluation framework

See LICENSE for usage details
"""
from datetime import datetime

from django.core.management.base import BaseCommand, CommandError

from tablib import Dataset

from Campaign.utils import (
    _create_uniform_task_map,
    _identify_super_users,
    _load_campaign_manifest,
    _process_campaign_agendas,
    _process_campaign_teams,
    _process_market_and_metadata,
    _process_users,
    _validate_language_codes,
)

# pylint: disable=C0111,C0330,E1101
class Command(BaseCommand):
    help = 'Initialises campaign based on manifest file'

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
            help='Include completed tasks in task agenda re-assignment',
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

        # Initialise campaign based on manifest data
        self.init_campaign(
            manifest_data, csv_output, xlsx_output, only_activated
        )

    def init_campaign(
        self, manifest_data, csv_output, xlsx_output, only_activated=True
    ):
        '''Initialises campaign based on manifest data.

        Parameters:
        - manifest_data:dict[str]->any dictionary containing manifest data;
        - csv_output:str path to CSV output file, or None;
        - xlsx_output:str path to Excel output file, or None;
        - only_activated:bool only include activated tasks for agenda creation.
        '''

        # TODO: refactor into _create_context()
        GENERATORS = {'uniform': _create_uniform_task_map}
        ALL_LANGUAGES = []
        ALL_LANGUAGE_CODES = set()
        TASKS_TO_ANNOTATORS = {}
        for pair_data in manifest_data['TASKS_TO_ANNOTATORS']:
            source_code, target_code, mode, annotators, tasks = pair_data

            # Validation needs access to full language codes,
            # including any script specification
            ALL_LANGUAGE_CODES.add(source_code)
            ALL_LANGUAGE_CODES.add(target_code)

            ALL_LANGUAGES.append((source_code, target_code))

            generator = GENERATORS[mode]
            TASKS_TO_ANNOTATORS[(source_code, target_code)] = generator(
                annotators, tasks, manifest_data['REDUNDANCY']
            )

        _validate_language_codes(ALL_LANGUAGE_CODES)

        CONTEXT = {
            'CAMPAIGN_KEY': manifest_data['CAMPAIGN_KEY'],
            'CAMPAIGN_NAME': manifest_data['CAMPAIGN_NAME'],
            'CAMPAIGN_NO': manifest_data['CAMPAIGN_NO'],
            'CAMPAIGN_URL': manifest_data['CAMPAIGN_URL'],
            'REDUNDANCY': manifest_data['REDUNDANCY'],
            'TASKS_TO_ANNOTATORS': TASKS_TO_ANNOTATORS,
        }
        # END refactor

        # Find super user
        superusers = _identify_super_users()
        self.stdout.write(
            'Identified superuser: {0}'.format(superusers[0])
        )

        # Process Market and Metadata instances for all language pairs
        _process_market_and_metadata(
            ALL_LANGUAGES,
            superusers[0],
            domain_name=manifest_data['CAMPAIGN_NAME'],
            corpus_name=manifest_data['CAMPAIGN_NAME'],
        )
        self.stdout.write('Processed Market/Metadata instances')

        # Create User accounts for all language pairs. We collect the
        # resulting user credentials for later print out/CSV export.
        credentials = _process_users(ALL_LANGUAGES, CONTEXT)
        self.stdout.write('Processed User instances')

        # Print credentials to screen.
        for username, secret in credentials.items():
            print(username, secret)

        # Generate Dataset with user credentials and SSO URLs
        export_data = Dataset()
        export_data.headers = ('Username', 'Password', 'URL')
        export_data.title = datetime.strftime(datetime.now(), '%Y%m%d')

        base_url = manifest_data['CAMPAIGN_URL']
        for _user, _password in credentials.items():
            _url = '{0}{1}/{2}/'.format(base_url, _user, _password)
            export_data.append((_user, _password, _url))

        # Export credentials to CSV or Excel files, if specified
        self.export_credentials(export_data, csv_output, xlsx_output)

        # Add User instances as CampaignTeam members
        _process_campaign_teams(ALL_LANGUAGES, superusers[0], CONTEXT)
        self.stdout.write('Processed CampaignTeam members')

        # Process TaskAgenda instances for current campaign
        _process_campaign_agendas(
            credentials.keys(), CONTEXT, only_activated=only_activated
        )

    def export_credentials(self, export_data, csv_output, xlsx_output):
        '''Export credentials to screen, CSV and Excel files.

        Parameters:
        - export_data:Dataset contains triples (username, password, url);
        - csv_output:str path to CSV output file, or None;
        - xlsx_output:str path to Excel output file, or None.
        '''

        # Write credentials to CSV file if specified.
        if csv_output:
            with open(csv_output, mode='w', newline='') as out_file:
                out_file.write(export_data.export('csv'))

            self.stdout.write(
                'Exported CSV file: {0!r}'.format(csv_output)
            )

        # Write credentials to Excel file if specified.
        if xlsx_output:
            with open(xlsx_output, mode='wb') as out_file:
                out_file.write(export_data.export('xlsx'))

            self.stdout.write(
                'Exported Excel file: {0!r}'.format(xlsx_output)
            )
