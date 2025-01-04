"""
Appraise evaluation framework

See LICENSE for usage details
"""
from datetime import datetime
from os import path

from django.core.files import File
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.core.management.base import CommandError

from Campaign.management.commands.init_campaign import _create_context
from Campaign.management.commands.init_campaign import _init_campaign
from Campaign.management.commands.ProcessCampaignData import _process_campaign_data
from Campaign.management.commands.validatecampaigndata import _validate_campaign_data
from Campaign.models import Campaign
from Campaign.models import CampaignData
from Campaign.models import CampaignTeam
from Campaign.models import Market
from Campaign.models import Metadata
from Campaign.utils import _identify_super_users
from Campaign.utils import _load_campaign_manifest
from Campaign.utils import _process_market_and_metadata
from Dashboard.utils import generate_confirmation_token
from EvalData.management.commands.UpdateEvalDataModels import _update_eval_data_models

# pylint: disable=C0111,C0330,E1101
class Command(BaseCommand):
    help = 'A single command for creating a new campaign based on manifest file'

    def add_arguments(self, parser):
        parser.add_argument(
            'manifest_json',
            metavar='manifest-json',
            type=str,
            help='Path to manifest file in JSON format.',
        )

        # TODO: support adding multiple batches
        parser.add_argument(
            '--batches-json',
            type=str,
            default=[],
            metavar='JSON',
            nargs='+',
            help='List of paths to batches in JSON format.',
        )

        parser.add_argument(
            '--csv-output',
            type=str,
            default=None,
            metavar='CSV',
            help='Path used to create CSV file containing credentials.',
        )

        parser.add_argument(
            '--xlsx-output',
            type=str,
            default=None,
            metavar='XLSX',
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
            help='Generate valid task confirmation tokens needed for integration '
            'with external crowd sourcing apps.',
        )

        parser.add_argument(
            '--max-count',
            type=int,
            default=-1,
            metavar='INTEGER',
            help='Defines maximum number of batches to be processed',
        )

    def handle(self, *args, **options):
        manifest_json = options['manifest_json']
        self.stdout.write('JSON manifest path: {0!r}'.format(manifest_json))

        csv_output = options['csv_output']
        self.stdout.write('CSV output path: {0!r}'.format(csv_output))
        if csv_output and not csv_output.lower().endswith('.csv'):
            raise CommandError(
                'csv_output {0!r} does not point to .csv file'.format(csv_output)
            )

        xlsx_output = options['xlsx_output']
        self.stdout.write('Excel output path: {0!r}'.format(xlsx_output))
        if xlsx_output and not xlsx_output.lower().endswith('.xlsx'):
            raise CommandError(
                'xlsx_output {0!r} does not point to .xlsx file'.format(xlsx_output)
            )

        # Load manifest data, this may raise CommandError
        manifest_data = _load_campaign_manifest(manifest_json)
        context = _create_context(manifest_data, stdout=self.stdout)

        # By default, we only include activated tasks into agenda creation.
        # Compute Boolean flag based on negation of --include-completed state.
        only_activated = not options['include_completed']
        confirmation_tokens = options['task_confirmation_tokens']

        # TODO: run only if the campaign does not exist

        #############################################################
        self.stdout.write('### Running InitCampaign')

        # Initialise campaign based on manifest data
        _init_campaign(
            context,
            csv_output,
            xlsx_output,
            only_activated,
            confirmation_tokens,
            # When run for the first time, do not process campaign agendas,
            # because the campaign does not exist yet
            skip_agendas=True,
            stdout=self.stdout,
        )

        owner = _identify_super_users()[0]

        #############################################################
        self.stdout.write('### Creating a new campaign')

        batches_json = options['batches_json']
        campaign_name = context['CAMPAIGN_NAME']
        campaign_opts = context.get('TASK_OPTIONS', '')
        if batches_json:
            # Get markets and metad data for batches
            markets_and_metadata = _process_market_and_metadata(
                context['ALL_LANGUAGES'],
                owner,
                domain_name=campaign_name,
                corpus_name=campaign_name,
            )
            # A batch needs its own market, so check if each batch has one
            if len(markets_and_metadata) != len(batches_json):
                raise ValueError(
                    'Mismatch of number of markets ({0}) and JSON batches ({1})'.format(
                        len(markets_and_metadata), len(batches_json)
                    )
                )

            campaign_data = []
            for _batches_json, (_market, _meta) in zip(
                batches_json, markets_and_metadata
            ):
                self.stdout.write('- {0!r}'.format(_batches_json))
                campaign_data.append(
                    _upload_batches_json(
                        _batches_json,
                        owner,
                        market=_market,
                        metadata=_meta,
                        stdout=self.stdout,
                    )
                )

            self.stdout.write('Campaign name: {}'.format(campaign_name))
            _campaign = _create_campaign(
                campaign_name, campaign_data, campaign_opts, owner, stdout=self.stdout
            )

        else:  # i.e. batches_json is empty
            _campaign = Campaign.objects.filter(campaignName=campaign_name)
            if _campaign.exists():
                _campaign = _campaign[0]
            else:
                raise CommandError(
                    'Campaign {0!r} does not exist and no JSON file '
                    'with batches provided via --batches-json.'.format(campaign_name)
                )

        #############################################################
        self.stdout.write('### Running validatecampaigndata')

        self.stdout.write('Campaign name: {}'.format(_campaign.campaignName))
        _validate_campaign_data(_campaign, self.stdout)

        #############################################################
        self.stdout.write('### Running ProcessCampaignData')

        _campaign_type = context['TASK_TYPE']
        _max_count = options['max_count']
        if not _campaign.activated:
            _process_campaign_data(_campaign, owner, _campaign_type, _max_count)

        #############################################################
        self.stdout.write('### Running UpdateEvalDataModels')
        _update_eval_data_models(self.stdout)

        #############################################################
        self.stdout.write('### Running init_campaign again')

        _init_campaign(
            context,
            csv_output,
            xlsx_output,
            only_activated,
            confirmation_tokens,
            skip_agendas=False,
            stdout=self.stdout,
        )

        if csv_output or xlsx_output:
            self.stdout.write('Done. Credentials exported to a CSV/XLSX file.')
        else:
            self.stdout.write(
                'Done. Re-run providing --csv-output or --xlsx-output '
                'to export credentials.'
            )


def _upload_batches_json(batches_json, owner, market, metadata, stdout=None):
    """Upload batches and return a CampaignData object."""
    stdout.write('Batch: {}'.format(batches_json))
    stdout.write('  Market: {}'.format(market))
    stdout.write('  Metadata: {}'.format(metadata))

    campaign_data = CampaignData(
        market=market,
        metadata=metadata,
        createdBy=owner,
    )

    _filename = path.basename(batches_json)
    with open(batches_json, 'rb') as _reader:
        _file = ContentFile(_reader.read())
        campaign_data.dataFile.save(_filename, _file)
    campaign_data.save()
    stdout.write('Uploaded file name: {}'.format(campaign_data.dataFile))

    return campaign_data


def _create_campaign(
    campaign_name, campaign_data, campaign_options, owner, stdout=None
):
    """Create a new campaign."""
    # The team is already created in one of the previous steps
    team = CampaignTeam.objects.get(teamName=campaign_name)
    campaign = Campaign(campaignName=campaign_name, createdBy=owner)
    if campaign_options:
        campaign.campaignOptions = campaign_options
    campaign.save()
    campaign.teams.add(team)
    for _campaign_data in campaign_data:
        campaign.batches.add(_campaign_data)
    campaign.save()
    return campaign
