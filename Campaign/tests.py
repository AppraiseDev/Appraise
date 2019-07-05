"""
Appraise evaluation framework

See LICENSE for usage details
"""
from pathlib import Path

from django.contrib.auth.models import User
from django.core.management.base import CommandError
from django.test import TestCase


class TestInitCampaign(TestCase):
    """Tests init_campaign management command."""

    def setUp(self):
        User.objects.create(username="admin", is_superuser=True)

    def test_creates_correct_csv_for_sample_manifests(self):
        """Verifies correct CSV creation for sample manifests."""
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
            }

            expected_msg = (
                'Campaign {0!r} does not exist. No task agendas '
                'have been assigned.'.format(campaign_name)
            )

            with self.assertRaisesMessage(CommandError, expected_msg):
                cmd.handle(**options)

            self.assertEqual(out_path.read_bytes(), csv_path.read_bytes())

            # Clean up
            out_path.unlink()
