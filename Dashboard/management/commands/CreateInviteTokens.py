"""
Appraise evaluation framework
"""
# pylint: disable=W0611
from csv import DictWriter
from datetime import datetime
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
        parser.add_argument(
          '--output-file', type=str, default=None,
          help='Output file path'
        )

    def handle(self, *args, **options):
        group_name = options['group_name']
        number_of_tokens = options['number_of_tokens']
        create_group = options['create_group']
        output_file = options['output_file']

        _msg = '\n[{0}]\n\n'.format(path.basename(__file__))
        self.stdout.write(_msg)

        self.stdout.write('      group_name: {0}'.format(group_name))
        self.stdout.write('number_of_tokens: {0}'.format(number_of_tokens))
        self.stdout.write('    create_group: {0}'.format(create_group))
        self.stdout.write('     output_file: {0}'.format(output_file))

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

        group_password = '{0}{1}'.format(
          group_name[:2].upper(),
          md5(group_name.encode('utf-8')).hexdigest()[:8]
        )

        date_created = datetime.utcnow().isoformat()

        self.stdout.write('      group name: {0}'.format(group_name))
        self.stdout.write('  group password: {0}'.format(group_password))
        self.stdout.write('    date created: {0}\n\n'.format(date_created))

        tokens = []
        group = Group.objects.filter(name=group_name).get()
        for _ in range(number_of_tokens):
            new_token = UserInviteToken()
            new_token.group = group
            new_token.save()

            tokens.append(new_token.token)
            self.stdout.write('           token: {0}'.format(new_token.token))

        if output_file is not None:
            with open(output_file, mode='a', encoding='utf8') as out_file:
                csv_writer = DictWriter(out_file, ('key', 'value'))

                csv_rows = [
                  {'key': 'group_name', 'value': group_name},
                  {'key': 'group_password', 'value': group_password},
                  {'key': 'number_of_tokens', 'value': number_of_tokens},
                  {'key': 'date_created', 'value': date_created}
                ]

                for token in tokens:
                    csv_rows.append({'key': 'token', 'value': token})

                csv_writer.writeheader()
                csv_writer.writerows(csv_rows)

        self.stdout.write('\n[DONE]\n\n')
