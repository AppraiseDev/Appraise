"""
Appraise evaluation framework

See LICENSE for usage details
"""
from hashlib import md5

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError

from Campaign.models import Campaign, CampaignTeam
from Dashboard.models import validate_language_code
from EvalData.models import Market, Metadata

EX_LANGUAGES = (
    'afr',
    'fas',
    'lav',
    'nld',
    'nob',
    'ron',
    'slk',
    'slv',
    'swe',
    'urd',
)

XE_LANGUAGES = (
    'afr',
    'fas',
    'lav',
    'nld',
    'nob',
    'ron',
    'slk',
    'slv',
    'swe',
)

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
    for _unused_annotator_id in range(annotators):
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

CAMPAIGN_URL = 'http://msrmt.appraise.cf/dashboard/sso/'
CAMPAIGN_NAME = 'HumanEvalFY1995'
CAMPAIGN_KEY = 'FY1995'
CAMPAIGN_NO = 237
ANNOTATORS = None  # Will be determined by TASKS_TO_ANNOTATORS mapping
TASKS = None
REDUNDANCY = 1

for code in EX_LANGUAGES + XE_LANGUAGES + XY_LANGUAGES:
    if not validate_language_code(code):
        _msg = '{0!r} contains invalid language code!'.format(code)
        raise CommandError(_msg)

for ex_code in EX_LANGUAGES:
    TASKS_TO_ANNOTATORS[('eng', ex_code)] = _create_uniform_task_map(
        5, 10, REDUNDANCY
    )

for xe_code in XE_LANGUAGES:
    TASKS_TO_ANNOTATORS[(xe_code, 'eng')] = _create_uniform_task_map(
        5, 10, REDUNDANCY
    )

for xy_code in XY_LANGUAGES:
    TASKS_TO_ANNOTATORS[xy_code] = _create_uniform_task_map(
        0, 0, REDUNDANCY
    )


def _get_or_create_campaign_team(name, owner, tasks, redudancy):
    """
    Creates CampaignTeam instance, if it does not exist yet.

    Returns reference to CampaignTeam instance.
    """
    # pylint: disable-msg=no-member
    _cteam = CampaignTeam.objects.get_or_create(
        teamName=name,
        owner=owner,
        requiredAnnotations=100,  # (tasks * redudancy), # TODO: fix
        requiredHours=50,  # (tasks * redudancy) / 2,
        createdBy=owner,
    )
    _cteam[0].members.add(owner)
    _cteam[0].save()
    return _cteam[0]


def _get_or_create_market(source_code, target_code, domain_name, owner):
    """
    Creates Market instance, if it does not exist yet.

    Returns reference to Market instance.
    """
    # pylint: disable-msg=no-member
    _market, _unused_created_signal = Market.objects.get_or_create(
        sourceLanguageCode=source_code,
        targetLanguageCode=target_code,
        domainName=domain_name,
        createdBy=owner,
    )
    return _market


def _get_or_create_meta(market, corpus_name, version_info, source, owner):
    """
    Creates Meta instance, if it does not exist yet.

    Returns reference to Meta instance.
    """
    # pylint: disable-msg=no-member
    _meta, _unused_created_signal = Metadata.objects.get_or_create(
        market=market,
        corpusName=corpus_name,
        versionInfo=version_info,
        source=source,
        createdBy=owner,
    )
    return _meta


# pylint: disable=C0111,C0330,E1101
class Command(BaseCommand):
    help = 'Initialises campaign FY19 #149'

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

        # Compute list of all language pairs
        _all_languages = (
            [('eng', _tgt) for _tgt in EX_LANGUAGES]
            + [(_src, 'eng') for _src in XE_LANGUAGES]
            + [(_src, _tgt) for _src, _tgt in XY_LANGUAGES]
        )

        # Create Market and Metadata instances for all language pairs
        for _src, _tgt in _all_languages:
            _market = _get_or_create_market(
                source_code=_src,
                target_code=_tgt,
                domain_name='AppenFY19',
                owner=superusers[0],
            )

            _meta = _get_or_create_meta(
                market=_market,
                corpus_name='AppenFY19',
                version_info='1.0',
                source='official',
                owner=superusers[0],
            )

        _msg = 'Processed Market/Metadata instances'
        self.stdout.write(_msg)

        # Create User accounts for all language pairs
        for _src, _tgt in _all_languages:
            _tasks_map = TASKS_TO_ANNOTATORS.get((_src, _tgt))
            if _tasks_map is None:
                _msg = 'No TASKS_TO_ANNOTATORS mapping for {0}'.format(
                    (_src, _tgt)
                )
                self.stdout.write(_msg)
                continue

            if sum([len(x) for x in _tasks_map]) % REDUNDANCY > 0:
                _msg = 'Bad TASKS_TO_ANNOTATORS mapping for {0}'.format(
                    (_src, _tgt)
                )
                self.stdout.write(_msg)
                continue

            _tasks = sum([len(x) for x in _tasks_map]) // REDUNDANCY
            _annotators = len(_tasks_map)

            campaign_team_object = _get_or_create_campaign_team(
                CAMPAIGN_NAME, superusers[0], _tasks, _annotators
            )

            for user_id in range(_annotators):
                username = '{0}{1}{2:02x}{3:02x}'.format(
                    _src, _tgt, CAMPAIGN_NO, user_id + 1
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
            for _user, _password in credentials.items():
                _url = '{0}{1}/{2}/'.format(CAMPAIGN_URL, _user, _password)
                csv_lines.append(','.join((_user, _password, _url)) + '\n')
            with open(csv_output, mode='w') as out_file:
                out_file.writelines(csv_lines)

        # Add user instances as CampaignTeam members
        for _src, _tgt in _all_languages:
            _tasks_map = TASKS_TO_ANNOTATORS.get((_src, _tgt))
            if _tasks_map is None:
                _msg = 'No TASKS_TO_ANNOTATORS mapping for {0}'.format(
                    (_src, _tgt)
                )
                self.stdout.write(_msg)
                continue

            if sum([len(x) for x in _tasks_map]) % REDUNDANCY > 0:
                _msg = 'Bad TASKS_TO_ANNOTATORS mapping for {0}'.format(
                    (_src, _tgt)
                )
                self.stdout.write(_msg)
                continue

            _tasks = sum([len(x) for x in _tasks_map]) // REDUNDANCY
            _annotators = len(_tasks_map)

            campaign_team_object = _get_or_create_campaign_team(
                CAMPAIGN_NAME, superusers[0], _tasks, _annotators
            )

            for user_id in range(_annotators):
                username = '{0}{1}{2:02x}{3:02x}'.format(
                    _src, _tgt, CAMPAIGN_NO, user_id + 1
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

        _campaign = Campaign.objects.filter(campaignName=CAMPAIGN_NAME)
        if not _campaign.exists():
            _msg = (
                'Campaign {0!r} does not exist. No task agendas '
                'have been assigned.'.format(CAMPAIGN_NAME)
            )
            raise CommandError(_msg)

        _campaign = _campaign[0]

        from EvalData.models import (
            DirectAssessmentTask,
            TaskAgenda,
            ObjectID,
        )
        from collections import defaultdict

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
            _tasks_map = TASKS_TO_ANNOTATORS.get((source, target))
            if _tasks_map is None:
                _msg = 'No TASKS_TO_ANNOTATORS mapping for {0}'.format(
                    (source, target)
                )
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
