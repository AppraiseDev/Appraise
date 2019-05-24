"""
Appraise
"""
# pylint: disable=C0103,C0111,C0330,E1101
from json import loads
from zipfile import ZipFile, is_zipfile
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError

from Campaign.models import Campaign

class Command(BaseCommand):
    help = 'Validates campaign data batches'

    def add_arguments(self, parser):
        parser.add_argument(
          'campaign_name', type=str,
          help='Name of the campaign you want to process data for'
        )

    def handle(self, *args, **options):
        # Identify Campaign instance for given name.
        try:
            campaign = Campaign.get_campaign_or_raise(
                options['campaign_name'])

        except LookupError as error:
            raise CommandError(error)

        # Find super user
        superusers = User.objects.filter(is_superuser=True)
        if not superusers.exists():
            _msg = 'Failure to identify superuser'
            self.stdout.write(_msg)
            return

        validated_batches = 0
        for batch in campaign.batches.filter(dataValid=False, dataReady=False):
            batch_name = batch.dataFile.name
            batch_file = batch.dataFile

            print(batch_name)

            try:
                # TODO: move validation code to CampaignData class.
                if batch_name.endswith('.zip'):
                    if not is_zipfile(batch_file):
                        _msg = 'Batch {0} not a valid ZIP archive'.format(batch_name)
                        self.stdout.write(_msg)
                        continue

                    batch_zip = ZipFile(batch_file)
                    batch_json_files = [x for x in batch_zip.namelist() if x.endswith('.json')]
                    for batch_json_file in batch_json_files:
                        batch_data = batch_zip.read(batch_json_file).decode('utf-8')
                        loads(batch_data, encoding='utf-8')

                else:
                    loads(str(batch_file.read(), encoding="utf-8"))

                batch.dataValid = True
                batch.save()

                validated_batches += 1

            except Exception as error:
                raise CommandError(error)

        _msg = 'Validated {0} batches'.format(validated_batches)
        self.stdout.write(_msg)
