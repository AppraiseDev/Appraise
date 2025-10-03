"""
Appraise evaluation framework

See LICENSE for usage details
"""

# pylint: disable=E1101
from collections import defaultdict
from datetime import datetime
import json
from math import floor
from math import sqrt

from django.core.management.base import CommandError
from django.http import HttpResponse

from Appraise.utils import _get_logger, _compute_user_total_annotation_time
from Campaign.utils import _get_campaign_instance
from EvalData.models import DataAssessmentResult
from EvalData.models import DirectAssessmentDocumentResult
from EvalData.models import PairwiseAssessmentDocumentResult
from EvalData.models import PairwiseAssessmentResult
from EvalData.models import seconds_to_timedelta
from EvalData.models import TASK_DEFINITIONS
from EvalData.models import TaskAgenda
from EvalData.models.direct_assessment_document import DirectAssessmentDocumentTask

# pylint: disable=import-error

RESULT_TYPE_BY_CLASS_NAME = {tup[1].__name__: tup[2] for tup in TASK_DEFINITIONS}

LOGGER = _get_logger(name=__name__)


def campaign_status(request, campaign_name, sort_key=None):
    """
    Campaign status view with completion details.
    """
    LOGGER.info(
        'Rendering campaign status view for user "%s".',
        request.user.username or "Anonymous",
    )

    if "," in campaign_name:
        responses = [campaign_status(request, name, sort_key) for name in campaign_name.split(",")]
        if not all([response.headers["Content-Type"] == responses[0].headers["Content-Type"] for response in responses]):
            return HttpResponse(
                'ERROR: You are mixing unrelated campaigns (views.py:campaign_status).',
                content_type='text/plain',
            )
        else:
            return HttpResponse(
                "\n\n".join([response.content.decode('utf-8') for response in responses]),
                content_type=responses[0].headers["Content-Type"],
            )

    # Get Campaign instance for campaign name
    try:
        campaign = _get_campaign_instance(campaign_name)

    except CommandError:
        _msg = 'Failure to identify campaign {0}'.format(campaign_name)
        return HttpResponse(_msg, content_type='text/plain')

    try:
        campaign_opts = campaign.campaignOptions.lower().split(";")
        # may raise KeyError
        result_type = RESULT_TYPE_BY_CLASS_NAME[campaign.get_campaign_type()]
    except KeyError as exc:
        LOGGER.debug(
            f'Invalid campaign type {campaign.get_campaign_type()} for campaign {campaign.campaignName}'
        )
        LOGGER.error(exc)
        return HttpResponse(
            'Invalid campaign type for campaign {0}'.format(campaign.campaignName),
            content_type='text/plain',
        )

    # special handling for ESA
    if "esa" in campaign_opts:
        return campaign_status_esa(campaign)
    else:
        return campaign_status_plain(request, campaign, result_type, campaign_opts, sort_key)


