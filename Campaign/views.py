"""
Appraise evaluation framework

See LICENSE for usage details
"""
# pylint: disable=E1101
from collections import defaultdict
from datetime import datetime
from math import floor
from math import sqrt

from django.contrib.auth.decorators import login_required
from django.core.management.base import CommandError
from django.http import HttpResponse

from Appraise.utils import _get_logger
from Campaign.utils import _get_campaign_instance
from EvalData.models import DataAssessmentResult
from EvalData.models import DirectAssessmentDocumentResult
from EvalData.models import PairwiseAssessmentDocumentResult
from EvalData.models import PairwiseAssessmentResult
from EvalData.models import seconds_to_timedelta
from EvalData.models import TASK_DEFINITIONS

# pylint: disable=import-error

RESULT_TYPE_BY_CLASS_NAME = {tup[1].__name__: tup[2] for tup in TASK_DEFINITIONS}

LOGGER = _get_logger(name=__name__)


@login_required
def campaign_status(request, campaign_name, sort_key=2):
    """
    Campaign status view with completion details.
    """
    LOGGER.info(
        'Rendering campaign status view for user "%s".',
        request.user.username or "Anonymous",
    )

    if sort_key is None:
        sort_key = 2

    # Get Campaign instance for campaign name
    try:
        campaign = _get_campaign_instance(campaign_name)

    except CommandError:
        _msg = 'Failure to identify campaign {0}'.format(campaign_name)
        return HttpResponse(_msg, content_type='text/plain')

    _out = []
    for team in campaign.teams.all():
        for user in team.members.all():
            try:
                result_type = RESULT_TYPE_BY_CLASS_NAME[
                    campaign.get_campaign_type()
                ]  # May raise KeyError

            except KeyError as exc:
                LOGGER.debug(
                    'Invalid campaign type %s for campaign %s',
                    campaign.get_campaign_type(),
                    campaign.campaignName,
                )
                LOGGER.error(exc)
                continue

            _data = result_type.objects.filter(
                createdBy=user, completed=True, task__campaign=campaign.id
            )

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

            _annotations = len(set([x[6] for x in _data]))
            _start_times = [x[0] for x in _data]
            _end_times = [x[1] for x in _data]
            _durations = [x[1] - x[0] for x in _data]

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
                if _x[-2] == 'TGT':
                    _dst = _tgt
                elif _x[-2] == 'BAD':
                    _dst = _bad
                else:
                    continue

                _z_score = (_x[2] - _user_mean) / _user_stdev
                # Script generating batches for data assessment task does not
                # keep equal itemIDs for respective TGT and BAD items, so it
                # cannot be used as a key.
                if result_type is DataAssessmentResult:
                    _key = str(_x[4])
                else:
                    _key = '{0}-{1}'.format(_x[3], _x[4])
                _dst[_key].append(_z_score)

            _first_modified = (
                seconds_to_timedelta(min(_start_times)) if _start_times else None
            )
            _last_modified = (
                seconds_to_timedelta(max(_end_times)) if _end_times else None
            )
            _annotation_time = sum(_durations) if _durations else None

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

                except ImportError:
                    print("scipy is not installed")
                    pass

                # Possible for mannwhitneyu() to throw in some scenarios:
                #
                # File "scipy/stats/stats.py", line 4865, in mannwhitneyu
                #   raise ValueError(
                #     'All numbers are identical in mannwhitneyu')
                except ValueError:
                    pass

            if _first_modified:
                _date_modified = datetime(1970, 1, 1) + _first_modified
                _first_modified = str(_date_modified).split('.')[0]

            else:
                _first_modified = 'Never'

            if _last_modified:
                _date_modified = datetime(1970, 1, 1) + _last_modified
                _last_modified = str(_date_modified).split('.')[0]

            else:
                _last_modified = 'Never'

            if _annotation_time:
                _hours = int(floor(_annotation_time / 3600))
                _minutes = int(floor((_annotation_time % 3600) / 60))
                _annotation_time = '{0:0>2d}h{1:0>2d}m'.format(_hours, _minutes)

            else:
                _annotation_time = 'n/a'

            if _reliable:
                _reliable = '{0:1.6f}'.format(_reliable)

            else:
                _reliable = 'n/a'

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

    _out.sort(key=lambda x: x[int(sort_key)])

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

    _txt = ['\t'.join(_header)]
    for _row in _out:
        _local_fmt = '{0:>20}\t{1:3}\t{2}\t{3}\t{4}\t{5}'
        if request.user.is_staff:
            _local_fmt += '\t{6}'

        _local_out = _local_fmt.format(*_row)
        _txt.append(_local_out)

    return HttpResponse(u'\n'.join(_txt), content_type='text/plain')
