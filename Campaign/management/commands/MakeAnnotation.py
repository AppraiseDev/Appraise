"""
Appraise evaluation framework

See LICENSE for usage details
"""

from datetime import datetime
from datetime import timedelta
import json

import django
from django.core.management.base import BaseCommand
from django.core.management.base import CommandError
from django.test import Client

from Campaign.utils import CAMPAIGN_TASK_TYPES
from Dashboard.views import TASK_DEFINITIONS


# pylint: disable=C0111,C0330,E1101
class Command(BaseCommand):
    help = "Make a testing annotation from a command line"

    def add_arguments(self, parser):
        parser.add_argument(
            "user",
            type=str,
            help="User name and password separated by a semicolon (:)",
        )

        _valid_task_types = ", ".join(CAMPAIGN_TASK_TYPES.keys())
        parser.add_argument(
            "campaign_type",
            metavar="campaign-type",
            type=str,
            help=f"Campaign type: {_valid_task_types}",
        )

        parser.add_argument(
            "score",
            metavar="score(s)",
            type=str,
            help="Score(s) that should be assigned, delimited by a semicolon "
            "if multiple scores are needed for the task type",
        )

        parser.add_argument(
            "--mqm",
            metavar="mqm(s)",
            type=str,
            nargs="+",
            help="JSON MQM annotations that should be assigned",
            default=["[]"],
        )

        parser.add_argument(
            "--source-error",
            metavar="TEXT",
            type=str,
            help="Source error(s) that should be assigned",
        )
        parser.add_argument(
            "--target-errors",
            metavar="TEXT",
            type=str,
            help="Error comment(s) that should be assigned, delimited by a semicolon "
            "if multiple comments are allowed for the task type",
        )

    def handle(self, *args, **options):
        # Get username and password from options
        username, password = options["user"].replace(":", " ").split(" ")

        # Get score(s)
        _scores = options["score"].replace(":", " ").split(" ")
        scores = [int(score) for score in _scores]

        # Get mqm(s)
        mqms = [json.loads(mqm) for mqm in options["mqm"]]

        # Get error comment(s)
        source_error = options.get("source_error", None)
        target_errors = []
        if options["target_errors"] is not None:
            target_errors = options["target_errors"].replace(":", " ").split(" ")

        # Needed to get the response context
        # http://jazstudios.blogspot.com/2011/01/django-testing-views.html
        self.stdout.write("Setting up the client")
        django.test.utils.setup_test_environment()

        # Create a client with a server name that is already in ALLOWED_HOSTS
        client = Client(SERVER_NAME="127.0.0.1")
        session = client.session
        session.save()

        is_logged_in = client.login(username=username, password=password)
        if not is_logged_in:
            raise CommandError("Incorrect username or password.")
        self.stdout.write(f"User {username!r} has successfully signed in")

        campaign_type = options["campaign_type"]
        if campaign_type not in CAMPAIGN_TASK_TYPES:
            raise CommandError(f'Task type "{campaign_type}" does not exist')
        self.stdout.write(f"Task type: {campaign_type!r}")
        campaign_url = _get_task_url(campaign_type)

        task_url = f"http://127.0.0.1:8000/{campaign_url}/"
        self.stdout.write(f"Task URL: {task_url!r}")

        try:
            response = client.get(task_url)
        except:
            raise CommandError(f"Invalid campaign URL for user {username!r}")
        if response.status_code == 400:
            raise CommandError(f"Invalid campaign URL for user {username!r}")

        # No context means no more items
        if response.context is None:
            self.stdout.write(
                f'Unsuccesful annotation: user "{username}" does not have more items'
            )
            exit()

        if options["verbosity"] > 1:
            self.stdout.write(f"Available context keys: {response.context.keys()}")

        # Each task has different context, so the POST request needs to be
        # built separately for each task type
        data = None
        msg_info = None

        ##################################################################
        if campaign_type == "Direct":
            if len(scores) != 1:
                raise ValueError('Task "Direct" requires exactly 1 score')

            data = {
                "score": scores[0],
                "item_id": response.context["item_id"],
                "task_id": response.context["task_id"],
                "start_timestamp": (datetime.now() - timedelta(minutes=5)).timestamp(),
                "end_timestamp": datetime.now().timestamp(),
            }

            msg_info = "item {}/{} with score {} for user {}".format(
                response.context["item_id"],
                response.context["task_id"],
                scores[0],
                username,
            )

        ##################################################################
        elif campaign_type == "Pairwise":
            if len(scores) != 2:
                raise ValueError('Task "Pairwise" requires exactly 2 scores')

            data = {
                "score": scores[0],
                "item_id": response.context["item_id"],
                "task_id": response.context["task_id"],
                "start_timestamp": (datetime.now() - timedelta(minutes=5)).timestamp(),
                "end_timestamp": datetime.now().timestamp(),
            }

            if source_error is not None:
                data["source_error"] = source_error

            if len(target_errors) > 0:
                data["error1"] = target_errors[0]

            if response.context["candidate2_text"] is not None:
                data["score2"] = scores[1]
                if len(target_errors) > 1:
                    data["error2"] = target_errors[1]

            msg_info = "item {}/{} with score(s) {}".format(
                response.context["item_id"], response.context["task_id"], scores[0]
            )
            if response.context["candidate2_text"] is not None:
                msg_info += f", {scores[1]}"

            msg_info += f" for user {username}"

        ##################################################################
        elif campaign_type == "PairwiseDocument":
            if len(scores) != 2:
                raise ValueError('Task "PairwiseDocument" requires exactly 2 scores')

            data = {
                "score1": scores[0],
                "score2": scores[1],
                "item_id": response.context["item_id"],
                "task_id": response.context["task_id"],
                "document_id": response.context["document_id"],
                "start_timestamp": (datetime.now() - timedelta(minutes=5)).timestamp(),
                "end_timestamp": datetime.now().timestamp(),
            }

            msg_info = "item {}/{}/{} with score(s) {}, {}".format(
                response.context["item_id"],
                response.context["task_id"],
                response.context["document_id"],
                scores[0],
                scores[1],
            )

            msg_info += f" for user {username}"

        ##################################################################
        elif campaign_type == "Document":
            if len(scores) != 1:
                raise ValueError('Task "Document" requires exactly 1 score')

            data = {
                "score": scores[0],
                "mqm": mqms[0],
                "item_id": response.context["item_id"],
                "document_id": response.context["document_id"],
                "task_id": response.context["task_id"],
                "start_timestamp": (datetime.now() - timedelta(minutes=5)).timestamp(),
                "end_timestamp": datetime.now().timestamp(),
            }

            msg_info = "item {}/{}/{} with score {} and mqm {} for user {}".format(
                response.context["item_id"],
                response.context["task_id"],
                response.context["document_id"],
                scores[0],
                mqms[0],
                username,
            )

        ##################################################################
        elif campaign_type == "Data":
            if len(scores) != 2:
                raise ValueError(
                    'Task "Data" requires exactly 1 score (0-100) and 1 label (1-4)'
                )

            data = {
                "score": scores[0],
                "rank": scores[1],
                "item_id": response.context["item_id"],
                "task_id": response.context["task_id"],
                "start_timestamp": (datetime.now() - timedelta(minutes=5)).timestamp(),
                "end_timestamp": datetime.now().timestamp(),
            }

            msg_info = "item {}/{} with score {} and label {} for user {}".format(
                response.context["item_id"],
                response.context["task_id"],
                scores[0],
                scores[1],
                username,
            )

        ##################################################################
        else:
            raise CommandError(
                f'Task type "{campaign_type}" is not yet supported in this script yet'
            )

        # Final call
        self.stdout.write(f"Created data: {data}")
        response = client.post(task_url, data, follow=True)

        if response.status_code != 200:
            raise CommandError("Unsuccesful annotation, status code != 200")
        else:
            self.stdout.write("Successfully annotated " + msg_info)


def _get_task_url(task_type):
    """Gets task URL based on the campaign task type name."""
    if task_type not in CAMPAIGN_TASK_TYPES:
        return None
    task_cls = CAMPAIGN_TASK_TYPES[task_type]
    task_url = [tup[3] for tup in TASK_DEFINITIONS if tup[1] == task_cls]
    if len(task_url) != 1:
        return None
    return task_url[0]
