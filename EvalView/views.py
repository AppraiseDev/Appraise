import logging

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.views import generic

from Appraise.settings import LOG_LEVEL, LOG_HANDLER, STATIC_URL, BASE_CONTEXT

# Setup logging support.
logging.basicConfig(level=LOG_LEVEL)
LOGGER = logging.getLogger('Dashboard.views')
LOGGER.addHandler(LOG_HANDLER)


from datetime import timedelta
def seconds_to_timedelta(value):
    """
    Converst the given value in secodns to datetime.timedelta.
    """
    _days =  value // 86400
    _hours = (value // 3600) % 24
    _mins = (value // 60) % 60
    _secs = value % 60
    return timedelta(days=_days, hours=_hours, minutes=_mins, seconds=_secs)

# pylint: disable=C0330
@login_required
def direct_assessment(request):
    """
    Direct assessment annotation view.
    """
    LOGGER.info('Rendering direct assessment view for user "{0}".'.format(
      request.user.username or "Anonymous"))

    if request.method == "POST":
        score = request.POST.get('score', None)
        item_id = request.POST.get('item_id', None)
        start_timestamp = request.POST.get('start_timestamp', None)
        end_timestamp = request.POST.get('end_timestamp', None)
        LOGGER.info('score={0}, item_id={1}'.format(score, item_id))
        if start_timestamp and end_timestamp:
            duration = float(end_timestamp) - float(start_timestamp)
            LOGGER.debug(float(start_timestamp))
            LOGGER.debug(float(end_timestamp))
            LOGGER.info('start={0}, end={1}, duration={2}'.format(start_timestamp, end_timestamp, duration))

        # If item_id is valid, create annotation result

    # Get item_id for next available item for direct assessment
    item_id = 'foo'

    context = {
      'active_page': 'direct-assessment',
      'reference_text': 'foo',
      'candidate_text': 'bar',
      'item_id': item_id,
    }
    context.update(BASE_CONTEXT)

    return render(request, 'EvalView/direct-assessment.html', context)
