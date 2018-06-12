from collections import defaultdict
from datetime import datetime
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import HttpResponse
from math import floor
from scipy import stats

from .models import Campaign
from EvalData.models import DirectAssessmentResult, seconds_to_timedelta


@login_required
def campaign_status(request, campaign_name, sort_key=2):
    if sort_key is None:
        sort_key = 2
    campaign = Campaign.objects.filter(campaignName=campaign_name).first()
    if not campaign:
        _msg = 'Failure to identify campaign {0}'.format(campaign_name)
        return HttpResponse(_msg, content_type='text/plain')

    _out = []
    for team in campaign.teams.all():
        for user in team.members.all():
            _data = DirectAssessmentResult.objects.filter(
              createdBy=user, completed=True
            ).values_list('start_time', 'end_time', 'score', 'item__itemID', 'item__itemType')

            _annotations = len(_data)
            _start_times = [x[0] for x in _data]
            _end_times = [x[1] for x in _data]
            _durations = [x[1]-x[0] for x in _data]

            _tgt = defaultdict(list)
            _bad = defaultdict(list)
            for _x in _data:
                if _x[-1] == 'TGT':
                    _dst = _tgt
                elif _x[-1] == 'BAD':
                    _dst = _bad
                else:
                    continue

                _dst[_x[3]].append(_x[2])

            _first_modified = seconds_to_timedelta(min(_start_times)) if len(_start_times) else None
            _last_modified = seconds_to_timedelta(max(_end_times)) if len(_end_times) else None
            _annotation_time = sum(_durations) if len(_durations) else None

            _x = []
            _y = []
            for _key in set.intersection(set(_tgt.keys()), set(_bad.keys())):
                _x.append(sum(_bad[_key])/float(len(_bad[_key] or 1)))
                _y.append(sum(_tgt[_key])/float(len(_tgt[_key] or 1)))

            _reliable = None
            if len(_x) and len(_y):
                t, pvalue = stats.mannwhitneyu(_x, _y, alternative='less')
                _reliable = pvalue

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
                _reliable = '{0:1.3f}'.format(_reliable)

            else:
                _reliable = 'n/a'

            _item = (user.username, user.is_active, _annotations, _first_modified, _last_modified, _annotation_time, _reliable)
            _out.append(_item)

    _out.sort(key=lambda x: x[int(sort_key)])
    _header = '\t'.join(('username', 'active', 'annotations', 'first_modified', 'last_modified', 'annotation_time', 'random'))
    _txt = [_header]
    for x in _out:
        _local_out = '{0:>20}\t{1:3}\t{2}\t{3}\t{4}\t{5}\t{6}'.format(*x)
        _txt.append(_local_out)

    return HttpResponse(u'\n'.join(_txt), content_type='text/plain')
