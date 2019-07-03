"""
Appraise evaluation framework

See LICENSE for usage details
"""
from django.core.management.base import BaseCommand, CommandError

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
            'manifest-json',
            metavar='manifest_json',
            type=str,
            help='Path to manifest file in JSON format',
        )

        parser.add_argument(
            '--csv-output',
            type=str,
            default=None,
            metavar='--csv',
            help='Path used to create CSV file containing credentials.',
        )

    def handle(self, *args, **options):
        manifest_json = options['manifest_json']
        self.stdout.write(
            'JSON manifest path: {0!r}'.format(manifest_json)
        )
        # Load manifest data, this may raise CommandError
        manifest_data = _load_campaign_manifest(manifest_json)

        # TODO: refactor into _create_context()
        GENERATORS = {'uniform': _create_uniform_task_map}
        ALL_LANGUAGES = []
        ALL_LANGUAGE_CODES = set()
        TASKS_TO_ANNOTATORS = {}
        for pair_data in manifest_data['TASKS_TO_ANNOTATORS']:
            source_code, target_code, mode, annotators, tasks = pair_data

            ALL_LANGUAGES.append((source_code, target_code))
            ALL_LANGUAGE_CODES.add(source_code)
            ALL_LANGUAGE_CODES.add(target_code)

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

        csv_output = options['csv_output']
        self.stdout.write('CSV output path: {0!r}'.format(csv_output))
        if csv_output and not csv_output.lower().endswith('.csv'):
            raise CommandError(
                'csv_output {0!r} does not point to .csv file'.format(
                    csv_output
                )
            )

        # Find super user
        superusers = _identify_super_users()
        self.stdout.write(
            'Identified superuser: {0}'.format(superusers[0])
        )

        # Process Market and Metadata instances for all language pairs
        _process_market_and_metadata(
            ALL_LANGUAGES,
            superusers[0],
            domain_name='AppenFY20',
            corpus_name='AppenFY20',
        )
        self.stdout.write('Processed Market/Metadata instances')

        # Create User accounts for all language pairs. We collect the
        # resulting user credentials for later print out/CSV export.
        credentials = _process_users(ALL_LANGUAGES, CONTEXT)
        self.stdout.write('Processed User instances')

        # Print credentials to screen.
        for username, secret in credentials.items():
            print(username, secret)

        # Write credentials to CSV file if specified.
        if csv_output:
            base_url = manifest_data['CAMPAIGN_URL']
            csv_lines = [','.join(('Username', 'Password', 'URL')) + '\n']
            for _user, _password in credentials.items():
                _url = '{0}{1}/{2}/'.format(base_url, _user, _password)
                csv_lines.append(','.join((_user, _password, _url)) + '\n')
            with open(csv_output, mode='w') as out_file:
                out_file.writelines(csv_lines)

        # Add User instances as CampaignTeam members
        _process_campaign_teams(ALL_LANGUAGES, superusers[0], CONTEXT)
        self.stdout.write('Processed CampaignTeam members')

        # Process TaskAgenda instances for current campaign
        _process_campaign_agendas(CONTEXT)
