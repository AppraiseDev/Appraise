"""
Appraise evaluation framework

See LICENSE for usage details
"""
from collections import defaultdict
from datetime import datetime
from hashlib import md5
from math import floor
from math import sqrt
from uuid import UUID

from scipy.stats import mannwhitneyu  # type: ignore

from Appraise.settings import SECRET_KEY
from EvalData.models import DataAssessmentResult
from EvalData.models import DirectAssessmentContextResult
from EvalData.models import DirectAssessmentDocumentResult
from EvalData.models import DirectAssessmentResult
from EvalData.models import MultiModalAssessmentResult
from EvalData.models import PairwiseAssessmentDocumentResult
from EvalData.models import PairwiseAssessmentResult
from EvalData.models import RESULT_TYPES

# Maximum allowed p-value for the Wilcoxon rank-sum test
MAX_WILCOXON_PVALUE = 0.010

# Minimum allowed total annotation time for a task
MIN_ANNOTATION_TIME = 600  # i.e. 10 minutes


def generate_confirmation_token(username, run_qc=True):
    """
    Generates a confirmation token for completed work.

    Returns a valid token if the quality control (QC) is successful, otherwise
    an invalid token if the user failed the QC or it cannot be run due to
    unsufficient annotation data.
    If performing QC is disabled, a valid token is always returned.
    """
    if run_qc == True:
        status = 'SUCCESS' if run_quality_control(username) else 'FAILED'
        seed = SECRET_KEY + username + status
    else:
        seed = SECRET_KEY + username + 'SUCCESS'

    token = md5()
    token.update(seed.encode('utf-8'))
    new_uuid = UUID(token.hexdigest())
    return new_uuid


def run_quality_control(username):
    """
    Runs quality control for the user.

    It is passed if p-value of the Wilcoxon test on annotated (TGT, BAD) pairs,
    and the total annotation times are in pre-defined thresholds.

    Code extracted from Campaign/views.py:campaign_status()
    """
    _data = None
    result_type = None
    for _type in RESULT_TYPES:
        _data = _type.objects.filter(createdBy__username=username, completed=True)
        # Get the first result task type available: might not work in all scenarios
        if _data:
            result_type = _type
            break

    if result_type is None:  # No items are completed yet
        return None

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

    _user_mean = sum([x[2] for x in _data]) / (_annotations or 1)

    _cs = _annotations - 1  # Corrected sample size for stdev.
    _user_stdev = 1
    if _cs > 0:
        _user_stdev = sqrt(sum(((x[2] - _user_mean) ** 2 / _cs) for x in _data))

    if int(_user_stdev) == 0:
        _user_stdev = 1

    # Extract pairs for the Wilcoxon test
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
        _key = '{0}-{1}'.format(_x[3], _x[4])
        _dst[_key].append(_z_score)

    _x = []
    _y = []
    for _key in set.intersection(set(_tgt.keys()), set(_bad.keys())):
        _x.append(sum(_bad[_key]) / float(len(_bad[_key] or 1)))
        _y.append(sum(_tgt[_key]) / float(len(_tgt[_key] or 1)))

    # Run the Wilcoxon rank-sum test
    pvalue = None
    if _x and _y:
        try:
            _t, _pvalue = mannwhitneyu(_x, _y, alternative='less')
            pvalue = _pvalue
        # Possible for mannwhitneyu() to throw in some scenarios:
        #
        # File "scipy/stats/stats.py", line 4865, in mannwhitneyu
        #   raise ValueError(
        #     'All numbers are identical in mannwhitneyu')
        except ValueError:
            pass

    # Compute the total annotation time
    _durations = [x[1] - x[0] for x in _data]
    annotation_time = sum(_durations) if _durations else None

    print(
        "User '{}', items= {}, p-value= {}, time= {}".format(
            username, len(_x), pvalue, annotation_time
        )
    )

    return (
        pvalue is not None
        and pvalue <= MAX_WILCOXON_PVALUE
        and annotation_time is not None
        and annotation_time >= MIN_ANNOTATION_TIME
    )
