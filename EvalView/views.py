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

DUMMY_DATA = [
  {
    'ref':"Petr Tlucho\u0159 is one of three MPs who have been accused by the prosecution service of taking bribes in the form of lucrative positions from the then Prime Minister Ne\u010das and his former chief of staff Jana Nagyova in return for a political concession.",
    'tgt':"Peter Tlucho\u0159 is one of three Members, who should, according to the indictment from the Prime Minister and his former cabinet chief Ne\u010dase Jany Nagyov\u00e9 political newsstand, a lucrative post for political concessions."
  },
  {
    'ref':"Indeed, the USA soccer star and the Dexter actress share incredibly similar face shapes and eyes.",
    'tgt':"Soccer star Hope Sol and actress Dexter Jennifer Carpenter have really incredibly similar face and eyes.",
  },
  {
    'ref':"It purifies the blood, strengthens blood circulation, it is also said to prevent the greying of hair, and it is packed with minerals.",
    'tgt':"Cleans blood, strengthens blood circulation, even supposedly prevents hair greasing and is literally charged with minerals.",
  },
  {
    'ref':"The Chinese and the Russians tend to split the prizes for the men, and the Chinese and the Canadians for the women.",
    'tgt':"The Chinese and the Russians tend to split the prizes for the men, and the Chinese and the Canadians for the women.",
  },
  {
    'ref':"\"If you suffocate people and they don't have any other options but to protest, it breaks out,\" said Seyoum Teshome, a university lecturer in central Ethiopia.",
    'tgt':"\"When you suffocate people and they have no choice but to protest, there will be a breach,\" said Seyoum Teshome, who lectured at the University of Central Ethiopia.",
  },
]

# pylint: disable=C0330
@login_required
def direct_assessment(request):
    """
    Direct assessment annotation view.
    """
    LOGGER.info('Rendering direct assessment view for user "{0}".'.format(
      request.user.username or "Anonymous"))

    import random
    ids = [x for x in range(len(DUMMY_DATA))]
    random.shuffle(ids)

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
    item_id = ids[0]

    context = {
      'active_page': 'direct-assessment',
      'reference_text': DUMMY_DATA[item_id]['ref'],
      'candidate_text': DUMMY_DATA[item_id]['tgt'],
      'item_id': item_id,
    }
    context.update(BASE_CONTEXT)

    return render(request, 'EvalView/direct-assessment.html', context)
