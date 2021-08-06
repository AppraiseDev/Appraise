from hashlib import md5

from django.contrib.auth.models import Group
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.core.management.base import CommandError

from Campaign.models import Campaign
from Campaign.models import CampaignTeam
from Dashboard.models import validate_language_code
from EvalData.models import Market
from EvalData.models import Metadata

EX_LANGUAGES = ('guj',)

XE_LANGUAGES = ()

XY_LANGUAGES = ()


def _create_uniform_task_map(annotators, tasks, redudancy):
    """
    Creates task maps, uniformly distributed across given annotators.
    """
    _total_tasks = tasks * redudancy
    if annotators == 0 or _total_tasks % annotators > 0:
        return None

    _tasks_per_annotator = _total_tasks // annotators

    _results = []
    _current_task_id = 0
    for annotator_id in range(annotators):
        _annotator_tasks = []
        for annotator_task in range(_tasks_per_annotator):
            task_id = (_current_task_id + annotator_task) % tasks
            _annotator_tasks.append(task_id)
            _current_task_id = task_id
        _current_task_id += 1
        _results.append(tuple(_annotator_tasks))

    return _results


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

CAMPAIGN_URL = 'http://wmt19.appraise.cf/dashboard/sso/'
CAMPAIGN_NAME = 'WMT19DocSrcDACrowd2'
CAMPAIGN_KEY = 'WMT19DocSrcDACrowd2'
CAMPAIGN_NO = 230
ANNOTATORS = None  # Will be determined by TASKS_TO_ANNOTATORS mapping
TASKS = None
REDUNDANCY = 1

for code in EX_LANGUAGES + XE_LANGUAGES + XY_LANGUAGES:
    if not validate_language_code(code):
        _msg = '{0!r} contains invalid language code!'.format(code)
        raise ValueError(_msg)

for ex_code in EX_LANGUAGES:
    TASKS_TO_ANNOTATORS[('eng', ex_code)] = _create_uniform_task_map(0, 0, REDUNDANCY)

for xe_code in XE_LANGUAGES:  # type: ignore
    TASKS_TO_ANNOTATORS[(xe_code, 'eng')] = _create_uniform_task_map(0, 0, REDUNDANCY)

for xy_code in XY_LANGUAGES:  # type: ignore
    TASKS_TO_ANNOTATORS[xy_code] = _create_uniform_task_map(0, 0, REDUNDANCY)

TASKS_TO_ANNOTATORS = {
    ('eng', 'guj'): _create_uniform_task_map(77, 154, REDUNDANCY),
}


def _create_campaign_team(name, owner, tasks, redudancy):
    """
    Creates CampaignTeam instance, if it does not exist yet.

    Returns reference to CampaignTeam instance.
    """
    _cteam = CampaignTeam.objects.get_or_create(
        teamName=CAMPAIGN_NAME,
        owner=owner,
        requiredAnnotations=100,  # (tasks * redudancy), # TODO: fix
        requiredHours=50,  # (tasks * redudancy) / 2,
        createdBy=owner,
    )
    _cteam[0].members.add(owner)
    _cteam[0].save()
    return _cteam[0]


