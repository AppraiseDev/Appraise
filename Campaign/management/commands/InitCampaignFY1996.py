"""
Appraise evaluation framework

See LICENSE for usage details
"""
from collections import defaultdict

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError

from Campaign.models import Campaign
from Campaign.utils import (
    _create_uniform_task_map,
    _get_or_create_campaign_team,
    _get_or_create_market,
    _get_or_create_meta,
    _get_tasks_map_for_language_pair,
    _identify_super_users,
    _process_campaign_teams,
    _process_market_and_metadata,
    _process_users,
)
from Dashboard.models import validate_language_code
from EvalData.models import (
    DirectAssessmentTask,
    TaskAgenda,
    ObjectID,
    Market,
    Metadata,
)

EX_LANGUAGES = (
    'ara',
    'deu',
    'fra',
    'ita',
    'jpn',
    'kor',
    'por',
    'rus',
    'spa',
    'zho',
)

XE_LANGUAGES = (
    'ara',
    'deu',
    'fra',
    'ita',
    'jpn',
    'kor',
    'por',
    'rus',
    'spa',
    'zho',
)

XY_LANGUAGES = ()


# Allows for arbitrary task to annotator mappings.
#
# Can be uniformly distributed, i.e., 2 tasks per annotator:
#     ('src', 'dst'): [2 for _ in range(no_annotators)],
#
# Also possible to supply a customised list:
#     ('src', 'dst'): [2, 1, 3, 2, 2],
#
# The number of list items explictly defines the number of annotators.
# To use mapping defined in TASK_TO_ANNOTATORS, set both ANNOTATORS = None
# and TASKS = None in the campaign config section below.
#
# Example:
#
# TASKS_TO_ANNOTATORS = {
#     ('deu', 'ces') : _create_uniform_task_map(12, 24, REDUNDANCY),
# }
TASKS_TO_ANNOTATORS = {}

CAMPAIGN_URL = 'http://msrmt.appraise.cf/dashboard/sso/'
CAMPAIGN_NAME = 'HumanEvalFY1996'
CAMPAIGN_KEY = 'FY1996'
CAMPAIGN_NO = 238
ANNOTATORS = None  # Will be determined by TASKS_TO_ANNOTATORS mapping
TASKS = None
REDUNDANCY = 1

CONTEXT = {
    'ANNOTATORS': ANNOTATORS,
    'CAMPAIGN_KEY': CAMPAIGN_KEY,
    'CAMPAIGN_NAME': CAMPAIGN_NAME,
    'CAMPAIGN_NO': CAMPAIGN_NO,
    'CAMPAIGN_URL': CAMPAIGN_URL,
    'REDUNDANCY': REDUNDANCY,
    'TASKS': TASKS,
    'TASKS_TO_ANNOTATORS': TASKS_TO_ANNOTATORS,
}

for code in EX_LANGUAGES + XE_LANGUAGES + XY_LANGUAGES:
    if not validate_language_code(code):
        _msg = '{0!r} contains invalid language code!'.format(code)
        raise CommandError(_msg)

for ex_code in EX_LANGUAGES:
    TASKS_TO_ANNOTATORS[('eng', ex_code)] = _create_uniform_task_map(
        10, 20, REDUNDANCY
    )

for xe_code in XE_LANGUAGES:
    TASKS_TO_ANNOTATORS[(xe_code, 'eng')] = _create_uniform_task_map(
        10, 20, REDUNDANCY
    )

for xy_code in XY_LANGUAGES:
    TASKS_TO_ANNOTATORS[xy_code] = _create_uniform_task_map(
        0, 0, REDUNDANCY
    )


