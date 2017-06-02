from json import loads
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError

from Campaign.models import Campaign, CampaignData, CampaignTeam
from EvalData.models import Market, Metadata, TextPair, DirectAssessmentTask

# pylint: disable=C0111,C0330,E1101
class Command(BaseCommand):
    help = 'Validates campaign data batches'

    def add_arguments(self, parser):
        parser.add_argument(
          'campaign_name', type=str,
          help='Name of the campaign you want to process data for'
        )
        parser.add_argument(
          '--activate', type=bool, default=False,
          help='Activate tasks after creation'
        )

    def handle(self, *args, **options):
        campaign_name = options['campaign_name']
        activate = options['activate']

        campaign = Campaign.objects.filter(campaignName=campaign_name)

        if not campaign.exists():
            _msg = 'Failure to identify campaign {0}'.format(campaign_name)
            self.stdout.write(_msg)
            return

        else:
            campaign = campaign[0]

        # Find super user
        superusers = User.objects.filter(is_superuser=True)
        if not superusers.exists():
            _msg = 'Failure to identify superuser'
            self.stdout.write(_msg)
            return

        # TODO: add rollback in case of errors
        for batch in campaign.batches.all():
            batch_name = batch.dataFile.name
            batch_file = batch.dataFile
            batch_json = loads(str(batch_file.read(), encoding="utf-8"))

            for batch_task in batch_json:
                print(batch_name, batch_task['task']['batchNo'])

                new_items = []
                for item in batch_task['items']:
                    new_item = TextPair(
                      sourceID=item['sourceID'],
                      sourceText=item['sourceText'],
                      targetID=item['targetID'],
                      targetText=item['targetText'],
                      createdBy=superusers[0],
                      itemID=item['itemID'],
                      itemType=item['itemType']
                    )
                    new_items.append(new_item)

                if not len(new_items) == 100:
                    _msg = 'Expected 100 items for task but found {0}'.format(
                      len(new_items)
                    )
                    self.stdout.write(_msg)
                    continue

                for new_item in new_items:
                    new_item.metadata = batch.metadata
                    new_item.save()

                new_task = DirectAssessmentTask(
                  campaign=campaign,
                  requiredAnnotations=batch_task['task']['requiredAnnotations'],
                  batchNo=batch_task['task']['batchNo'],
                  batchData=batch,
                  createdBy=superusers[0]
                )
                new_task.save()

                for new_item in new_items:
                    new_task.items.add(new_item)

                if activate:
                    new_task.activate()

                new_task.save()

                _msg = 'Success processing batch {0}, task {1}'.format(
                  str(batch), batch_task['task']['batchNo']
                )
                self.stdout.write(_msg)
