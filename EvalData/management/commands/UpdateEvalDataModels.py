"""
Appraise evaluation framework
"""
# pylint: disable=W0611
from os import path
from django.contrib.auth.models import User

from django.core.management.base import BaseCommand, CommandError
from django.db.utils import OperationalError, ProgrammingError
from EvalData.models import Market, Metadata, DirectAssessmentTask, \
  DirectAssessmentResult


INFO_MSG = 'INFO: '
WARNING_MSG = 'WARN: '

# pylint: disable=C0111,C0330
class Command(BaseCommand):
    help = 'Updates object instances required for EvalData app'

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):
        _msg = '\n[{0}]\n\n'.format(path.basename(__file__))
        self.stdout.write(_msg)
        self.stdout.write('\n[INIT]\n\n')

        # News Task language pairs
        news_task_languages = (
          'ces', 'deu', 'fin', 'lav', 'rus', 'trk', 'zho'
        )
        news_task_pairs = [(x, 'eng') for x in news_task_languages] \
          + [('eng', x) for x in news_task_languages]

        # Find super user
        superusers = User.objects.filter(is_superuser=True)
        if not superusers.exists():
            _msg = 'Failure to identify superuser'
            self.stdout.write(_msg)
            return

        # Ensure that all Market and Metadata instances exist.
        for source, target in news_task_pairs:
            try:
                # Create NewsTask Market instance, if needed
                market = Market.objects.filter(
                  sourceLanguageCode=source,
                  targetLanguageCode=target,
                  domainName='NewsTask'
                )

                if not market.exists():
                    new_market = Market(
                      sourceLanguageCode=source,
                      targetLanguageCode=target,
                      domainName='NewsTask',
                      createdBy=superusers[0]
                    )
                    new_market.save()
                    market = new_market

                else:
                    market = market[0]

                metadata = Metadata.objects.filter(market=market)

                if not metadata.exists():
                    new_metadata = Metadata(
                      market=market,
                      corpusName='NewsTest2017',
                      versionInfo='1.0',
                      source='official',
                      createdBy=superusers[0]
                    )
                    new_metadata.save()

            except (OperationalError, ProgrammingError):
                _msg = 'Failure processing source={0}, target={1}'.format(
                  source, target
                )

            finally:
                _msg = 'Success processing source={0}, target={1}'.format(
                  source, target
                )

            self.stdout.write(_msg)

        # Ensure that all DirectAssessmentResults link back to tasks.
        tasks = DirectAssessmentTask.objects.filter(
          activated=True,
          completed=False
        )

        fixed_results = 0
        completed_results = 0
        for task in tasks:
            for item in task.items.all():
                results = DirectAssessmentResult.objects.filter(
                  item=item
                )

                for result in results:
                    if result.task != task:
                        result.task = task
                        result.save()
                        fixed_results += 1
                    
                    if not result.completed:
                        result.complete()
                        result.save()
                        completed_results += 1

        _msg = 'Fixed task mappings for {0} results'.format(fixed_results)
        self.stdout.write(_msg)

        _msg = 'Completed {0} results'.format(completed_results)
        self.stdout.write(_msg)

        self.stdout.write('\n[DONE]\n\n')