# pylint: disable=C0111,C0330,E1101
class Command(BaseCommand):
    help = 'Initialises campaign FY19 #150'

    def add_arguments(self, parser):
        parser.add_argument(
            '--csv-output',
            type=str,
            default=None,
            metavar='--csv',
            help='Path used to create CSV file containing credentials.',
        )

    def handle(self, *args, **options):
        csv_output = options['csv_output']
        self.stdout.write('CSV output path: {0!r}'.format(csv_output))
        if csv_output and not csv_output.endswith('.csv'):
            _msg = 'csv_output does not point to .csv file'
            raise CommandError(_msg)

        # Find super user
        superusers = _identify_super_users()

        _msg = 'Identified superuser: {0}'.format(superusers[0])
        self.stdout.write(_msg)

        # Compute list of all language pairs
        _all_languages = (
            [('eng', _tgt) for _tgt in EX_LANGUAGES]
            + [(_src, 'eng') for _src in XE_LANGUAGES]
            + [(_src, _tgt) for _src, _tgt in XY_LANGUAGES]
        )

        # Process Market and Metadata instances for all language pairs
        _process_market_and_metadata(_all_languages, superusers[0])

        _msg = 'Processed Market/Metadata instances'
        self.stdout.write(_msg)

        # Create User accounts for all language pairs. We collect the
        # resulting user credentials for later print out/CSV export.
        credentials = _process_users(_all_languages, CONTEXT)

        _msg = 'Processed User instances'
        self.stdout.write(_msg)

        # Print credentials to screen.
        for username, secret in credentials.items():
            print(username, secret)

        # Write credentials to CSV file if specified.
        if csv_output:
            csv_lines = [','.join(('Username', 'Password', 'URL')) + '\n']
            for _user, _password in credentials.items():
                _url = '{0}{1}/{2}/'.format(CAMPAIGN_URL, _user, _password)
                csv_lines.append(','.join((_user, _password, _url)) + '\n')
            with open(csv_output, mode='w') as out_file:
                out_file.writelines(csv_lines)

        # Add user instances as CampaignTeam members
        _process_campaign_teams(_all_languages, superusers[0], CONTEXT)

        _msg = 'Processed CampaignTeam members'
        self.stdout.write(_msg)

        _campaign = Campaign.objects.filter(campaignName=CAMPAIGN_NAME)
        if not _campaign.exists():
            _msg = (
                'Campaign {0!r} does not exist. No task agendas '
                'have been assigned.'.format(CAMPAIGN_NAME)
            )
            raise CommandError(_msg)

        _campaign = _campaign[0]

        tasks = DirectAssessmentTask.objects.filter(
            campaign=_campaign, activated=True
        )

        # Assignment scheme:
        #
        # T1 U1 U2
        # T2 U3 U4
        # T3 U1 U2
        # T4 U3 U4
        #
        # To assign this, we need to duplicate Ts below.
        tasks_for_market = defaultdict(list)
        users_for_market = defaultdict(list)
        for task in tasks.order_by('id'):
            market = '{0}{1:02x}'.format(
                task.marketName().replace('_', '')[:6], CAMPAIGN_NO
            )
            tasks_for_market[market].append(task)

        # This assigns tasks like this
        #
        # T1 U1 U3
        # T2 U1 U4
        # T3 U2 U4
        # T4 U2 U5
        # T5 U3 U5
        #
        #        tasks_for_current_market = tasks_for_market[market]
        #        redundant_tasks = []
        #        for i in range(REDUNDANCY):
        #            redundant_tasks.extend(tasks_for_current_market)
        #        tasks_for_market[market] = redundant_tasks

        for key in tasks_for_market:
            users = User.objects.filter(username__startswith=key)

            source = key[:3]
            target = key[3:6]

            try:
                _tasks_map = _get_tasks_map_for_language_pair(
                    source, target, CONTEXT
                )

            except (LookupError, ValueError) as _exc:
                self.stdout.write(str(_exc))
                continue

            _tasks = tasks_for_market[key]
            tasks_for_market[key] = []
            for user, tasks in zip(users.order_by('id'), _tasks_map):
                print(source, target, user, tasks)
                for task_id in tasks:
                    users_for_market[key].append(user)
                    tasks_for_market[key].append(_tasks[task_id])

            # _tasks should match _users in size
            _tasks = tasks_for_market[key]
            _users = users_for_market[key]
            for u, t in zip(_users, _tasks):
                print(u, '-->', t.id)

                a = TaskAgenda.objects.filter(user=u, campaign=_campaign)

                if not a.exists():
                    a = TaskAgenda.objects.create(
                        user=u, campaign=_campaign
                    )
                else:
                    a = a[0]

                serialized_t = ObjectID.objects.get_or_create(
                    typeName='DirectAssessmentTask', primaryID=t.id
                )

                _task_done_for_user = t.next_item_for_user(u) is None
                if _task_done_for_user:
                    if serialized_t[0] not in a._completed_tasks.all():
                        a._completed_tasks.add(serialized_t[0])
                    if serialized_t[0] in a._open_tasks.all():
                        a._open_tasks.remove(serialized_t[0])

                else:
                    if serialized_t[0] in a._completed_tasks.all():
                        a._completed_tasks.remove(serialized_t[0])
                    if serialized_t[0] not in a._open_tasks.all():
                        a._open_tasks.add(serialized_t[0])
