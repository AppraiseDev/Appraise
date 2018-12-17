from hashlib import md5

from django.contrib.auth.models import User, Group
from django.core.management.base import BaseCommand, CommandError

from Campaign.models import Campaign, CampaignTeam
from EvalData.models import Market, Metadata

EX_LANGUAGES = (
    'ara', 'deu', 'fra', 'ita', 'jpn', 'kor', 'por', 'rus', 'spa', 'zho'
)

XE_LANGUAGES = (
    'ara', 'deu', 'fra', 'ita', 'jpn', 'kor', 'por', 'rus', 'spa', 'zho'
)

XY_LANGUAGES = (
)

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
TASKS_TO_ANNOTATORS = {
    ('ara', 'eng'): [2 for _ in range(15)],
    ('deu', 'eng'): [2 for _ in range(22)],
    ('fra', 'eng'): [2 for _ in range(27)],
    ('ita', 'eng'): [2 for _ in range(17)],
    ('jpn', 'eng'): [2 for _ in range(12)],
    ('kor', 'eng'): [2 for _ in range(9)],
    ('por', 'eng'): [2 for _ in range(14)],
    ('rus', 'eng'): [2 for _ in range(14)],
    ('spa', 'eng'): [2 for _ in range(23)],
    ('zho', 'eng'): [2 for _ in range(25)],
    ('eng', 'ara'): [2 for _ in range(15)],
    ('eng', 'deu'): [2 for _ in range(22)],
    ('eng', 'fra'): [2 for _ in range(27)],
    ('eng', 'ita'): [2 for _ in range(17)],
    ('eng', 'jpn'): [2 for _ in range(12)],
    ('eng', 'kor'): [2 for _ in range(9)],
    ('eng', 'por'): [2 for _ in range(14)],
    ('eng', 'rus'): [2 for _ in range(14)],
    ('eng', 'spa'): [2 for _ in range(23)],
    ('eng', 'zho'): [2 for _ in range(25)],
}

CAMPAIGN_NAME = 'HumanEvalFY193A'
CAMPAIGN_KEY = 'FY193A'
CAMPAIGN_NO = 146
ANNOTATORS = None # Will be determined by TASKS_TO_ANNOTATORS mapping
TASKS = None
REDUNDANCY = 1

def _create_campaign_team(name, owner, tasks, redudancy):
    """
    Creates CampaignTeam instance, if it does not exist yet.

    Returns reference to CampaignTeam instance.
    """
    _cteam = CampaignTeam.objects.get_or_create(
      teamName=CAMPAIGN_NAME,
      owner=owner,
      requiredAnnotations=100, #(tasks * redudancy), # TODO: fix
      requiredHours=50, #(tasks * redudancy) / 2,
      createdBy=owner
    )
    _cteam[0].members.add(owner)
    _cteam[0].save()
    return _cteam[0]

