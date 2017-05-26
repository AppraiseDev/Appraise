"""
Appraise evaluation framework
"""
# pylint: disable=W0611
from hashlib import md5
from os import path
from traceback import format_exc
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand, CommandError
from Dashboard.models import UserInviteToken


INFO_MSG = 'INFO: '
WARNING_MSG = 'WARN: '

# pylint: disable=C0111
class Command(BaseCommand):
    help = 'Creates invite tokens for the given group'

    # pylint: disable=C0330
    def add_arguments(self, parser):
        parser.add_argument(
          'group_name', type=str,
          help='Name of the group the invite tokens belong to'
        )
        parser.add_argument(
          'number_of_tokens', type=int,
          help='Number of tokens to create'
        )
        parser.add_argument(
          '--create-group', type=bool, default=False,
          help='Create group if it does not exist yet'
        )

    def handle(self, *args, **options):
        group_name = options['group_name']
        number_of_tokens = options['number_of_tokens']
        create_group = options['create_group']

        _msg = '\n[{0}]\n\n'.format(path.basename(__file__))
        self.stdout.write(_msg)

        self.stdout.write('      group_name: {0}'.format(group_name))
        self.stdout.write('number_of_tokens: {0}'.format(number_of_tokens))
        self.stdout.write('    create_group: {0}'.format(create_group))

        self.stdout.write('\n[INIT]\n\n')

        if not Group.objects.filter(name=group_name).exists():
            if not create_group:
                _msg = '{0}Specified group does not exist: {1}\n'.format(
                  WARNING_MSG, group_name
                )
                self.stdout.write(_msg)
                self.stdout.write('      You can use --create-group to create it.')
                self.stdout.write('\n[FAIL]\n\n')
                return

            else:
                new_group = Group(name=group_name)
                new_group.save()

        if number_of_tokens < 1 or number_of_tokens > 50:
            _msg = '{0}Specified number of tokens is insane: {1}'.format(
              WARNING_MSG, number_of_tokens
            )
            self.stdout.write(_msg)
            self.stdout.write('      You can request creation of up to 50 tokens.')
            self.stdout.write('\n[FAIL]\n\n')
            return

        tokens = []
        group = Group.objects.filter(name=group_name).get()
        for _ in range(number_of_tokens):
            new_token = UserInviteToken()
            new_token.group = group
            new_token.save()

            tokens.append(new_token.token)
            self.stdout.write(new_token.token)

        group_password = '{0}{1}'.format(
          group_name[:2].upper(),
          md5(group_name.encode('utf-8')).hexdigest()[:8]
        )

        self.stdout.write('\n      group name: {0}'.format(group_name))
        self.stdout.write('  group password: {0}\n\n'.format(group_password))

        self.stdout.write('\n[DONE]\n\n')
