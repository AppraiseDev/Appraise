# pylint: disable=C0103,C0111,C0330,E1101
"""
Django management command to export system scores to CSV format.

This command supports exporting scores from either:
1. Active user accounts (default behavior)
2. Reset accounts only (shadow users created during task agenda resets)

The --reset-accounts-only option allows you to export scores from previous
annotation rounds before task agendas were reset, enabling comparison
between different annotation phases.
"""
import csv
import sys
from re import compile as re_compile

from django.core.management.base import BaseCommand
from django.core.management.base import CommandError
from django.contrib.auth.models import User

from Campaign.models import Campaign
from EvalData.models import TASK_DEFINITIONS

CAMPAIGN_TASK_PAIRS = {(tup[1], tup[2]) for tup in TASK_DEFINITIONS}


def get_shadow_users():
    """
    Returns a list of shadow users (inactive users created during task agenda resets).
    Shadow users follow the pattern: {original_username}-{hex_number}
    """
    shadow_pattern = re_compile(r'^[^-]+-[0-9a-f]{2}$')
    all_users = User.objects.filter(is_active=False)
    shadow_users = [user for user in all_users if shadow_pattern.match(user.username)]
    return shadow_users


def validate_reset_accounts(command_instance):
    """
    Validates that shadow users exist for reset accounts export.
    Returns shadow users list or None if validation fails.
    """
    shadow_users = get_shadow_users()
    if not shadow_users:
        command_instance.stderr.write(
            '# No reset accounts (shadow users) found. '
            'This means no task agendas have been reset yet.'
        )
        return None

    shadow_usernames = [user.username for user in shadow_users]
    command_instance.stderr.write(
        f'# Found {len(shadow_users)} reset accounts (shadow users): '
        f'{", ".join(shadow_usernames)}. '
        f'Exporting scores from these accounts only.'
    )
    return shadow_users


def get_scores_from_reset_accounts(result_cls, campaign, options, command_instance):
    """
    Retrieves scores from shadow users (reset accounts) for the given result class.

    Args:
        result_cls: The result model class to query
        campaign: Campaign instance
        options: Command options dictionary
        command_instance: Command instance for logging

    Returns:
        List of filtered scores from shadow users
    """
    shadow_users = get_shadow_users()
    if not shadow_users:
        return []

    shadow_usernames = {user.username for user in shadow_users}

    # Use the include_retired parameter to get retired annotations
    all_scores = result_cls.get_system_data(
        campaign.id,
        extended_csv=True,
        add_batch_info=options['batch_info'],
        include_inactive=True,  # Include inactive users (shadow users)
        include_retired=True,   # Include retired annotations
    )

    command_instance.stderr.write(
        f"# Found {len(all_scores)} retired annotations from {result_cls.__name__}"
    )

    # Filter to only include scores from shadow users
    filtered_scores = []
    for score in all_scores:
        # Assuming the username is the first element in the score tuple
        if len(score) > 0 and score[0] in shadow_usernames:
            filtered_scores.append(score)

    return filtered_scores


def get_scores_from_active_accounts(result_cls, campaign, options):
    """
    Retrieves scores from active user accounts (normal behavior).

    Args:
        result_cls: The result model class to query
        campaign: Campaign instance
        options: Command options dictionary

    Returns:
        List of scores from active users
    """
    return result_cls.get_system_data(
        campaign.id,
        extended_csv=True,
        add_batch_info=options['batch_info'],
    )


class Command(BaseCommand):
    help = 'Exports system scores over all results to CSV format. Use --reset-accounts-only to export scores from previous annotation rounds (before task agenda resets).'

    """
    Usage examples:

    # Export scores from active users (default behavior):
    python manage.py ExportSystemScoresToCSV my_campaign --completed-only --batch-info

    # Export scores from reset accounts only (previous annotation rounds):
    python manage.py ExportSystemScoresToCSV my_campaign --reset-accounts-only --completed-only

    # Compare results by running both commands and analyzing the differences
    """

    def add_arguments(self, parser):
        parser.add_argument(
            'campaign_name',
            type=str,
            help='Name of the campaign you want to process data for',
        )
        parser.add_argument(
            '--completed-only',
            action='store_true',
            help='Include completed tasks only in the computation',
        )
        parser.add_argument(
            '--batch-info',
            action='store_true',
            help='Export batch and item IDs to help matching the scores to items in the JSON batches',
        )
        parser.add_argument(
            '--reset-accounts-only',
            action='store_true',
            help='Export scores only from reset accounts (shadow users created during task agenda resets)',
        )
        # TODO: add argument to specify batch user

    def handle(self, *args, **options):
        # Identify Campaign instance for given name.
        try:
            campaign = Campaign.get_campaign_or_raise(options['campaign_name'])
        except LookupError as error:
            raise CommandError(error)

        # Validate reset accounts if requested
        if options['reset_accounts_only']:
            shadow_users = validate_reset_accounts(self)
            if shadow_users is None:
                return

        csv_writer = csv.writer(sys.stdout, quoting=csv.QUOTE_MINIMAL)
        system_scores = []
        total_scores_exported = 0

        for task_cls, result_cls in CAMPAIGN_TASK_PAIRS:
            qs_name = task_cls.__name__.lower()
            qs_attr = f'evaldata_{qs_name}_campaign'
            qs_obj = getattr(campaign, qs_attr, None)

            # Constrain to only completed tasks, if requested.
            if options['completed_only']:
                qs_obj = qs_obj.filter(completed=True)

            if qs_obj and qs_obj.exists():
                if options['reset_accounts_only']:
                    _scores = get_scores_from_reset_accounts(result_cls, campaign, options, self)
                else:
                    _scores = get_scores_from_active_accounts(result_cls, campaign, options)

                total_scores_exported += len(_scores)
                system_scores.extend(_scores)

        # Write all scores to CSV
        for system_score in system_scores:
            csv_writer.writerow([str(x) for x in system_score])

        # Print summary to stderr so it doesn't interfere with CSV output
        account_type = "reset accounts" if options['reset_accounts_only'] else "active accounts"
        self.stderr.write(
            f"# Exported {total_scores_exported} scores from {account_type} for campaign '{campaign.campaignName}'"
        )
