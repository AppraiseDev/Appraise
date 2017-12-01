from datetime import datetime
from django.contrib.auth.models import User
from django.http import HttpResponse

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
            ).values_list('end_time', flat=True)

            _annotations = len(_data)
            _last_modified = seconds_to_timedelta(max(_data)) if len(_data) else None
            if _last_modified:
                _date_modified = datetime(1970, 1, 1) + _last_modified
                _last_modified = str(_date_modified).split('.')[0]

            else:
                _last_modified = 'Never'

            _item = (user.username, _annotations, _last_modified)
            _out.append(_item)

    _out.sort(key=lambda x: x[int(sort_key)])
    _txt = []
    for x in _out:
        _local_out = '{0:>20}\t{1:3}\t{2}'.format(*x)
        _txt.append(_local_out)

    return HttpResponse(u'\n'.join(_txt), content_type='text/plain')
