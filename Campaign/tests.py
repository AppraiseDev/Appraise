"""
Appraise evaluation framework

See LICENSE for usage details
"""
from pathlib import Path

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.files.base import File
from django.core.management.base import CommandError
from django.test import TestCase

from Campaign.models import _validate_package_file
from Campaign.models import Campaign


class TestInitCampaign(TestCase):
    '''Tests init_campaign management command.'''

    def setUp(self):
        User.objects.create(username="admin", is_superuser=True)

    def test_creates_correct_csv_for_sample_manifests(self):
        '''Verifies correct CSV creation for sample manifests.'''
        from Campaign.management.commands.init_campaign import Command

        test_data = (
            (
                'HumanEvalFY2001',
                'HumanEvalFY2001_Manifest.json',
                'HumanEvalFY2001_Accounts_Control.csv',
            ),
            (
                'HumanEvalFY2002',
                'HumanEvalFY2002_Manifest.json',
                'HumanEvalFY2002_Accounts_Control.csv',
            ),
        )

        cmd = Command()
        for test_item in test_data:
            campaign_name, json_file, csv_file = test_item

            # Run init_campaign with this JSON file
            json_path = 'Campaign/testdata' / Path(json_file)

            # Write output to this CSV file
            out_file = json_file.replace('.json', '_Output.csv')
            out_path = 'Campaign/testdata' / Path(out_file)

            # Compare output against this reference file
            csv_path = 'Campaign/testdata' / Path(csv_file)

            # Remove output CSV data if it exists
            if out_path.exists():
                out_path.unlink()

            options = {
                'manifest_json': str(json_path),
                'csv_output': str(out_path),
                'xlsx_output': None,  # Defaults to None
                'include_completed': False,  # Defaults to False
            }

            expected_msg = (
                'Campaign {0!r} does not exist. No task agendas '
                'have been assigned.'.format(campaign_name)
            )

            with self.assertRaisesMessage(CommandError, expected_msg):
                cmd.handle(**options)

            self.assertEqual(out_path.read_text(), csv_path.read_text())

            # Clean up
            out_path.unlink()

    def test_validates_good_package_file(self):
        '''Verifies that good package file passes validation.'''
        package_file = Path('Campaign/testdata/FY2002/FY2002.zip')

        campaign = Campaign()
        campaign.campaignName = 'SomeCampaignName'
        campaign.packageFile = File(package_file.open(mode='rb'))

        self.assertTrue(_validate_package_file(campaign.packageFile))

    def test_invalidates_bad_package_files(self):
        '''Verifies that bad package files raise ValidationError.'''
        package_paths = (
            (
                'BadCode/BadCode.zip',
                "manifest.json key 'TASKS_TO_ANNOTATORS' list item has "
                "invalid language codes, check ['eng', 'abc', 'uniform', "
                "18, 36]",
            ),
            (
                'BadContent/BadContent.zip',
                "manifest.json should contain 'CAMPAIGN_KEY' key",
            ),
            (
                'BadJSONType/BadJSONType.zip',
                'manifest.json should contain single object',
            ),
            (
                'BadTaskMap/BadTaskMap.zip',
                "manifest.json key 'TASKS_TO_ANNOTATORS' list item has "
                "bad task map (17 * 2 * 1 != 36), check ['eng', 'trk', "
                "'uniform', 17, 36]",
            ),
            (
                'BadTaskMapRedundancy/BadTaskMapRedundancy.zip',
                "manifest.json key 'TASKS_TO_ANNOTATORS' list item has "
                "bad task map (18 * 2 * 2 != 36), check ['trk', 'eng', "
                "'uniform', 18, 36]",
            ),
            (
                'BadTypeNo/BadTypeNo.zip',
                "manifest.json key 'CAMPAIGN_NO' should be number (int) "
                "type, is 'Not a number (int) value...'",
            ),
            (
                'BadTypeTasksToAnnotators/BadTypeTasksToAnnotators.zip',
                "manifest.json key 'TASKS_TO_ANNOTATORS' should have list "
                'type, is 123',
            ),
            (
                'BadTypeTasksToAnnotatorsItem/BadTypeTasksToAnnotators' 'Item.zip',
                "manifest.json key 'TASKS_TO_ANNOTATORS' list item should "
                "have <str, str, str, int, int> signature, is ['trk', 123, "
                "'uniform', 18, 36]",
            ),
            (
                'BadTypeURL/BadTypeURL.zip',
                "manifest.json key 'CAMPAIGN_URL' should be string type, " 'is 123',
            ),
            (
                'ValidManifest/ValidManifest.zip',
                "Invalid package file 'ValidManifest.zip' -- expected at "
                'least one batch JSON archive file',
            ),
            (
                'ValidManifestNotEnoughBatches/ValidManifestNotEnough' 'Batches.zip',
                "Invalid package file 'ValidManifestNotEnoughBatches.zip' -- "
                'wrong number of batches (1 != 9)',
            ),
        )

        for package_path, expected_msg in package_paths:
            package_file = 'Campaign/testdata' / Path(package_path)

            campaign = Campaign()
            campaign.campaignName = 'SomeCampaignName'
            campaign.packageFile = File(package_file.open(mode='rb'))

            with self.assertRaisesMessage(ValidationError, expected_msg):
                _validate_package_file(campaign.packageFile)
