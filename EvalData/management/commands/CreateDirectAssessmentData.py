from django.core.management.base import BaseCommand, CommandError

class Command(BaseCommand):
    help = 'Creates JSON file containing DirectAssessmentTask data'

    # pylint: disable=C0330
    def add_arguments(self, parser):
        parser.add_argument(
          'batch_size', type=int, help='Total batch size'
        )
        parser.add_argument(
          'source_language', type=str, help='Source language code'
        )
        parser.add_argument(
          'target_language', type=str, help='Target language code'
        )
        parser.add_argument(
          'source_text', type=str, help='Path to source text file'
        )
        parser.add_argument(
          'reference_text', type=str, help='Path to reference text file'
        )
        parser.add_argument(
          'system_text', type=str, help='Path to system text file'
        )

        parser.add_argument(
          '--redundant', type=int, required=False, help='Number of redundant items'
        )
        parser.add_argument(
          '--refs', type=int, required=False, help='Number of reference items'
        )
        parser.add_argument(
          '--bad-refs', type=int, required=False, help='Number of bad reference items'
        )
        parser.add_argument(
          '--random-seed', type=int, required=False, help='Random generator seed value'
        )
        parser.add_argument(
          '--randomize', required=False, action='store_true', help='Randomize extracted work items'
        )


    def handle(self, *args, **options):
        self.stdout.write("I would do something now...")
        self.stdout.write(options['source_text'])
        self.stdout.write(options['reference_text'])
        self.stdout.write(options['systems_text'])
