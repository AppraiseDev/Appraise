"""
Appraise evaluation framework
"""
# pylint: disable=W0611
from os import path
from django.contrib.auth.models import Group, User

from django.core.management.base import BaseCommand, CommandError
from django.db.utils import OperationalError, ProgrammingError
from Campaign.models import Campaign, CampaignTeam


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
          'XMU', 'CASICT', 'URMT', 'KIT', 'UU'
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

        self.stdout.write('\n[DONE]\n\n')
