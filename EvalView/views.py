from datetime import datetime
import logging

# pylint: disable=import-error
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils.timezone import utc

from Appraise.settings import (
    LOG_LEVEL,
    LOG_HANDLER,
    BASE_CONTEXT,
)
from Campaign.models import Campaign
from EvalData.models import (
    DirectAssessmentTask, DirectAssessmentResult,
    MultiModalAssessmentTask, MultiModalAssessmentResult,
    TaskAgenda
)


# Setup logging support.
logging.basicConfig(level=LOG_LEVEL)
LOGGER = logging.getLogger('Dashboard.views')
LOGGER.addHandler(LOG_HANDLER)


# pylint: disable=C0103,C0330
@login_required
def direct_assessment(request, code=None, campaign_name=None):
    """
    Direct assessment annotation view.
    """
    t1 = datetime.now()

    campaign = None
    if campaign_name:
        campaign = Campaign.objects.filter(campaignName=campaign_name)
        if not campaign.exists():
            _msg = 'No campaign named "%s" exists, redirecting to dashboard'
            LOGGER.info(_msg, campaign_name)
            return redirect('dashboard')

        campaign = campaign[0]

    LOGGER.info('Rendering direct assessment view for user "%s".',
        request.user.username or "Anonymous")

    current_task = None

    # Try to identify TaskAgenda for current user.
    agendas = TaskAgenda.objects.filter(
      user=request.user
    )

    if campaign:
        agendas = agendas.filter(
          campaign=campaign
        )

    for agenda in agendas:
        modified = False
        LOGGER.info('Identified work agenda %s', agenda)
        for serialized_open_task in agenda.serialized_open_tasks():
            open_task = serialized_open_task.get_object_instance()
            if open_task.next_item_for_user(request.user) is not None:
                current_task = open_task
                if not campaign:
                    campaign = agenda.campaign
            else:
                agenda.complete_open_task(serialized_open_task)
                modified = True

        if modified:
            agenda.save()

    if not current_task and agendas.count() > 0:
        LOGGER.info('Work agendas completed, redirecting to dashboard')
        LOGGER.info('- code=%s, campaign=%s', code, campaign)
        return redirect('dashboard')

    # If language code has been given, find a free task and assign to user.
    if not current_task:
        current_task = DirectAssessmentTask.get_task_for_user(user=request.user)

    if not current_task:
        if code is None or campaign is None:
            LOGGER.info('No current task detected, redirecting to dashboard')
            LOGGER.info('- code=%s, campaign=%s', code, campaign)
            return redirect('dashboard')

        LOGGER.info('Identifying next task for code "%s", campaign="%s"',
          code, campaign)
        next_task = DirectAssessmentTask.get_next_free_task_for_language(
            code, campaign, request.user)

        if next_task is None:
            LOGGER.info('No next task detected, redirecting to dashboard')
            return redirect('dashboard')

        next_task.assignedTo.add(request.user)
        next_task.save()

        current_task = next_task

    if current_task:
        if not campaign:
            campaign = current_task.campaign

        elif campaign.campaignName != current_task.campaign.campaignName:
            _msg = 'Incompatible campaign given, using item campaign instead!'
            LOGGER.info(_msg)
            campaign = current_task.campaign

    t2 = datetime.now()
    if request.method == "POST":
        score = request.POST.get('score', None)
        item_id = request.POST.get('item_id', None)
        task_id = request.POST.get('task_id', None)
        start_timestamp = request.POST.get('start_timestamp', None)
        end_timestamp = request.POST.get('end_timestamp', None)
        LOGGER.info('score=%s, item_id=%s', score, item_id)
        if score and item_id and start_timestamp and end_timestamp:
            duration = float(end_timestamp) - float(start_timestamp)
            LOGGER.debug(float(start_timestamp))
            LOGGER.debug(float(end_timestamp))
            LOGGER.info('start=%s, end=%s, duration=%s',
                start_timestamp, end_timestamp, duration)

            current_item = current_task.next_item_for_user(request.user)
            if (current_item.itemID != int(item_id) or
                current_item.id != int(task_id)):
                _msg = 'Item ID %s does not match item %s, will not save!'
                LOGGER.debug(_msg, item_id, current_item.itemID)

            else:
                utc_now = datetime.utcnow().replace(tzinfo=utc)

                # pylint: disable=E1101
                DirectAssessmentResult.objects.create(
                  score=score,
                  start_time=float(start_timestamp),
                  end_time=float(end_timestamp),
                  item=current_item,
                  task=current_task,
                  createdBy=request.user,
                  activated=False,
                  completed=True,
                  dateCompleted=utc_now,
                )

    t3 = datetime.now()

    current_item, completed_items = current_task.next_item_for_user(
        request.user, return_completed_items=True)
    if not current_item:
        LOGGER.info('No current item detected, redirecting to dashboard')
        return redirect('dashboard')

    # completed_items_check = current_task.completed_items_for_user(request.user)
    completed_blocks = int(completed_items / 10)
    _msg = 'completed_items=%s, completed_blocks=%s'
    LOGGER.info(_msg, completed_items, completed_blocks)

    source_language = current_task.marketSourceLanguage()
    target_language = current_task.marketTargetLanguage()

    t4 = datetime.now()

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
      'debug_times': (t2-t1, t3-t2, t4-t3, t4-t1),
      'template_debug': 'debug' in request.GET,
      'campaign': campaign.campaignName,
      'datask_id': current_task.id,
      'trusted_user': current_task.is_trusted_user(request.user),
    }
    context.update(BASE_CONTEXT)

    return render(request, 'EvalView/direct-assessment.html', context)


