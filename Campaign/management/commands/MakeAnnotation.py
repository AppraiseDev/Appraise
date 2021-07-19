"""
Appraise evaluation framework

See LICENSE for usage details
"""
from datetime import datetime, timedelta

import django

from django.core.management.base import BaseCommand, CommandError
from django.test import Client
from django.template.response import SimpleTemplateResponse

from Campaign.utils import CAMPAIGN_TASK_TYPES
from Dashboard.views import TASK_DEFINITIONS




# pylint: disable=C0111,C0330,E1101
class Command(BaseCommand):
    help = 'Make a testing annotation from a command line'

    def add_arguments(self, parser):
        parser.add_argument(
            'user',
            type=str,
            help='User name and password separated by a semicolon (:)',
        )

        _valid_task_types = ', '.join(CAMPAIGN_TASK_TYPES.keys())
        parser.add_argument(
            'campaign_type',
            metavar='campaign-type',
            type=str,
            help='Campaign type: {0}'.format(_valid_task_types),
        )

        parser.add_argument(
            'score',
            metavar='score(s)',
            type=str,
            help='Score(s) that should be assigned, delimited by a semicolon ' \
                 'if multiple scores are needed for the task type'
        )

    def handle(self, *args, **options):
        # Get username and password from options
        username, password = options['user'].replace(':', ' ').split(' ')

        # Get score(s)
        _scores = options['score'].replace(':', ' ').split(' ')
        scores = [int(score) for score in _scores]

        # Needed to get the response context
        # http://jazstudios.blogspot.com/2011/01/django-testing-views.html
        self.stdout.write("Setting up the client")
        django.test.utils.setup_test_environment()

        # Create a client with a server name that is already in ALLOWED_HOSTS
        client = Client(SERVER_NAME='localhost')
        session = client.session
        session.save()

        is_logged_in = client.login(username=username, password=password)
        if not is_logged_in:
            raise CommandError('Incorrect username or password.')
        self.stdout.write('User "{0}" has successfully signed in'.format(username))

        campaign_type = options['campaign_type']
        if campaign_type not in CAMPAIGN_TASK_TYPES:
            raise CommandError('Task type "{0}" does not exist'.format(campaign_type))
        self.stdout.write('Task type: {0!r}'.format(campaign_type))
        campaign_url = _get_task_url(campaign_type)

        task_url = 'http://localhost:8000/{}/'.format(campaign_url)
        self.stdout.write('Task URL: {0!r}'.format(task_url))

        response = client.get(task_url)
        if response.status_code == 400:
            raise CommandError('Incorrect campaign URL for user "{}"'.format(username))
        # print(response)
        # print(response.context.keys())

        # Each task has different context, so the POST request needs to be
        # built separately for each task type
        if campaign_type == 'Direct':
            if len(scores) != 1:
                raise ValueError('"Direct" task requires exactly 1 score.')

            data = {
                'score': scores[0],
                'item_id': response.context['item_id'],
                'task_id': response.context['task_id'],
                'start_timestamp': (datetime.now() - timedelta(minutes=5)).timestamp(),
                'end_timestamp': datetime.now().timestamp(),
            }
            self.stdout.write('Created data: {0}'.format(data))
            _response = client.post(task_url, data, follow=True)

            if _response.status_code != 200:
                raise CommandError('Unsuccesful annotation, status code != 200')

            self.stdout.write(
                'Successfully annotated item {}/{} with score {} for user {}'.format(
                    response.context['item_id'],
                    response.context['task_id'],
                    scores[0],
                    username
                )
            )

        else:
            raise CommandError(
                'Task type "{}" is not yet supported in this script yet'.format(
                    campaign_type
                )
            )

        self.stdout.write('Done')


def _get_task_url(task_type):
    """Gets task URL based on the campaign task type name."""
    if task_type not in CAMPAIGN_TASK_TYPES:
        return None
    task_cls = CAMPAIGN_TASK_TYPES[task_type]
    task_url = [tup[3] for tup in TASK_DEFINITIONS if tup[1] == task_cls]
    if len(task_url) != 1:
        return None
    return task_url[0]
