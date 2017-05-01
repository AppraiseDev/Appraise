from django.core.management.base import BaseCommand, CommandError

class Command(BaseCommand):
    help = 'Validates campaign data batches'

    def handle(self, *args, **options):
        self.stdout.write("I would do something now...")
