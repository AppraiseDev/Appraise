"""
Appraise evaluation framework
"""
from os.path import basename

# pylint: disable=E0401,W0611
from django.core.management.base import (
    BaseCommand,
    CommandError,
)

from EvalData.models import DirectAssessmentResult, MultiModalAssessmentResult


INFO_MSG = 'INFO: '
WARNING_MSG = 'WARN: '

# pylint: disable=C0111,C0330
class Command(BaseCommand):
    help = 'Dumps all DirectAssessmentResult and MultiModalAssessmentResult instances'

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):
        del args  # Unused.
        del options  # Unused.

        _msg = '\n[{0}]\n\n'.format(basename(__file__))
        self.stdout.write(_msg)
        self.stdout.write('\n[INIT]\n\n')

        DirectAssessmentResult.dump_all_results_to_csv_file(
            'DirectAssessmentResults.csv')
        MultiModalAssessmentResult.dump_all_results_to_csv_file(
            'MultiModalAssessmentResults.csv')

        self.stdout.write('\n[DONE]\n\n')
