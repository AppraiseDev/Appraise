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
from django.utils.html import escape

from Appraise.utils import _get_logger, _compute_user_total_annotation_time
from Campaign.utils import _get_campaign_instance
from EvalData.models import DataAssessmentResult
from EvalData.models import DirectAssessmentDocumentResult
from EvalData.models import ContrastiveAssessmentDocumentResult
from EvalData.models import PairwiseAssessmentDocumentResult
from EvalData.models import PairwiseAssessmentResult
from EvalData.models import TASK_DEFINITIONS
from EvalData.models import TaskAgenda
from EvalData.models.direct_assessment_document import DirectAssessmentDocumentTask

# pylint: disable=import-error

RESULT_TYPE_BY_CLASS_NAME = {tup[1].__name__: tup[2] for tup in TASK_DEFINITIONS}

LOGGER = _get_logger(name=__name__)


def _format_duration(seconds, with_space=False):
    if seconds is None:
        return None

    total_seconds = max(0, int(seconds))
    hours = int(floor(total_seconds / 3600))
    minutes = int(floor((total_seconds % 3600) / 60))
    separator = ' ' if with_space else ''
    return f'{hours:0>2d}h{separator}{minutes:0>2d}m'


def _format_timestamp_strings(epoch_seconds):
    if epoch_seconds is None:
        return ('Never', '')

    dt_value = datetime.fromtimestamp(epoch_seconds)
    full_value = str(dt_value).split('.')[0]
    trimmed_value = ':'.join(full_value.split(':')[:-1])
    return (full_value, trimmed_value)


def _resolve_task_from_object_id(object_id):
    try:
        return object_id.get_object_instance()
    except Exception:  # pylint: disable=broad-except
        LOGGER.debug('Failed to resolve task object for %s', object_id, exc_info=True)
        return None


def _estimate_total_items(user, campaign, first_result):
    agenda = TaskAgenda.objects.filter(user=user, campaign=campaign).first()
    total_items = 0
    has_items = False

    if agenda:
        for serialized_task in agenda.serialized_open_tasks():
            task_obj = _resolve_task_from_object_id(serialized_task)
            if task_obj and hasattr(task_obj, 'items'):
                total_items += task_obj.items.count()
                has_items = True

        if not has_items:
            for serialized_task in agenda._completed_tasks.all():  # pylint: disable=protected-access
                task_obj = _resolve_task_from_object_id(serialized_task)
                if task_obj and hasattr(task_obj, 'items'):
                    total_items += task_obj.items.count()
                    has_items = True

        if has_items:
            return total_items

    if first_result and hasattr(first_result, 'task'):
        task = first_result.task
        if task and hasattr(task, 'items'):
            try:
                return task.items.count()
            except Exception:  # pylint: disable=broad-except
                LOGGER.debug('Failed to count items for task %s', task, exc_info=True)

    return None


def _derive_status_emoji(is_active, annotations, total_items, has_data):
    if not is_active:
        return '🚫'

    if annotations and total_items is None:
        return '❌'

    if total_items:
        if annotations >= total_items:
            return '✅'
        if annotations > 0:
            return '🛠️'
        return '💤'

    if annotations or has_data:
        return '🛠️'

    return '💤'