# pylint: disable=C0111,C0330,E1101
class Command(BaseCommand):
    help = 'Initialises campaign FY19 #139'

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
            raise ValueError(_msg)

        # We will collect user credentials for later print out or CSV export.
        credentials = {}

        # Find super user
        superusers = User.objects.filter(is_superuser=True)
        if not superusers.exists():
            _msg = 'Failure to identify superuser'
            self.stdout.write(_msg)
            return

        _msg = 'Identified superuser: {0}'.format(superusers[0])
        self.stdout.write(_msg)

        # Create Market and Metadata instances for all language pairs
        for code in EX_LANGUAGES:
            # EX
            _ex_market = Market.objects.filter(
                sourceLanguageCode='eng',
                targetLanguageCode=code,
                domainName='WMT19',
            )

            if not _ex_market.exists():
                _ex_market = Market.objects.get_or_create(
                    sourceLanguageCode='eng',
                    targetLanguageCode=code,
                    domainName='WMT19',
                    createdBy=superusers[0],
                )
                _ex_market = _ex_market[0]

            else:
                _ex_market = _ex_market.first()

            _ex_meta = Metadata.objects.filter(
                market=_ex_market,
                corpusName='WMT19',
                versionInfo='1.0',
                source='official',
            )

            if not _ex_meta.exists():
                _ex_meta = Metadata.objects.get_or_create(
                    market=_ex_market,
                    corpusName='WMT19',
                    versionInfo='1.0',
                    source='official',
                    createdBy=superusers[0],
                )
                _ex_meta = _ex_meta[0]

            else:
                _ex_meta = _ex_meta.first()

        for code in XE_LANGUAGES:
            # XE
            _xe_market = Market.objects.filter(
                sourceLanguageCode=code,
                targetLanguageCode='eng',
                domainName='WMT19',
            )

            if not _xe_market.exists():
                _xe_market = Market.objects.get_or_create(
                    sourceLanguageCode=code,
                    targetLanguageCode='eng',
                    domainName='WMT19',
                    createdBy=superusers[0],
                )
                _xe_market = _xe_market[0]

            else:
                _xe_market = _xe_market.first()

            _xe_meta = Metadata.objects.filter(
                market=_xe_market,
                corpusName='WMT19',
                versionInfo='1.0',
                source='official',
            )

            if not _xe_meta.exists():
                _xe_meta = Metadata.objects.get_or_create(
                    market=_xe_market,
                    corpusName='WMT19',
                    versionInfo='1.0',
                    source='official',
                    createdBy=superusers[0],
                )
                _xe_meta = _xe_meta[0]

            else:
                _xe_meta = _xe_meta.first()

        for source, target in XY_LANGUAGES:
            # XY
            _xy_market = Market.objects.filter(
                sourceLanguageCode=source,
                targetLanguageCode=target,
                domainName='WMT19',
            )

            if not _xy_market.exists():
                _xy_market = Market.objects.get_or_create(
                    sourceLanguageCode=source,
                    targetLanguageCode=target,
                    domainName='WMT19',
                    createdBy=superusers[0],
                )
                _xy_market = _xy_market[0]

            else:
                _xy_market = _xy_market.first()

            _xy_meta = Metadata.objects.filter(
                market=_xy_market,
                corpusName='WMT19',
                versionInfo='1.0',
                source='official',
            )

            if not _xy_meta.exists():
                _xy_meta = Metadata.objects.get_or_create(
                    market=_xy_market,
                    corpusName='WMT19',
                    versionInfo='1.0',
                    source='official',
                    createdBy=superusers[0],
                )
                _xy_meta = _xy_meta[0]

            else:
                _xy_meta = _xy_meta.first()

        _msg = 'Processed Market/Metadata instances'
        self.stdout.write(_msg)

        # Create User accounts
        for code in EX_LANGUAGES:
            _tasks_map = TASKS_TO_ANNOTATORS.get(('eng', code))
            if _tasks_map is None:
                _msg = 'No TASKS_TO_ANNOTATORS mapping for {0}'.format(('eng', code))
                self.stdout.write(_msg)
                continue

            if sum([len(x) for x in _tasks_map]) % REDUNDANCY > 0:
                _msg = 'Bad TASKS_TO_ANNOTATORS mapping for {0}'.format(('eng', code))
                self.stdout.write(_msg)
                continue

            TASKS = sum([len(x) for x in _tasks_map]) // REDUNDANCY
            ANNOTATORS = len(_tasks_map)

            campaign_team_object = _create_campaign_team(
                CAMPAIGN_NAME, superusers[0], TASKS, ANNOTATORS
            )

            # EX
            for user_id in range(ANNOTATORS):
                username = '{0}{1}{2:02x}{3:02x}'.format(
                    'eng', code, CAMPAIGN_NO, user_id + 1
                )

                hasher = md5()
                hasher.update(username.encode('utf8'))
                hasher.update(CAMPAIGN_KEY.encode('utf8'))
                secret = hasher.hexdigest()[:8]

                if not User.objects.filter(username=username).exists():
                    new_user = User.objects.create_user(
                        username=username, password=secret
                    )
                    new_user.save()

                credentials[username] = secret

        for code in XE_LANGUAGES:
            _tasks_map = TASKS_TO_ANNOTATORS.get((code, 'eng'))
            if _tasks_map is None:
                _msg = 'No TASKS_TO_ANNOTATORS mapping for {0}'.format((code, 'eng'))
                self.stdout.write(_msg)
                continue

            if sum([len(x) for x in _tasks_map]) % REDUNDANCY > 0:
                _msg = 'Bad TASKS_TO_ANNOTATORS mapping for {0}'.format((code, 'eng'))
                self.stdout.write(_msg)
                continue

            TASKS = sum([len(x) for x in _tasks_map]) // REDUNDANCY
            ANNOTATORS = len(_tasks_map)

            _cteam = _create_campaign_team(
                CAMPAIGN_NAME, superusers[0], TASKS, ANNOTATORS
            )

            # XE
            for user_id in range(ANNOTATORS):
                username = '{0}{1}{2:02x}{3:02x}'.format(
                    code, 'eng', CAMPAIGN_NO, user_id + 1
                )

                hasher = md5()
                hasher.update(username.encode('utf8'))
                hasher.update(CAMPAIGN_KEY.encode('utf8'))
                secret = hasher.hexdigest()[:8]

                if not User.objects.filter(username=username).exists():
                    new_user = User.objects.create_user(
                        username=username, password=secret
                    )
                    new_user.save()

                credentials[username] = secret

        for source, target in XY_LANGUAGES:
            _tasks_map = TASKS_TO_ANNOTATORS.get((source, target))
            if _tasks_map is None:
                _msg = 'No TASKS_TO_ANNOTATORS mapping for {0}'.format((source, target))
                self.stdout.write(_msg)
                continue

            if sum([len(x) for x in _tasks_map]) % REDUNDANCY > 0:
                _msg = 'Bad TASKS_TO_ANNOTATORS mapping for {0}'.format(
                    (source, target)
                )
                self.stdout.write(_msg)
                continue

            TASKS = sum([len(x) for x in _tasks_map]) // REDUNDANCY
            ANNOTATORS = len(_tasks_map)

            _cteam = _create_campaign_team(
                CAMPAIGN_NAME, superusers[0], TASKS, ANNOTATORS
            )

            # XY
            for user_id in range(ANNOTATORS):
                username = '{0}{1}{2:02x}{3:02x}'.format(
                    source, target, CAMPAIGN_NO, user_id + 1
                )

                hasher = md5()
                hasher.update(username.encode('utf8'))
                hasher.update(CAMPAIGN_KEY.encode('utf8'))
                secret = hasher.hexdigest()[:8]

                if not User.objects.filter(username=username).exists():
                    new_user = User.objects.create_user(
                        username=username, password=secret
                    )
                    new_user.save()

                credentials[username] = secret

        _msg = 'Processed User instances'
        self.stdout.write(_msg)

        # Print credentials to screen.
        for username, secret in credentials.items():
            print(username, secret)

        # Write credentials to CSV file if specified.
        if csv_output:
            csv_lines = [','.join(('Username', 'Password', 'URL')) + '\n']
            for u, p in credentials.items():
                url = '{0}{1}/{2}/'.format(CAMPAIGN_URL, u, p)
                csv_lines.append(','.join((u, p, url)) + '\n')
            with open(csv_output, mode='w') as out_file:
                out_file.writelines(csv_lines)

        # Add user instances as CampaignTeam members
        for code in EX_LANGUAGES:
            _tasks_map = TASKS_TO_ANNOTATORS.get(('eng', code))
            if _tasks_map is None:
                _msg = 'No TASKS_TO_ANNOTATORS mapping for {0}'.format(('eng', code))
                self.stdout.write(_msg)
                continue

            if sum([len(x) for x in _tasks_map]) % REDUNDANCY > 0:
                _msg = 'Bad TASKS_TO_ANNOTATORS mapping for {0}'.format(('eng', code))
                self.stdout.write(_msg)
                continue

            TASKS = sum([len(x) for x in _tasks_map]) // REDUNDANCY
            ANNOTATORS = len(_tasks_map)

            campaign_team_object = _create_campaign_team(
                CAMPAIGN_NAME, superusers[0], TASKS, ANNOTATORS
            )

            # EX
            for user_id in range(ANNOTATORS):
                username = '{0}{1}{2:02x}{3:02x}'.format(
                    'eng', code, CAMPAIGN_NO, user_id + 1
                )

                user_object = User.objects.get(username=username)
                if user_object not in campaign_team_object.members.all():
                    print(
                        '{0} --> {1}'.format(
                            campaign_team_object.teamName,
                            user_object.username,
                        )
                    )
                    campaign_team_object.members.add(user_object)

        for code in XE_LANGUAGES:
            _tasks_map = TASKS_TO_ANNOTATORS.get((code, 'eng'))
            if _tasks_map is None:
                _msg = 'No TASKS_TO_ANNOTATORS mapping for {0}'.format((code, 'eng'))
                self.stdout.write(_msg)
                continue

            if sum([len(x) for x in _tasks_map]) % REDUNDANCY > 0:
                _msg = 'Bad TASKS_TO_ANNOTATORS mapping for {0}'.format((code, 'eng'))
                self.stdout.write(_msg)
                continue

            TASKS = sum([len(x) for x in _tasks_map]) // REDUNDANCY
            ANNOTATORS = len(_tasks_map)

            campaign_team_object = _create_campaign_team(
                CAMPAIGN_NAME, superusers[0], TASKS, ANNOTATORS
            )

            # XE
            for user_id in range(ANNOTATORS):
                username = '{0}{1}{2:02x}{3:02x}'.format(
                    code, 'eng', CAMPAIGN_NO, user_id + 1
                )

                user_object = User.objects.get(username=username)
                if user_object not in campaign_team_object.members.all():
                    print(
                        '{0} --> {1}'.format(
                            campaign_team_object.teamName,
                            user_object.username,
                        )
                    )
                    campaign_team_object.members.add(user_object)

        for source, target in XY_LANGUAGES:
            _tasks_map = TASKS_TO_ANNOTATORS.get((source, target))
            if _tasks_map is None:
                _msg = 'No TASKS_TO_ANNOTATORS mapping for {0}'.format((source, target))
                self.stdout.write(_msg)
                continue

            if sum([len(x) for x in _tasks_map]) % REDUNDANCY > 0:
                _msg = 'Bad TASKS_TO_ANNOTATORS mapping for {0}'.format(
                    (source, target)
                )
                self.stdout.write(_msg)
                continue

            TASKS = sum([len(x) for x in _tasks_map]) // REDUNDANCY
            ANNOTATORS = len(_tasks_map)

            campaign_team_object = _create_campaign_team(
                CAMPAIGN_NAME, superusers[0], TASKS, ANNOTATORS
            )

            # XY
            for user_id in range(ANNOTATORS):
                username = '{0}{1}{2:02x}{3:02x}'.format(
                    source, target, CAMPAIGN_NO, user_id + 1
                )

                user_object = User.objects.get(username=username)
                if user_object not in campaign_team_object.members.all():
                    print(
                        '{0} --> {1}'.format(
                            campaign_team_object.teamName,
                            user_object.username,
                        )
                    )
                    campaign_team_object.members.add(user_object)

        _msg = 'Processed CampaignTeam members'
        self.stdout.write(_msg)

        c = Campaign.objects.filter(campaignName=CAMPAIGN_NAME)
        if not c.exists():
            return
        c = c[0]

        from EvalData.models import (
            DirectAssessmentContextTask,
            TaskAgenda,
            ObjectID,
        )
        from collections import defaultdict

        tasks = DirectAssessmentContextTask.objects.filter(campaign=c, activated=True)

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
            _tasks_map = TASKS_TO_ANNOTATORS.get((source, target))
            if _tasks_map is None:
                _msg = 'No TASKS_TO_ANNOTATORS mapping for {0}'.format((source, target))
                self.stdout.write(_msg)
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

                a = TaskAgenda.objects.filter(user=u, campaign=c)

                if not a.exists():
                    a = TaskAgenda.objects.create(user=u, campaign=c)
                else:
                    a = a[0]

                serialized_t = ObjectID.objects.get_or_create(
                    typeName='DirectAssessmentContextTask', primaryID=t.id
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
