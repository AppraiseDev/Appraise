import logging

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.views import generic

from Appraise.settings import LOG_LEVEL, LOG_HANDLER, STATIC_URL, BASE_CONTEXT

# Setup logging support.
logging.basicConfig(level=LOG_LEVEL)
LOGGER = logging.getLogger('Dashboard.views')
LOGGER.addHandler(LOG_HANDLER)


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
        LOGGER.info('score={0}, item_id={1}'.format(score, item_id))

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
