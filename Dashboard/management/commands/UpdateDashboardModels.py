"""
Appraise evaluation framework

See LICENSE for usage details
"""
# pylint: disable=C0103,W0611
from os.path import basename

from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
from django.core.management.base import CommandError
from django.db.utils import OperationalError
from django.db.utils import ProgrammingError

from Dashboard.models import LANGUAGE_CODES_AND_NAMES

# pylint: disable=import-error


INFO_MSG = 'INFO: '
WARNING_MSG = 'WARN: '

# pylint: disable=C0111,C0330
class Command(BaseCommand):
    help = 'Updates object instances required for Dashboard app'

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):
        del args  # Unused.
        del options  # Unused.

        _msg = '\n[{0}]\n\n'.format(basename(__file__))
        self.stdout.write(_msg)
        self.stdout.write('\n[INIT]\n\n')

        # Ensure that all languages have a corresponding group.
        for code in LANGUAGE_CODES_AND_NAMES:
            try:
                if not Group.objects.filter(name=code).exists():
                    new_language_group = Group(name=code)
                    new_language_group.save()

            except (OperationalError, ProgrammingError):
                _msg = 'Failure processing language code={0}'.format(code)

            finally:
                _msg = 'Success processing language code={0}'.format(code)

            self.stdout.write(_msg)

        self.stdout.write('\n[DONE]\n\n')
