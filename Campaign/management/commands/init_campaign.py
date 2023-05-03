"""
Appraise evaluation framework

See LICENSE for usage details
"""
from datetime import datetime

from django.core.management.base import BaseCommand
from django.core.management.base import CommandError
from tablib import Dataset  # type: ignore

from Campaign.utils import _create_linear_task_map
from Campaign.utils import _create_uniform_task_map
from Campaign.utils import _identify_super_users
from Campaign.utils import _load_campaign_manifest
from Campaign.utils import _process_campaign_agendas
from Campaign.utils import _process_campaign_teams
from Campaign.utils import _process_market_and_metadata
from Campaign.utils import _process_users
from Campaign.utils import _validate_language_codes
from Campaign.utils import CAMPAIGN_TASK_TYPES
from Dashboard.utils import generate_confirmation_token

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
            help='Include completed tasks in task agenda re-assignment.',
        )

        parser.add_argument(
            '--task-confirmation-tokens',
            action='store_true',
            default=False,
            help='Generate valid task confirmation tokens needed for '
            'integration with external crowd sourcing apps.',
        )

    def handle(self, *args, **options):
        manifest_json = options.get('manifest_json')
        self.stdout.write('JSON manifest path: {0!r}'.format(manifest_json))

        csv_output = options.get('csv_output')
        self.stdout.write('CSV output path: {0!r}'.format(csv_output))
        if csv_output and not csv_output.lower().endswith('.csv'):
            raise CommandError(
                'csv_output {0!r} does not point to .csv file'.format(csv_output)
            )

        xlsx_output = options.get('xlsx_output')
        self.stdout.write('Excel output path: {0!r}'.format(xlsx_output))
        if xlsx_output and not xlsx_output.lower().endswith('.xlsx'):
            raise CommandError(
                'xlsx_output {0!r} does not point to .xlsx file'.format(xlsx_output)
            )

        # Load manifest data, this may raise CommandError
        manifest_data = _load_campaign_manifest(manifest_json)
        # Read context from manifest data
        context = _create_context(manifest_data, stdout=self.stdout)

        # By default, we only include activated tasks into agenda creation.
        # Compute Boolean flag based on negation of --include-completed state.
        only_activated = not options['include_completed']
        confirmation_tokens = options.get('task_confirmation_tokens', False)

        # Initialise campaign based on manifest data
        _init_campaign(
            context,
            csv_output,
            xlsx_output,
            only_activated,
            confirmation_tokens,
            stdout=self.stdout,
        )


def _init_campaign(
    context,
    csv_output,
    xlsx_output,
    only_activated=True,
    confirmation_tokens=False,
    skip_agendas=False,
    stdout=None,
):
    """Initialises campaign based on manifest data.

    Parameters:
    - context:dict[str]->any dictionary containing manifest data;
    - csv_output:str path to CSV output file, or None;
    - xlsx_output:str path to Excel output file, or None;
    - only_activated:bool only include activated tasks for agenda creation;
    - confirmation_tokens:bool export valid task confirmation tokens.
    """
    ALL_LANGUAGES = context['ALL_LANGUAGES']
    print('All languages:', ALL_LANGUAGES)

    # Find super user
    superusers = _identify_super_users()
    if stdout is not None:
        stdout.write('Identified superuser: {0}'.format(superusers[0]))

    # Process Market and Metadata instances for all language pairs
    _process_market_and_metadata(
        ALL_LANGUAGES,
        superusers[0],
        domain_name=context['CAMPAIGN_NAME'],
        corpus_name=context['CAMPAIGN_NAME'],
    )
    if stdout is not None:
        stdout.write('Processed Market/Metadata instances')

    # Create User accounts for all language pairs. We collect the
    # resulting user credentials for later print out/CSV export.
    credentials = _process_users(ALL_LANGUAGES, context)
    if stdout is not None:
        stdout.write('Processed User instances')

    # Print credentials to screen.
    for username, secret in credentials.items():
        print(username, secret)

    # Generate Dataset with user credentials and SSO URLs
    export_data = Dataset()
    if confirmation_tokens:
        export_data.headers = ('Username', 'Password', 'URL', 'ConfirmationToken')
    else:
        export_data.headers = ('Username', 'Password', 'URL')
    export_data.title = datetime.strftime(datetime.now(), '%Y%m%d')

    base_url = context['CAMPAIGN_URL']
    for _user, _password in credentials.items():
        _url = '{0}{1}/{2}/'.format(base_url, _user, _password)
        if confirmation_tokens:
            _token = generate_confirmation_token(_user, run_qc=False)
            export_data.append((_user, _password, _url, _token))
        else:
            export_data.append((_user, _password, _url))

    # Export credentials to CSV or Excel files, if specified
    _export_credentials(export_data, csv_output, xlsx_output, stdout=stdout)

    # Add User instances as CampaignTeam members
    _process_campaign_teams(ALL_LANGUAGES, superusers[0], context)
    if stdout is not None:
        stdout.write('Processed CampaignTeam members')

    if not skip_agendas:
        # Process TaskAgenda instances for current campaign
        _process_campaign_agendas(
            credentials.keys(), context, only_activated=only_activated
        )
    else:
        if stdout is not None:
            stdout.write('Processing campaign agendas was not requested')

    return context