def _reliability_sort_value(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return float('inf')


def _collect_campaign_status_rows(campaign, result_type, campaign_opts):
    rows = []

    for team in campaign.teams.all():
        for user in team.members.all():
            results_qs = result_type.objects.filter(
                createdBy=user, completed=True, task__campaign=campaign.id
            )
            first_result = results_qs.first()
            data_qs = results_qs
            is_mqm_or_esa = False

            if (
                result_type is PairwiseAssessmentResult
                or result_type is PairwiseAssessmentDocumentResult
                or result_type is ContrastiveAssessmentDocumentResult
            ):
                data_rows = list(
                    data_qs.values_list(
                        'start_time',
                        'end_time',
                        'score1',
                        'item__itemID',
                        'item__target1ID',
                        'item__itemType',
                        'item__id',
                    )
                )
                time_pairs = [(row[0], row[1]) for row in data_rows]
            elif 'mqm' in campaign_opts:
                is_mqm_or_esa = True
                raw_rows = list(
                    data_qs.values_list(
                        'start_time',
                        'end_time',
                        'mqm',
                        'item__itemID',
                        'item__targetID',
                        'item__itemType',
                        'item__id',
                        'item__documentID',
                    )
                )
                doc_time_pairs = defaultdict(list)
                for row in raw_rows:
                    doc_time_pairs[f'{row[7]} ||| {row[4]}'].append((row[0], row[1]))

                time_pairs = [
                    (
                        min(start for start, _ in doc_rows),
                        max(end for _, end in doc_rows),
                    )
                    for doc_rows in doc_time_pairs.values()
                ]

                data_rows = [
                    (
                        row[0],
                        row[1],
                        -len(json.loads(row[2])),
                        row[3],
                        row[4],
                        row[5],
                        row[6],
                    )
                    for row in raw_rows
                ]
            else:
                data_rows = list(
                    data_qs.values_list(
                        'start_time',
                        'end_time',
                        'score',
                        'item__itemID',
                        'item__targetID',
                        'item__itemType',
                        'item__id',
                    )
                )
                time_pairs = [(row[0], row[1]) for row in data_rows]

            reliability = stat_reliable_testing(data_rows, campaign_opts, result_type)
            annotations = len({row[6] for row in data_rows})
            start_times = [row[0] for row in data_rows if row[0] > 0]
            end_times = [row[1] for row in data_rows if row[1] > 0]
            first_epoch = min(start_times) if start_times else None
            last_epoch = max(end_times) if end_times else None
            first_full, first_trim = _format_timestamp_strings(first_epoch)
            last_full, last_trim = _format_timestamp_strings(last_epoch)
            has_data = bool(data_rows)

            if not has_data:
                first_trim = ''
                last_trim = ''

            annotation_time_seconds = (
                _compute_user_total_annotation_time(time_pairs)
                if time_pairs
                else 0
            )
            coarse_seconds = None
            if first_epoch is not None and last_epoch is not None:
                coarse_seconds = max(int(last_epoch - first_epoch), 0)

            annotation_time_plain = 'n/a'
            annotation_time_html = ''
            if annotation_time_seconds:
                annotation_time_plain = _format_duration(annotation_time_seconds)
                annotation_time_html = _format_duration(
                    annotation_time_seconds, with_space=True
                )

            coarse_plain = None
            coarse_html = ''
            if coarse_seconds is not None:
                coarse_plain = _format_duration(coarse_seconds)
                coarse_html = _format_duration(coarse_seconds, with_space=True)

            if (
                is_mqm_or_esa
                and annotation_time_plain != 'n/a'
                and coarse_plain
            ):
                annotation_time_plain = f'{annotation_time_plain}--{coarse_plain}'

            total_items = _estimate_total_items(user, campaign, first_result)
            if total_items is None:
                progress_text = 'Task not found' if annotations else 'No task assigned'
            elif total_items:
                completion_ratio = min(annotations / total_items, 1.0)
                progress_text = f'{annotations}/{total_items} ({completion_ratio:.0%})'
            else:
                progress_text = '0/0'

            status_emoji = _derive_status_emoji(
                user.is_active, annotations, total_items, has_data
            )

            rows.append(
                {
                    'username': user.username,
                    'is_active': user.is_active,
                    'annotations': annotations,
                    'first_modified_epoch': first_epoch,
                    'first_modified_full': first_full,
                    'first_modified_trim': first_trim,
                    'last_modified_epoch': last_epoch,
                    'last_modified_full': last_full,
                    'last_modified_trim': last_trim,
                    'annotation_time_seconds': annotation_time_seconds,
                    'annotation_time_plain': annotation_time_plain,
                    'annotation_time_html': annotation_time_html,
                    'coarse_seconds': coarse_seconds,
                    'coarse_time_plain': coarse_plain,
                    'coarse_time_html': coarse_html,
                    'reliability': reliability,
                    'progress': progress_text,
                    'status_emoji': status_emoji,
                    'total_items': total_items,
                    'has_data': has_data,
                }
            )

    return rows


def _sort_campaign_rows(rows, sort_key, include_staff):
    sort_functions = [
        lambda row: row['username'].lower(),
        lambda row: row['is_active'],
        lambda row: row['annotations'],
        lambda row: row['first_modified_epoch']
        if row['first_modified_epoch'] is not None
        else float('inf'),
        lambda row: row['last_modified_epoch']
        if row['last_modified_epoch'] is not None
        else float('inf'),
        lambda row: row['annotation_time_seconds'],
    ]

    if include_staff:
        sort_functions.append(
            lambda row: _reliability_sort_value(row['reliability'])
        )

    default_index = 2
    if sort_key is not None:
        try:
            sort_index = int(sort_key)
            if sort_index < 0 or sort_index >= len(sort_functions):
                sort_index = default_index
        except ValueError:
            sort_index = default_index
    else:
        sort_index = default_index

    rows.sort(key=sort_functions[sort_index])


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
    if "newcampaignstatuspage" in campaign_opts:
        return campaign_status_new(
            request, campaign, result_type, campaign_opts, sort_key
        )
    return campaign_status_plain(
        request, campaign, result_type, campaign_opts, sort_key
    )


def campaign_status_plain(request, campaign, result_type, campaign_opts, sort_key):
    rows = _collect_campaign_status_rows(campaign, result_type, campaign_opts)
    _sort_campaign_rows(rows, sort_key, request.user.is_staff)

    formatted_rows = []
    for row in rows:
        formatted = (
            row['username'],
            row['is_active'],
            row['annotations'],
            row['first_modified_full'],
            row['last_modified_full'],
            row['annotation_time_plain'],
        )
        if request.user.is_staff:
            formatted += (row['reliability'],)
        formatted_rows.append(formatted)

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
    for _row in [_header] + formatted_rows:
        _local_fmt = '|{0:>15}|{1:>6}|{2:>11}|{3:>20}|{4:>20}|{5:>15}|'
        if request.user.is_staff:
            _local_fmt += '{6:>10}|'

        _local_out = _local_fmt.format(*_row)
        _txt.append(_local_out)

    return HttpResponse('\n'.join(_txt), content_type='text/plain')


def campaign_status_new(request, campaign, result_type, campaign_opts, sort_key):
    rows = _collect_campaign_status_rows(campaign, result_type, campaign_opts)
    _sort_campaign_rows(rows, sort_key, request.user.is_staff)

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
    out_str += f"<h1>{escape(campaign.campaignName)}</h1>\n"
    out_str += "<table>\n"

    header = """<tr>
<th>Username</th>
<th>Progress</th>
<th>First Modified</th>
<th>Last Modified</th>
<th style="cursor: pointer" title="Very coarse upper bound estimate between the last and the first interaction with the system.">Time (Coarse❔)</th>
<th style="cursor: pointer" title="Sum of times between any two interactions that are not longer than 10 minutes.">Time (Real❔)</th>
"""

    if request.user.is_staff:
        header += "<th>Reliability</th>"

    header += "</tr>\n"
    out_str += header

    for row in rows:
        username_cell = escape(row['username'])
        if row['status_emoji']:
            username_cell = f"{username_cell} {row['status_emoji']}"
        if not row['is_active']:
            username_cell = f"{username_cell} (inactive)"

        progress_cell = escape(row['progress']) if row['progress'] else ''
        first_modified_cell = escape(row['first_modified_trim']) if row['first_modified_trim'] else ''
        last_modified_cell = escape(row['last_modified_trim']) if row['last_modified_trim'] else ''
        coarse_cell = escape(row['coarse_time_html']) if row['coarse_time_html'] else ''
        real_cell = escape(row['annotation_time_html']) if row['annotation_time_html'] else ''

        out_str += "<tr>"
        out_str += f"<td>{username_cell}</td>"
        out_str += f"<td>{progress_cell}</td>"
        out_str += f"<td>{first_modified_cell}</td>"
        out_str += f"<td>{last_modified_cell}</td>"
        out_str += f"<td>{coarse_cell}</td>"
        out_str += f"<td>{real_cell}</td>"

        if request.user.is_staff:
            reliability_cell = escape(row['reliability']) if row['reliability'] else 'n/a'
            out_str += f"<td>{reliability_cell}</td>"

        out_str += "</tr>\n"

    out_str += "</table>"
    return HttpResponse(out_str, content_type='text/html')


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
                first_modified = min([x.start_time for x in _data if x.start_time > 0])
                last_modified = max([x.end_time for x in _data if x.end_time > 0])

                first_modified_str = str(datetime.fromtimestamp(first_modified)).split('.')[0]
                last_modified_str = str(datetime.fromtimestamp(last_modified)).split('.')[0]
                # remove seconds
                first_modified_str = ":".join(first_modified_str.split(":")[:-1])
                last_modified_str = ":".join(last_modified_str.split(":")[:-1])

                out_str += f"<td>{first_modified_str}</td>"
                out_str += f"<td>{last_modified_str}</td>"
                annotation_time_upper = last_modified - first_modified
                annotation_time_upper = f'{int(floor(annotation_time_upper / 3600)):0>2d}h {int(floor((annotation_time_upper % 3600) / 60)):0>2d}m'
                out_str += f"<td>{annotation_time_upper}</td>"

                # consider time that's in any action within 10 minutes
                times = sorted([t for item in _data for t in [item.start_time, item.end_time] if t > 0])
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
