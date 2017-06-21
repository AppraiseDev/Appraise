"""
Appraise evaluation framework
"""
# pylint: disable=W0611
from os import path
from django.contrib.auth.models import Group, User

from django.core.management.base import BaseCommand, CommandError
from django.db.utils import OperationalError, ProgrammingError
from Campaign.models import Campaign, CampaignTeam, TrustedUser


INFO_MSG = 'INFO: '
WARNING_MSG = 'WARN: '

# pylint: disable=C0111,C0330,E1101
class Command(BaseCommand):
    help = 'Updates object instances required for Campaign app'

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):
        _msg = '\n[{0}]\n\n'.format(path.basename(__file__))
        self.stdout.write(_msg)
        self.stdout.write('\n[INIT]\n\n')

        # Find super user
        superusers = User.objects.filter(is_superuser=True)
        if not superusers.exists():
            _msg = 'Failure to identify superuser'
            self.stdout.write(_msg)
            return

        # Ensure that NewsTask campaign team exists.
        news_task_name = 'NewsTask'
        news_task_annotations = 1200
        news_task_hours = 600
        team = CampaignTeam.objects.filter(teamName=news_task_name)
        if not team.exists():
            new_team = CampaignTeam(
              teamName=news_task_name,
              owner=superusers[0],
              requiredAnnotations=news_task_annotations,
              requiredHours=news_task_hours,
              createdBy=superusers[0]
            )
            new_team.save()
            team = new_team

        else:
            team = team[0]

        team.requiredAnnotations = news_task_annotations
        team.requiredHours = news_task_hours
        team.save()

        # Auto-populate team members based on known groups.
        news_task_groups = [
          'USFD', 'Tilde', 'Tartu-Riga-Zurich', 'UFAL', 'Helsinki', 'Aalto',
          'HZSK-apertium', 'LIMSI-CNRS', 'LIUM', 'PROMT', 'uedin', 'RWTH',
          'HunterCollege', 'QT21', 'NRC', 'AFRL', 'TALP-UPC', 'LMU-Munich',
          'XMU', 'CASICT', 'URMT', 'KIT', 'UU', 'FBK', 'JHU'
        ]

        # Initially, remove everybody from the members relationship.
        team.members.clear()

        # Then, add associated group members to this campaign team.
        for group_name in news_task_groups:
            group = Group.objects.filter(name=group_name).first()
            if group:
                for user in group.user_set.all():
                    team.members.add(user)
                    _msg = 'Updated team {0}, adding user {1}'.format(
                      team.teamName, user.username
                    )
                    self.stdout.write(_msg)

        # Finally, add any super users who are part of all campaign teams.
        for user in superusers:
            team.members.add(user)
            _msg = 'Updated team {0}, adding super user {1}'.format(
              team.teamName, user.username
            )
            self.stdout.write(_msg)
        team.save()

        MINIMUM_RESULTS_UNTIL_TRUSTED = 300
        from EvalData.models import DirectAssessmentResult
        for u in User.objects.all():
            for c in Campaign.objects.all():
                if TrustedUser.objects.filter(user=u, campaign=c).exists():
                    continue

                completed_hits = DirectAssessmentResult.completed_results_for_user_and_campaign(u, c)
                if completed_hits >= MINIMUM_RESULTS_UNTIL_TRUSTED:
                    TrustedUser.objects.create(
                      user=u, campaign=c
                    )
                    _msg = 'Created trusted user {0} for campaign {1}'.format(
                      u.username, c.campaignName
                    )
                    self.stdout.write(_msg)

        # Ensure that MetricsTask campaign team exists.
        metrics_task_name = 'MetricsTask'
        metrics_task_annotations = 48
        metrics_task_hours = 24
        team = CampaignTeam.objects.filter(teamName=metrics_task_name)
        if not team.exists():
            new_team = CampaignTeam(
              teamName=metrics_task_name,
              owner=superusers[0],
              requiredAnnotations=metrics_task_annotations,
              requiredHours=metrics_task_hours,
              createdBy=superusers[0]
            )
            new_team.save()
            team = new_team

        else:
            team = team[0]

        team.requiredAnnotations = metrics_task_annotations
        team.requiredHours = metrics_task_hours
        team.save()

        # Ensure that all users are trusted for MetricsTask.
        c = Campaign.objects.filter(campaignName='MetricsTask')
        if c.exists():
            c = c[0]
            for u in User.objects.all():
                trusted_used = TrustedUser.objects.filter(user=u, campaign=c)
                if not trusted_used.exists():
                    TrustedUser.objects.create(
                      user=u, campaign=c
                    )
                    _msg = 'Created trusted user {0} for campaign {1}'.format(
                      u.username, c.campaignName
                    )
                    self.stdout.write(_msg)

        # Ensure that MetricsTask campaign team exists.
        multimodal_task_name = 'MultiModalTask'
        multimodal_task_annotations = 100
        multimodal_task_hours = 50
        team = CampaignTeam.objects.filter(teamName=multimodal_task_name)
        if not team.exists():
            new_team = CampaignTeam(
              teamName=multimodal_task_name,
              owner=superusers[0],
              requiredAnnotations=multimodal_task_annotations,
              requiredHours=multimodal_task_hours,
              createdBy=superusers[0]
            )
            new_team.save()
            team = new_team

        else:
            team = team[0]

        team.requiredAnnotations = multimodal_task_annotations
        team.requiredHours = multimodal_task_hours
        team.save()

        # Ensure that all users are trusted for MultiModalTask.
        c = Campaign.objects.filter(campaignName='MultiModalTask')
        if c.exists():
            c = c[0]
            for u in User.objects.all():
                trusted_used = TrustedUser.objects.filter(user=u, campaign=c)
                if not trusted_used.exists():
                    TrustedUser.objects.create(
                      user=u, campaign=c
                    )
                    _msg = 'Created trusted user {0} for campaign {1}'.format(
                      u.username, c.campaignName
                    )
                    self.stdout.write(_msg)

        self.stdout.write('\n[DONE]\n\n')