# pylint: disable=C0103,C0330
@login_required
def multimodal_assessment(request, code=None, campaign_name=None):
    """
    Multi modal assessment annotation view.
    """
    t1 = datetime.now()

    campaign = None
    if campaign_name:
        campaign = Campaign.objects.filter(campaignName=campaign_name)
        if not campaign.exists():
            _msg = 'No campaign named "%s" exists, redirecting to dashboard'
            LOGGER.info(_msg, campaign_name)
            return redirect('dashboard')

        campaign = campaign[0]

    LOGGER.info('Rendering multimodal assessment view for user "%s".',
        request.user.username or "Anonymous")

    current_task = None

    # Try to identify TaskAgenda for current user.
    agendas = TaskAgenda.objects.filter(
      user=request.user
    )

    if campaign:
        agendas = agendas.filter(
          campaign=campaign
        )

    for agenda in agendas:
        modified = False
        LOGGER.info('Identified work agenda %s', agenda)
        for serialized_open_task in agenda.serialized_open_tasks():
            open_task = serialized_open_task.get_object_instance()
            if open_task.next_item_for_user(request.user) is not None:
                current_task = open_task
                if not campaign:
                    campaign = agenda.campaign
            else:
                agenda.complete_open_task(serialized_open_task)
                modified = True

        if modified:
            agenda.save()

    if not current_task and agendas.count() > 0:
        LOGGER.info('Work agendas completed, redirecting to dashboard')
        LOGGER.info('- code=%s, campaign=%s', code, campaign)
        return redirect('dashboard')

    # If language code has been given, find a free task and assign to user.
    if not current_task:
        current_task = DirectAssessmentTask.get_task_for_user(
            user=request.user)

    if not current_task:
        if code is None or campaign is None:
            LOGGER.info('No current task detected, redirecting to dashboard')
            LOGGER.info('- code=%s, campaign=%s', code, campaign)
            return redirect('dashboard')

        _msg = 'Identifying next task for code "%s", campaign="%s"'
        LOGGER.info(_msg, code, campaign)
        next_task = MultiModalAssessmentTask.get_next_free_task_for_language(
            code, campaign, request.user)

        if next_task is None:
            LOGGER.info('No next task detected, redirecting to dashboard')
            return redirect('dashboard')

        next_task.assignedTo.add(request.user)
        next_task.save()

        current_task = next_task

    if current_task:
        if not campaign:
            campaign = current_task.campaign

        elif campaign.campaignName != current_task.campaign.campaignName:
            _msg = 'Incompatible campaign given, using item campaign instead!'
            LOGGER.info(_msg)
            campaign = current_task.campaign

    t2 = datetime.now()
    if request.method == "POST":
        score = request.POST.get('score', None)
        item_id = request.POST.get('item_id', None)
        task_id = request.POST.get('task_id', None)
        start_timestamp = request.POST.get('start_timestamp', None)
        end_timestamp = request.POST.get('end_timestamp', None)
        LOGGER.info('score=%s, item_id=%s', score, item_id)
        if score and item_id and start_timestamp and end_timestamp:
            duration = float(end_timestamp) - float(start_timestamp)
            LOGGER.debug(float(start_timestamp))
            LOGGER.debug(float(end_timestamp))
            LOGGER.info('start=%s, end=%s, duration=%s',
                start_timestamp, end_timestamp, duration)

            current_item = current_task.next_item_for_user(request.user)
            if (current_item.itemID != int(item_id) or
                current_item.id != int(task_id)):
                _msg = 'Item ID %s does not match  item %s, will not save!'
                LOGGER.debug(_msg, item_id, current_item.itemID)

            else:
                utc_now = datetime.utcnow().replace(tzinfo=utc)

                # pylint: disable=E1101
                MultiModalAssessmentResult.objects.create(
                  score=score,
                  start_time=float(start_timestamp),
                  end_time=float(end_timestamp),
                  item=current_item,
                  task=current_task,
                  createdBy=request.user,
                  activated=False,
                  completed=True,
                  dateCompleted=utc_now,
                )

    t3 = datetime.now()

    current_item, completed_items = current_task.next_item_for_user(
        request.user, return_completed_items=True)
    if not current_item:
        LOGGER.info('No current item detected, redirecting to dashboard')
        return redirect('dashboard')

    # completed_items_check = current_task.completed_items_for_user(request.user)
    completed_blocks = int(completed_items / 10)
    _msg = 'completed_items=%s, completed_blocks=%s'
    LOGGER.info(_msg, completed_items, completed_blocks)

    source_language = current_task.marketSourceLanguage()
    target_language = current_task.marketTargetLanguage()

    t4 = datetime.now()

    context = {
      'active_page': 'multimodal-assessment',
      'reference_text': current_item.sourceText,
      'candidate_text': current_item.targetText,
      'image_url': current_item.imageURL,
      'item_id': current_item.itemID,
      'task_id': current_item.id,
      'completed_blocks': completed_blocks,
      'items_left_in_block': 10 - (completed_items - completed_blocks * 10),
      'source_language': source_language,
      'target_language': target_language,
      'debug_times': (t2-t1, t3-t2, t4-t3, t4-t1),
      'template_debug': 'debug' in request.GET,
      'campaign': campaign.campaignName,
      'datask_id': current_task.id,
      'trusted_user': current_task.is_trusted_user(request.user),
    }
    context.update(BASE_CONTEXT)

    return render(request, 'EvalView/multimodal-assessment.html', context)
