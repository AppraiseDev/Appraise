from hashlib import md5

from django.contrib.auth.models import Group
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.core.management.base import CommandError

from Campaign.models import Campaign
from Campaign.models import CampaignTeam
from EvalData.models import Market
from EvalData.models import Metadata

EX_LANGUAGES = ('ces', 'deu', 'fra')

XE_LANGUAGES = ()

XY_LANGUAGES = ()

CAMPAIGN_NAME = 'MMT18Task1v2'
CAMPAIGN_KEY = 'MMT18Task1v2'
CAMPAIGN_NO = 86
ANNOTATORS = {
    'eng-ces': 36,
    'eng-deu': 34,
    'eng-fra': 30,
}
TASKS = {
    'eng-ces': ANNOTATORS['eng-ces'],
    'eng-deu': ANNOTATORS['eng-deu'],
    'eng-fra': ANNOTATORS['eng-fra'],
}
REDUNDANCY = 1

# pylint: disable=C0111,C0330,E1101
class Command(BaseCommand):
    help = 'Initialises campaign MMT18 Task #1 v2'

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
                domainName='WMT18',
            )

            if not _ex_market.exists():
                _ex_market = Market.objects.get_or_create(
                    sourceLanguageCode='eng',
                    targetLanguageCode=code,
                    domainName='WMT18',
                    createdBy=superusers[0],
                )
                _ex_market = _ex_market[0]

            else:
                _ex_market = _ex_market.first()

            _ex_meta = Metadata.objects.filter(
                market=_ex_market,
                corpusName='WMT18',
                versionInfo='1.0',
                source='official',
            )

            if not _ex_meta.exists():
                _ex_meta = Metadata.objects.get_or_create(
                    market=_ex_market,
                    corpusName='WMT18',
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
                domainName='WMT18',
            )

            if not _xe_market.exists():
                _xe_market = Market.objects.get_or_create(
                    sourceLanguageCode=code,
                    targetLanguageCode='eng',
                    domainName='WMT18',
                    createdBy=superusers[0],
                )
                _xe_market = _xe_market[0]

            else:
                _xe_market = _xe_market.first()

            _xe_meta = Metadata.objects.filter(
                market=_xe_market,
                corpusName='WMT18',
                versionInfo='1.0',
                source='official',
            )

            if not _xe_meta.exists():
                _xe_meta = Metadata.objects.get_or_create(
                    market=_xe_market,
                    corpusName='WMT18',
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
                domainName='WMT18',
            )

            if not _xy_market.exists():
                _xy_market = Market.objects.get_or_create(
                    sourceLanguageCode=source,
                    targetLanguageCode=target,
                    domainName='WMT18',
                    createdBy=superusers[0],
                )
                _xy_market = _xy_market[0]

            else:
                _xy_market = _xy_market.first()

            _xy_meta = Metadata.objects.filter(
                market=_xy_market,
                corpusName='WMT18',
                versionInfo='1.0',
                source='official',
            )

            if not _xy_meta.exists():
                _xy_meta = Metadata.objects.get_or_create(
                    market=_xy_market,
                    corpusName='WMT18',
                    versionInfo='1.0',
                    source='official',
                    createdBy=superusers[0],
                )
                _xy_meta = _xy_meta[0]

            else:
                _xy_meta = _xy_meta.first()

        _msg = 'Processed Market/Metadata instances'
        self.stdout.write(_msg)

        # Create CampaignTeam instance
        _cteam = CampaignTeam.objects.get_or_create(
            teamName=CAMPAIGN_NAME,
            owner=superusers[0],
            requiredAnnotations=min(100 * sum(TASKS.values()) * REDUNDANCY, 32767),
            requiredHours=(sum(TASKS.values()) * REDUNDANCY) / 2,
            createdBy=superusers[0],
        )
        _cteam[0].members.add(superusers[0])
        _cteam[0].save()
        campaign_team_object = _cteam[0]

        _msg = 'Processed CampaignTeam instance'
        self.stdout.write(_msg)

        # Create User accounts
        for code in EX_LANGUAGES:
            # EX
            for user_id in range(ANNOTATORS['eng-' + code]):
                username = '{0}{1}{2:02x}{3:02d}'.format(
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

                print(username, secret)

        for code in XE_LANGUAGES:
            # XE
            for user_id in range(ANNOTATORS[code + '-eng']):
                username = '{0}{1}{2:02x}{3:02d}'.format(
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

                print(username, secret)

        for source, target in XY_LANGUAGES:
            # XY
            for user_id in range(ANNOTATORS[source + '-' + target]):
                username = '{0}{1}{2:02x}{3:02d}'.format(
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

                print(username, secret)

        _msg = 'Processed User instances'
        self.stdout.write(_msg)

        # Add user instances as CampaignTeam members
        for code in EX_LANGUAGES:
            # EX
            for user_id in range(ANNOTATORS['eng-' + code]):
                username = '{0}{1}{2:02x}{3:02d}'.format(
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
            # XE
            for user_id in range(ANNOTATORS[code + '-eng']):
                username = '{0}{1}{2:02x}{3:02d}'.format(
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
            # XY
            for user_id in range(ANNOTATORS[source + '-' + target]):
                username = '{0}{1}{2:02x}{3:02d}'.format(
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
            MultiModalAssessmentTask,
            TaskAgenda,
            ObjectID,
        )
        from collections import defaultdict

        tasks = MultiModalAssessmentTask.objects.filter(campaign=c, activated=True)

        # Assignment scheme:
        #
        # T1 U1
        # ...
        # T6 U6
        #
        # To assign this, we don't need to duplicate Ts below.
        tasks_for_market = defaultdict(list)
        users_for_market = defaultdict(list)
        for task in tasks.order_by('id'):
            market = '{0}{1:02x}'.format(
                task.marketName().replace('_', '')[:6], CAMPAIGN_NO
            )
            for i in range(1):
                tasks_for_market[market].append(task)

        for key in tasks_for_market:
            users = User.objects.filter(username__startswith=key)

            for user in users.order_by('id'):
                users_for_market[key].append(user)

            # _tasks has size X due to not duplicating tasks above
            # _users has size X , so we need one copiy to match
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
                    typeName='MultiModalAssessmentTask', primaryID=t.id
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
