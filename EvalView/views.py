import logging

from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required
from django.views import generic

from EvalData.models import DirectAssessmentTask, DirectAssessmentResult, \
  TextPair, seconds_to_timedelta
from Appraise.settings import LOG_LEVEL, LOG_HANDLER, STATIC_URL, BASE_CONTEXT

# Setup logging support.
logging.basicConfig(level=LOG_LEVEL)
LOGGER = logging.getLogger('Dashboard.views')
LOGGER.addHandler(LOG_HANDLER)


# pylint: disable=C0330
@login_required
def direct_assessment(request, code=None):
    """
    Direct assessment annotation view.
    """
    LOGGER.info('Rendering direct assessment view for user "{0}".'.format(
      request.user.username or "Anonymous"))

    # If language code has been given, find a free task and assign to user.
    current_task = DirectAssessmentTask.get_task_for_user(user=request.user)
    if not current_task:
        if code is None:
            LOGGER.info('No current task detected, redirecting to dashboard')
            return redirect('dashboard')

        LOGGER.info('Identifying next task for code "{0}"'.format(code))
        next_task = DirectAssessmentTask.get_next_free_task_for_language(code)

        if next_task is None:
            LOGGER.info('No next task detected, redirecting to dashboard')
            return redirect('dashboard')

        next_task.assignedTo.add(request.user)
        next_task.save()

        current_task = next_task

    if request.method == "POST":
        score = request.POST.get('score', None)
        item_id = request.POST.get('item_id', None)
        task_id = request.POST.get('task_id', None)
        start_timestamp = request.POST.get('start_timestamp', None)
        end_timestamp = request.POST.get('end_timestamp', None)
        LOGGER.info('score={0}, item_id={1}'.format(score, item_id))
        if score and item_id and start_timestamp and end_timestamp:
            duration = float(end_timestamp) - float(start_timestamp)
            LOGGER.debug(float(start_timestamp))
            LOGGER.debug(float(end_timestamp))
            LOGGER.info('start={0}, end={1}, duration={2}'.format(start_timestamp, end_timestamp, duration))

            current_item = current_task.next_item()
            if current_item.itemID != int(item_id) \
              or current_item.id != int(task_id):
                LOGGER.debug(
                  'Item ID {0} does not match current item {1}, will ' \
                  'not save result!'.format(item_id, current_item.itemID)
                )

            else:
                new_result = DirectAssessmentResult(
                  score=score,
                  start_time=float(start_timestamp),
                  end_time=float(end_timestamp),
                  item=current_item,
                  task=current_task,
                  createdBy=request.user
                )
                new_result.complete()
                new_result.save()

                current_item.complete()
                current_item.save()



            # 1) Create results object, save
            # 2) Complete item, save
            # 3) If no more items, complete task and redirect to dashboard

        # If item_id is valid, create annotation result

    # Get item_id for next available item for direct assessment

    current_item = current_task.next_item()
    if not current_item:
        LOGGER.info('No current item detected, redirecting to dashboard')
        return redirect('dashboard')

    completed_items = current_task.completed_items()
    completed_blocks = int(completed_items / 10)
    print(completed_items, completed_blocks)

    source_language = current_task.marketSourceLanguage()
    target_language = current_task.marketTargetLanguage()

    context = {
      'active_page': 'direct-assessment',
      'reference_text': current_item.sourceText,
      'candidate_text': current_item.targetText,
      'item_id': current_item.itemID,
      'task_id': current_item.id,
      'completed_blocks': completed_blocks,
      'items_left_in_block': 10 - (completed_items - completed_blocks * 10),
      'source_language': source_language,
      'target_language': target_language,
    }
    context.update(BASE_CONTEXT)

    return render(request, 'EvalView/direct-assessment.html', context)