# pylint: disable=C0111,C0330,E1101
class Command(BaseCommand):
    help = 'Initialises campaign FY19 #58'

    def handle(self, *args, **options):
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
              domainName='AppenFY19'              
            )

            if not _ex_market.exists():
                _ex_market = Market.objects.get_or_create(
                  sourceLanguageCode='eng',
                  targetLanguageCode=code,
                  domainName='AppenFY19',
                  createdBy=superusers[0]
                )
                _ex_market = _ex_market[0]

            else:
                _ex_market = _ex_market.first()

            _ex_meta = Metadata.objects.filter(
              market=_ex_market,
              corpusName='AppenFY19',
              versionInfo='1.0',
              source='official'             
            )

            if not _ex_meta.exists():
                _ex_meta = Metadata.objects.get_or_create(
                  market=_ex_market,
                  corpusName='AppenFY19',
                  versionInfo='1.0',
                  source='official',
                  createdBy=superusers[0]
                )
                _ex_meta = _ex_meta[0]

            else:
                _ex_meta = _ex_meta.first()

        for code in XE_LANGUAGES:
            # XE
            _xe_market = Market.objects.filter(
              sourceLanguageCode=code,
              targetLanguageCode='eng',
              domainName='AppenFY19'              
            )

            if not _xe_market.exists():
                _xe_market = Market.objects.get_or_create(
                  sourceLanguageCode=code,
                  targetLanguageCode='eng',
                  domainName='AppenFY19',
                  createdBy=superusers[0]
                )
                _xe_market = _xe_market[0]

            else:
                _xe_market = _xe_market.first()

            _xe_meta = Metadata.objects.filter(
              market=_xe_market,
              corpusName='AppenFY19',
              versionInfo='1.0',
              source='official'             
            )

            if not _xe_meta.exists():
                _xe_meta = Metadata.objects.get_or_create(
                  market=_xe_market,
                  corpusName='AppenFY19',
                  versionInfo='1.0',
                  source='official',
                  createdBy=superusers[0]
                )
                _xe_meta = _xe_meta[0]

            else:
                _xe_meta = _xe_meta.first()

        for source, target in XY_LANGUAGES:
            # XY
            _xy_market = Market.objects.filter(
              sourceLanguageCode=source,
              targetLanguageCode=target,
              domainName='AppenFY19'              
            )

            if not _xy_market.exists():
                _xy_market = Market.objects.get_or_create(
                  sourceLanguageCode=source,
                  targetLanguageCode=target,
                  domainName='AppenFY19',
                  createdBy=superusers[0]
                )
                _xy_market = _xy_market[0]

            else:
                _xy_market = _xy_market.first()

            _xy_meta = Metadata.objects.filter(
              market=_xy_market,
              corpusName='AppenFY19',
              versionInfo='1.0',
              source='official'             
            )

            if not _xy_meta.exists():
                _xy_meta = Metadata.objects.get_or_create(
                  market=_xy_market,
                  corpusName='AppenFY19',
                  versionInfo='1.0',
                  source='official',
                  createdBy=superusers[0]
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
                _msg = 'No TASKS_TO_ANNOTATORS mapping for {0}'.format(
                    ('eng', code))
                self.stdout.write(_msg)
                continue

            if sum(_tasks_map) % REDUNDANCY > 0:
                _msg = 'Bad TASKS_TO_ANNOTATORS mapping for {0}'.format(
                    ('eng', code))
                self.stdout.write(_msg)
                continue

            TASKS = sum(_tasks_map) // REDUNDANCY
            ANNOTATORS = len(_tasks_map)

            campaign_team_object = _create_campaign_team(
                CAMPAIGN_NAME, superusers[0], TASKS, ANNOTATORS)

            # EX
            for user_id in range(ANNOTATORS):
                username = '{0}{1}{2:02x}{3:02d}'.format(
                  'eng', code, CAMPAIGN_NO, user_id+1
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

                print(username, secret)

        for code in XE_LANGUAGES:
            _tasks_map = TASKS_TO_ANNOTATORS.get((code, 'eng'))
            if _tasks_map is None:
                _msg = 'No TASKS_TO_ANNOTATORS mapping for {0}'.format(
                    (code, 'eng'))
                self.stdout.write(_msg)
                continue

            if sum(_tasks_map) % REDUNDANCY > 0:
                _msg = 'Bad TASKS_TO_ANNOTATORS mapping for {0}'.format(
                    (code, 'eng'))
                self.stdout.write(_msg)
                continue

            TASKS = sum(_tasks_map) // REDUNDANCY
            ANNOTATORS = len(_tasks_map)

            _cteam = _create_campaign_team(
                CAMPAIGN_NAME, superusers[0], TASKS, ANNOTATORS)

            # XE
            for user_id in range(ANNOTATORS):
                username = '{0}{1}{2:02x}{3:02d}'.format(
                  code, 'eng', CAMPAIGN_NO, user_id+1
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

                print(username, secret)

        for source, target in XY_LANGUAGES:
            _tasks_map = TASKS_TO_ANNOTATORS.get((source, target))
            if _tasks_map is None:
                _msg = 'No TASKS_TO_ANNOTATORS mapping for {0}'.format(
                    (source, target))
                self.stdout.write(_msg)
                continue

            if sum(_tasks_map) % REDUNDANCY > 0:
                _msg = 'Bad TASKS_TO_ANNOTATORS mapping for {0}'.format(
                    (source, target))
                self.stdout.write(_msg)
                continue

            TASKS = sum(_tasks_map) // REDUNDANCY
            ANNOTATORS = len(_tasks_map)

            _cteam = _create_campaign_team(
                CAMPAIGN_NAME, superusers[0], TASKS, ANNOTATORS)

            # XY
            for user_id in range(ANNOTATORS):
                username = '{0}{1}{2:02x}{3:02d}'.format(
                  source, target, CAMPAIGN_NO, user_id+1
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

                print(username, secret)

        _msg = 'Processed User instances'
        self.stdout.write(_msg)

        # Add user instances as CampaignTeam members
        for code in EX_LANGUAGES:
            _tasks_map = TASKS_TO_ANNOTATORS.get(('eng', code))
            if _tasks_map is None:
                _msg = 'No TASKS_TO_ANNOTATORS mapping for {0}'.format(
                    ('eng', code))
                self.stdout.write(_msg)
                continue

            if sum(_tasks_map) % REDUNDANCY > 0:
                _msg = 'Bad TASKS_TO_ANNOTATORS mapping for {0}'.format(
                    ('eng', code))
                self.stdout.write(_msg)
                continue

            TASKS = sum(_tasks_map) // REDUNDANCY
            ANNOTATORS = len(_tasks_map)

            campaign_team_object = _create_campaign_team(
                CAMPAIGN_NAME, superusers[0], TASKS, ANNOTATORS)

            # EX
            for user_id in range(ANNOTATORS):
                username = '{0}{1}{2:02x}{3:02d}'.format(
                  'eng', code, CAMPAIGN_NO, user_id+1
                )

                user_object = User.objects.get(username=username)
                if user_object not in campaign_team_object.members.all():
                    print('{0} --> {1}'.format(
                      campaign_team_object.teamName, user_object.username
                    ))
                    campaign_team_object.members.add(user_object)

        for code in XE_LANGUAGES:
            _tasks_map = TASKS_TO_ANNOTATORS.get((code, 'eng'))
            if _tasks_map is None:
                _msg = 'No TASKS_TO_ANNOTATORS mapping for {0}'.format(
                    (code, 'eng'))
                self.stdout.write(_msg)
                continue

            if sum(_tasks_map) % REDUNDANCY > 0:
                _msg = 'Bad TASKS_TO_ANNOTATORS mapping for {0}'.format(
                    (code, 'eng'))
                self.stdout.write(_msg)
                continue

            TASKS = sum(_tasks_map) // REDUNDANCY
            ANNOTATORS = len(_tasks_map)

            campaign_team_object = _create_campaign_team(
                CAMPAIGN_NAME, superusers[0], TASKS, ANNOTATORS)

            # XE
            for user_id in range(ANNOTATORS):
                username = '{0}{1}{2:02x}{3:02d}'.format(
                  code, 'eng', CAMPAIGN_NO, user_id+1
                )

                user_object = User.objects.get(username=username)
                if user_object not in campaign_team_object.members.all():
                    print('{0} --> {1}'.format(
                      campaign_team_object.teamName, user_object.username
                    ))
                    campaign_team_object.members.add(user_object)

        for source, target in XY_LANGUAGES:
            _tasks_map = TASKS_TO_ANNOTATORS.get((source, target))
            if _tasks_map is None:
                _msg = 'No TASKS_TO_ANNOTATORS mapping for {0}'.format(
                    (source, target))
                self.stdout.write(_msg)
                continue

            if sum(_tasks_map) % REDUNDANCY > 0:
                _msg = 'Bad TASKS_TO_ANNOTATORS mapping for {0}'.format(
                    (source, target))
                self.stdout.write(_msg)
                continue

            TASKS = sum(_tasks_map) // REDUNDANCY
            ANNOTATORS = len(_tasks_map)

            campaign_team_object = _create_campaign_team(
                CAMPAIGN_NAME, superusers[0], TASKS, ANNOTATORS)

            # XY
            for user_id in range(ANNOTATORS):
                username = '{0}{1}{2:02x}{3:02d}'.format(
                  source, target, CAMPAIGN_NO, user_id+1
                )

                user_object = User.objects.get(username=username)
                if user_object not in campaign_team_object.members.all():
                    print('{0} --> {1}'.format(
                      campaign_team_object.teamName, user_object.username
                    ))
                    campaign_team_object.members.add(user_object)

        _msg = 'Processed CampaignTeam members'
        self.stdout.write(_msg)

        c = Campaign.objects.filter(campaignName=CAMPAIGN_NAME)
        if not c.exists():
          return
        c = c[0]

        from EvalData.models import DirectAssessmentTask, TaskAgenda, ObjectID
        from collections import defaultdict
        tasks = DirectAssessmentTask.objects.filter(
          campaign=c, activated=True
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
              task.marketName().replace('_', '')[:6],
              CAMPAIGN_NO
            )
            for i in range(REDUNDANCY):
                tasks_for_market[market].append(task)

        for key in tasks_for_market:
            users = User.objects.filter(
              username__startswith=key
            )

            source = key[:3]
            target = key[3:6]
            _tasks_map = TASKS_TO_ANNOTATORS.get((source, target))
            if _tasks_map is None:
                _msg = 'No TASKS_TO_ANNOTATORS mapping for {0}'.format(
                    (source, target))
                self.stdout.write(_msg)
                continue

            for user, tasks in zip(users.order_by('id'), _tasks_map):
                for _ in range(tasks):
                    users_for_market[key].append(user)

            # _tasks should match _users in size
            _tasks = tasks_for_market[key]
            _users = users_for_market[key]
            for u, t in zip(_users, _tasks):
                print(u, '-->', t.id)

                a = TaskAgenda.objects.filter(
                  user=u, campaign=c
                )

                if not a.exists():
                    a = TaskAgenda.objects.create(
                      user=u, campaign=c
                    )
                else:
                    a = a[0]

                serialized_t = ObjectID.objects.get_or_create(
                  typeName='DirectAssessmentTask',
                  primaryID=t.id
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