def _export_credentials(export_data, csv_output, xlsx_output, stdout=None):
    """Export credentials to screen, CSV and Excel files.

    Parameters:
    - export_data:Dataset contains triples or 4-tuples (username,
      password, url, [token]);
    - csv_output:str path to CSV output file, or None;
    - xlsx_output:str path to Excel output file, or None.
    """

    # Write credentials to CSV file if specified.
    if csv_output:
        with open(csv_output, mode='w', newline='') as out_file:
            out_file.write(export_data.export('csv'))

        if stdout is not None:
            stdout.write('Exported CSV file: {0!r}'.format(csv_output))

    # Write credentials to Excel file if specified.
    if xlsx_output:
        with open(xlsx_output, mode='wb') as out_file:
            out_file.write(export_data.export('xlsx'))

        if stdout is not None:
            stdout.write('Exported Excel file: {0!r}'.format(xlsx_output))


def _create_context(manifest_data, stdout=None):
    """Create context from manifest JSON.

    Parameters:
    - manifest_data:dict[str]->any dictionary containing manifest data;
    """
    GENERATORS = {
        'uniform': _create_uniform_task_map,
        'linear': _create_linear_task_map,
    }
    ALL_LANGUAGES = []
    ALL_LANGUAGE_CODES = set()
    TASKS_TO_ANNOTATORS = {}
    for pair_data in manifest_data['TASKS_TO_ANNOTATORS']:
        (
            source_code,
            target_code,
            mode,
            num_annotators,
            num_tasks,
        ) = pair_data

        # Validation needs access to full language codes,
        # including any script specification
        ALL_LANGUAGE_CODES.add(source_code)
        ALL_LANGUAGE_CODES.add(target_code)

        ALL_LANGUAGES.append((source_code, target_code))

        generator = GENERATORS[mode]
        TASKS_TO_ANNOTATORS[(source_code, target_code)] = generator(
            num_annotators,
            num_tasks,
            manifest_data['REDUNDANCY'],
        )

    _validate_language_codes(ALL_LANGUAGE_CODES)

    # DirectAssessmentTask is the default task for backward compatibility
    if 'TASK_TYPE' not in manifest_data:
        TASK_TYPE = 'Direct'
        if stdout is not None:
            stdout.write(
                'No task type found in the manifest file, assuming it is "Direct". '
                'If this is incorrect, define "TASK_TYPE" in the manifest file.'
            )
    else:
        TASK_TYPE = manifest_data.get('TASK_TYPE', 'Direct')

    # Raise an exception if an unrecognized task type is provided
    if TASK_TYPE not in CAMPAIGN_TASK_TYPES:
        _msg = 'Unrecognized TASK_TYPE \'{0}\'. Supported tasks are: {1}'.format(
            TASK_TYPE, ', '.join(CAMPAIGN_TASK_TYPES.keys())
        )
        raise ValueError(_msg)

    context = {
        'ALL_LANGUAGES': ALL_LANGUAGES,
        'CAMPAIGN_KEY': manifest_data['CAMPAIGN_KEY'],
        'CAMPAIGN_NAME': manifest_data['CAMPAIGN_NAME'],
        'CAMPAIGN_NO': manifest_data['CAMPAIGN_NO'],
        'CAMPAIGN_URL': manifest_data['CAMPAIGN_URL'],
        'REDUNDANCY': manifest_data['REDUNDANCY'],
        'TASKS_TO_ANNOTATORS': TASKS_TO_ANNOTATORS,
        'TASK_TYPE': TASK_TYPE,
        'TASK_OPTIONS': manifest_data.get('TASK_OPTIONS', ''),
    }

    return context
