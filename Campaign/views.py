from datetime import datetime
from django.contrib.auth.models import User
from django.http import HttpResponse
from math import floor

from .models import Campaign
from EvalData.models import DirectAssessmentResult, seconds_to_timedelta


# Create your views here.
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
            ).values_list('start_time', 'end_time')

            _annotations = len(_data)
            _start_times = [x[0] for x in _data]
            _end_times = [x[1] for x in _data]
            _durations = [x[1]-x[0] for x in _data]

            _first_modified = seconds_to_timedelta(min(_start_times)) if len(_start_times) else None
            _last_modified = seconds_to_timedelta(max(_end_times)) if len(_end_times) else None
            _annotation_time = sum(_durations) if len(_durations) else None

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

            _item = (user.username, _annotations, _first_modified, _last_modified, _annotation_time)
            _out.append(_item)

    _out.sort(key=lambda x: x[int(sort_key)])
    _header = '\t'.join(('username', 'annotations', 'first_modified', 'last_modified', 'annotation_time'))
    _txt = [_header]
    for x in _out:
        _local_out = '{0:>20}\t{1:3}\t{2}\t{3}\t{4}'.format(*x)
        _txt.append(_local_out)

    return HttpResponse(u'\n'.join(_txt), content_type='text/plain')