def campaign_status_plain(request, campaign, result_type, campaign_opts, sort_key):
    _out = []
    for team in campaign.teams.all():
        for user in team.members.all():

            _data = result_type.objects.filter(
                createdBy=user, completed=True, task__campaign=campaign.id
            )
            is_mqm_or_esa = False

            # Exclude document scores in document-level tasks, because we want to keep
            # the numbers reported on the campaign status page consistent across
            # accounts, which usually include different numbers of document
            if (
                result_type is DirectAssessmentDocumentResult
                or result_type is PairwiseAssessmentDocumentResult
            ):
                _data = _data.exclude(item__isCompleteDocument=True)
            # Contrastive tasks use different field names for target segments/scores
            if (
                result_type is PairwiseAssessmentResult
                or result_type is PairwiseAssessmentDocumentResult
            ):
                _data = _data.values_list(
                    'start_time',
                    'end_time',
                    'score1',
                    'item__itemID',
                    'item__target1ID',
                    'item__itemType',
                    'item__id',
                )
            elif "mqm" in campaign_opts:
                is_mqm_or_esa = True
                _data = _data.values_list(
                    'start_time',
                    'end_time',
                    'mqm',
                    'item__itemID',
                    'item__targetID',
                    'item__itemType',
                    'item__id',
                    'item__documentID',
                )
                # compute time override based on document times
                import collections

                _time_pairs = collections.defaultdict(list)
                for x in _data:
                    _time_pairs[x[7] + " ||| " + x[4]].append((x[0], x[1]))
                _time_pairs = [
                    (min([x[0] for x in doc_v]), max([x[1] for x in doc_v]))
                    for doc, doc_v in _time_pairs.items()
                ]
                _data = [
                    (x[0], x[1], -len(json.loads(x[2])), x[3], x[4], x[5], x[6])
                    for x in _data
                ]
            else:
                _data = _data.values_list(
                    'start_time',
                    'end_time',
                    'score',
                    'item__itemID',
                    'item__targetID',
                    'item__itemType',
                    'item__id',
                )

            _reliable = stat_reliable_testing(_data, campaign_opts, result_type)

            # Compute number of annotations
            _annotations = len(set([x[6] for x in _data]))

            _start_times = [x[0] for x in _data]
            _end_times = [x[1] for x in _data]

            # Compute first modified time
            _first_modified_raw = (
                seconds_to_timedelta(min(_start_times)) if _start_times else None
            )
            if _first_modified_raw:
                _date_modified = datetime(1970, 1, 1) + _first_modified_raw
                _first_modified = str(_date_modified).split('.')[0]
            else:
                _first_modified = 'Never'

            # Compute last modified time
            _last_modified_raw = (
                seconds_to_timedelta(max(_end_times)) if _end_times else None
            )
            if _last_modified_raw:
                _date_modified = datetime(1970, 1, 1) + _last_modified_raw
                _last_modified = str(_date_modified).split('.')[0]
            else:
                _last_modified = 'Never'

            # Compute total annotation time
            if is_mqm_or_esa and _first_modified_raw and _last_modified_raw:
                # for MQM and ESA compute the lower and upper annotation times
                # use only the end times
                _annotation_time_upper = (
                    _last_modified_raw - _first_modified_raw
                ).seconds
                _hours = int(floor(_annotation_time_upper / 3600))
                _minutes = int(floor((_annotation_time_upper % 3600) / 60))
                _annotation_time_upper = f'{_hours:0>2d}h{_minutes:0>2d}m'
            else:
                _time_pairs = list(zip(_start_times, _end_times))
                _annotation_time_upper = None
            _annotation_time = _compute_user_total_annotation_time(_time_pairs)

            # Format total annotation time
            if _annotation_time:
                _hours = int(floor(_annotation_time / 3600))
                _minutes = int(floor((_annotation_time % 3600) / 60))
                _annotation_time = f'{_hours:0>2d}h{_minutes:0>2d}m'
                # for MQM and ESA join it together
                if is_mqm_or_esa and _annotation_time_upper:
                    _annotation_time = f'{_annotation_time}--{_annotation_time_upper}'
            else:
                _annotation_time = 'n/a'

            _item = (
                user.username,
                user.is_active,
                _annotations,
                _first_modified,
                _last_modified,
                _annotation_time,
            )
            if request.user.is_staff:
                _item += (_reliable,)

            _out.append(_item)

    _out.sort(key=lambda x: x[sort_key if sort_key else 2])

    _header = (
        'username',
        'active',
        'annotations',
        'first_modified',
        'last_modified',
        'annotation_time',
    )
    if request.user.is_staff:
        _header += ('random',)

    _txt = []
    # align everything with the same formatting
    for _row in [_header] + _out:
        _local_fmt = '|{0:>15}|{1:>6}|{2:>11}|{3:>20}|{4:>20}|{5:>15}|'
        if request.user.is_staff:
            _local_fmt += '{6:>10}|'

        _local_out = _local_fmt.format(*_row)
        _txt.append(_local_out)

    return HttpResponse(u'\n'.join(_txt), content_type='text/plain')


def campaign_status_esa(campaign) -> str:
    import collections
    out_str = """
    <meta charset="UTF-8">

    <style>
    table, tr, td, th {
        border: 1px solid black; border-collapse: collapse;
    }
    td, th {
        padding: 5px;
    }
    * {
    font-family: monospace;
    }
    </style>\n
    """
    out_str += f"<h1>{campaign.campaignName}</h1>\n"
    out_str += "<table>\n"
    out_str += """<tr>
<th>Username</th>
<th>Progress</th>
<th>First Modified</th>
<th>Last Modified</th>
<th style="cursor: pointer" title="Very coarse upper bound estimate between the last and the first interaction with the system.">Time (Coarse❔)</th>
<th style="cursor: pointer" title="Sum of times between any two interactions that are not longer than 10 minutes.">Time (Real❔)</th>
</tr>\n
""" 
    for team in campaign.teams.all():
        for user in team.members.all():
            if user.is_staff:
                continue
            out_str += "<tr>"

            # Get the task for this user even when there's no completed data
            task = None

            # First try to get the task from TaskAgenda
            agenda = TaskAgenda.objects.filter(user=user, campaign=campaign).first()
            if agenda:
                # Try to get an open or completed task from the agenda
                for serialized_task in agenda.serialized_open_tasks():
                    potential_task = serialized_task.get_object_instance()
                    if isinstance(potential_task, DirectAssessmentDocumentTask):
                        task = potential_task
                        break
                # If no open task, try completed tasks
                if not task:
                    for serialized_task in agenda._completed_tasks.all():
                        potential_task = serialized_task.get_object_instance()
                        if isinstance(potential_task, DirectAssessmentDocumentTask):
                            task = potential_task
                            break

            # Get the completed data for this user
            _data = DirectAssessmentDocumentResult.objects.filter(
                createdBy=user, completed=True, task__campaign=campaign.id
            )
            _data_uniq_len = len({(item.item.sourceID, item.item.targetID, item.item.itemType, item.item.id) for item in _data})

            # If no data, show 0 progress or show that no task is assigned
            if not _data:
                if task:
                    total_count = task.items.count()
                    out_str += f"<td>{user.username} 💤</td>"
                    out_str += f"<td>0/{total_count} (0%)</td>"
                else:
                    # No task assigned to this user
                    out_str += f"<td>{user.username} 💤</td>"
                    out_str += "<td>No task assigned</td>"
                out_str += "<td></td>"
                out_str += "<td></td>"
                out_str += "<td></td>"
                out_str += "<td></td>"

            # If we have data, show the progress
            else:
                if not task:
                    # Fallback to checking the first result's task for the task ID
                    task = DirectAssessmentDocumentTask.objects.filter(id=_data[0].task_id).first()
                if not task:
                    # Skip this user if we can't find the task
                    out_str += f"<td>{user.username} ❌</td>"
                    out_str += "<td>Task not found</td>"
                    out_str += "<td></td>"
                    out_str += "<td></td>"
                    out_str += "<td></td>"
                    out_str += "<td></td>"
                    out_str += "</tr>\n"
                    continue

                total_count = task.items.count()
                if total_count == _data_uniq_len:
                    out_str += f"<td>{user.username} ✅</td>"
                else:
                    out_str += f"<td>{user.username} 🛠️</td>"
                out_str += f"<td>{_data_uniq_len}/{total_count} ({_data_uniq_len / total_count:.0%})</td>"
                first_modified = min([x.start_time for x in _data])
                last_modified = max([x.end_time for x in _data])

                first_modified_str = str(datetime(1970, 1, 1) + seconds_to_timedelta(first_modified)).split('.')[0]
                last_modified_str = str(datetime(1970, 1, 1) + seconds_to_timedelta(last_modified)).split('.')[0]
                # remove seconds
                first_modified_str = ":".join(first_modified_str.split(":")[:-1])
                last_modified_str = ":".join(last_modified_str.split(":")[:-1])

                out_str += f"<td>{first_modified_str}</td>"
                out_str += f"<td>{last_modified_str}</td>"
                annotation_time_upper = last_modified - first_modified
                annotation_time_upper = f'{int(floor(annotation_time_upper / 3600)):0>2d}h {int(floor((annotation_time_upper % 3600) / 60)):0>2d}m'
                out_str += f"<td>{annotation_time_upper}</td>"

                # consider time that's in any action within 10 minutes
                times = sorted([item.start_time for item in _data] + [item.end_time for item in _data])
                annotation_time = sum([b-a for a, b in zip(times, times[1:]) if (b-a) < 10*60])
                annotation_time = f'{int(floor(annotation_time / 3600)):0>2d}h {int(floor((annotation_time % 3600) / 60)):0>2d}m'

                out_str += f"<td>{annotation_time}</td>"

            out_str += "</tr>\n"

    out_str += "</table>"
    return HttpResponse(out_str, content_type='text/html')


def stat_reliable_testing(_data, campaign_opts, result_type):
    _annotations = len(set([x[6] for x in _data]))
    _user_mean = sum([x[2] for x in _data]) / (_annotations or 1)
    _cs = _annotations - 1  # Corrected sample size for stdev.
    _user_stdev = 1
    if _cs > 0:
        _user_stdev = sqrt(sum(((x[2] - _user_mean) ** 2 / _cs) for x in _data))

    if int(_user_stdev) == 0:
        _user_stdev = 1

    _tgt = defaultdict(list)
    _bad = defaultdict(list)
    for _x in _data:
        if _x[5] == 'TGT':
            _dst = _tgt
        elif _x[5] == "BAD" or _x[5].startswith('BAD.'):
            # ESA/MQM have extra payload in itemType
            _dst = _bad
        else:
            continue

        _z_score = (_x[2] - _user_mean) / _user_stdev
        # Script generating batches for data assessment task does not
        # keep equal itemIDs for respective TGT and BAD items, so it
        # cannot be used as a key.
        if result_type is DataAssessmentResult:
            _key = f"{_x[4]}"
        else:
            _key = f'{_x[3]}-{_x[4]}'
        # Hotfix: remove #bad from key for ESA campaigns
        if "esa" in campaign_opts and "#bad" in _key:
            _key = _key.replace("#bad", "")
        _dst[_key].append(_z_score)

    _x = []
    _y = []
    for _key in set.intersection(set(_tgt.keys()), set(_bad.keys())):
        _x.append(sum(_bad[_key]) / float(len(_bad[_key] or 1)))
        _y.append(sum(_tgt[_key]) / float(len(_tgt[_key] or 1)))

    _reliable = None
    if _x and _y:
        try:
            from scipy.stats import mannwhitneyu  # type: ignore

            _t, pvalue = mannwhitneyu(_x, _y, alternative='less')
            _reliable = pvalue

        # Possible for mannwhitneyu() to throw in some scenarios
        except ValueError:
            pass

    if _reliable:
        _reliable = f'{_reliable:1.6f}'
    else:
        _reliable = 'n/a'
    return _reliable
