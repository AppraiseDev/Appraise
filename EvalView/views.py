"""
Appraise evaluation framework

See LICENSE for usage details
"""
from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect
from django.shortcuts import render
from django.utils.timezone import utc

from Appraise.settings import BASE_CONTEXT
from Appraise.utils import _get_logger
from Campaign.models import Campaign
from EvalData.models import DataAssessmentResult
from EvalData.models import DataAssessmentTask
from EvalData.models import DirectAssessmentContextResult
from EvalData.models import DirectAssessmentContextTask
from EvalData.models import DirectAssessmentDocumentResult
from EvalData.models import DirectAssessmentDocumentTask
from EvalData.models import DirectAssessmentResult
from EvalData.models import DirectAssessmentTask
from EvalData.models import MultiModalAssessmentResult
from EvalData.models import MultiModalAssessmentTask
from EvalData.models import PairwiseAssessmentResult
from EvalData.models import PairwiseAssessmentTask
from EvalData.models import TaskAgenda

# pylint: disable=import-error

LOGGER = _get_logger(name=__name__)

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

    LOGGER.info(
        'Rendering direct assessment view for user "%s".',
        request.user.username or "Anonymous",
    )

    current_task = None

    # Try to identify TaskAgenda for current user.
    agendas = TaskAgenda.objects.filter(user=request.user)

    if campaign:
        agendas = agendas.filter(campaign=campaign)

    for agenda in agendas:
        LOGGER.info('Identified work agenda %s', agenda)

        tasks_to_complete = []
        for serialized_open_task in agenda.serialized_open_tasks():
            open_task = serialized_open_task.get_object_instance()

            # Skip tasks which are not available anymore
            if open_task is None:
                continue

            if open_task.next_item_for_user(request.user) is not None:
                current_task = open_task
                if not campaign:
                    campaign = agenda.campaign
            else:
                tasks_to_complete.append(serialized_open_task)

        modified = False
        for task in tasks_to_complete:
            modified = agenda.complete_open_task(task) or modified

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

        LOGGER.info(
            'Identifying next task for code "%s", campaign="%s"',
            code,
            campaign,
        )
        next_task = DirectAssessmentTask.get_next_free_task_for_language(
            code, campaign, request.user
        )

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
            LOGGER.info(
                'start=%s, end=%s, duration=%s',
                start_timestamp,
                end_timestamp,
                duration,
            )

            current_item = current_task.next_item_for_user(request.user)
            if current_item.itemID != int(item_id) or current_item.id != int(task_id):
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
        request.user, return_completed_items=True
    )
    if not current_item:
        LOGGER.info('No current item detected, redirecting to dashboard')
        return redirect('dashboard')

    # completed_items_check = current_task.completed_items_for_user(
    #     request.user)
    completed_blocks = int(completed_items / 10)
    _msg = 'completed_items=%s, completed_blocks=%s'
    LOGGER.info(_msg, completed_items, completed_blocks)

    source_language = current_task.marketSourceLanguage()
    target_language = current_task.marketTargetLanguage()

    t4 = datetime.now()

    # Define priming question
    #
    # Default:
    #   How accurately does the above candidate text convey the original
    #   semantics of the source text? Slider ranges from
    #   <em>Not at all</em> (left) to <em>Perfectly</em> (right).
    #
    # We currently allow specific overrides, based on campaign name.
    reference_label = 'Source text'
    candidate_label = 'Candidate translation'
    priming_question_text = (
        'How accurately does the above candidate text convey the original '
        'semantics of the source text? Slider ranges from '
        '<em>Not at all</em> (left) to <em>Perfectly</em> (right).'
    )

    _reference_campaigns = ('HumanEvalFY19{0}'.format(x) for x in ('7B',))

    _adequacy_campaigns = ('HumanEvalFY19{0}'.format(x) for x in ('51', '57', '63'))

    _fluency_campaigns = ('HumanEvalFY19{0}'.format(x) for x in ('52', '58', '64'))

    if campaign.campaignName in _reference_campaigns:
        reference_label = 'Reference text'
        candidate_label = 'Candidate translation'
        priming_question_text = (
            'How accurately does the above candidate text convey the original '
            'semantics of the reference text? Slider ranges from '
            '<em>Not at all</em> (left) to <em>Perfectly</em> (right).'
        )

    elif campaign.campaignName in _adequacy_campaigns:
        reference_label = 'Candidate A'
        candidate_label = 'Candidate B'
        priming_question_text = (
            'How accurately does candidate text B convey the original '
            'semantics of candidate text A? Slider ranges from '
            '<em>Not at all</em> (left) to <em>Perfectly</em> (right).'
        )

    elif campaign.campaignName in _fluency_campaigns:
        reference_label = 'Candidate A'
        candidate_label = 'Candidate B'
        priming_question_text = (
            'Which of the two candidate texts is more fluent? Slider marks '
            'preference for <em>Candidate A</em> (left), no difference '
            '(middle) or preference for <em>Candidate B</em> (right).'
        )

    campaign_opts = campaign.campaignOptions or ""
    if 'sqm' in campaign_opts.lower():
        html_file = 'EvalView/direct-assessment-sqm.html'
    else:
        html_file = 'EvalView/direct-assessment-context.html'

    context = {
        'active_page': 'direct-assessment',
        'reference_label': reference_label,
        'reference_text': current_item.sourceText,
        'candidate_label': candidate_label,
        'candidate_text': current_item.targetText,
        'priming_question_text': priming_question_text,
        'item_id': current_item.itemID,
        'task_id': current_item.id,
        'completed_blocks': completed_blocks,
        'items_left_in_block': 10 - (completed_items - completed_blocks * 10),
        'source_language': source_language,
        'target_language': target_language,
        'debug_times': (t2 - t1, t3 - t2, t4 - t3, t4 - t1),
        'template_debug': 'debug' in request.GET,
        'campaign': campaign.campaignName,
        'datask_id': current_task.id,
        'trusted_user': current_task.is_trusted_user(request.user),
    }
    context.update(BASE_CONTEXT)

    return render(request, html_file, context)


# pylint: disable=C0103,C0330
@login_required
def direct_assessment_context(request, code=None, campaign_name=None):
    """
    Direct assessment context annotation view.
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

    LOGGER.info(
        'Rendering direct assessment context view for user "%s".',
        request.user.username or "Anonymous",
    )

    current_task = None

    # Try to identify TaskAgenda for current user.
    agendas = TaskAgenda.objects.filter(user=request.user)

    if campaign:
        agendas = agendas.filter(campaign=campaign)

    for agenda in agendas:
        LOGGER.info('Identified work agenda %s', agenda)

        tasks_to_complete = []
        for serialized_open_task in agenda.serialized_open_tasks():
            open_task = serialized_open_task.get_object_instance()

            # Skip tasks which are not available anymore
            if open_task is None:
                continue

            if open_task.next_item_for_user(request.user) is not None:
                current_task = open_task
                if not campaign:
                    campaign = agenda.campaign
            else:
                tasks_to_complete.append(serialized_open_task)

        modified = False
        for task in tasks_to_complete:
            modified = agenda.complete_open_task(task) or modified

        if modified:
            agenda.save()

    if not current_task and agendas.count() > 0:
        LOGGER.info('Work agendas completed, redirecting to dashboard')
        LOGGER.info('- code=%s, campaign=%s', code, campaign)
        return redirect('dashboard')

    # If language code has been given, find a free task and assign to user.
    if not current_task:
        current_task = DirectAssessmentContextTask.get_task_for_user(user=request.user)

    if not current_task:
        if code is None or campaign is None:
            LOGGER.info('No current task detected, redirecting to dashboard')
            LOGGER.info('- code=%s, campaign=%s', code, campaign)
            return redirect('dashboard')

        LOGGER.info(
            'Identifying next task for code "%s", campaign="%s"',
            code,
            campaign,
        )
        next_task = DirectAssessmentContextTask.get_next_free_task_for_language(
            code, campaign, request.user
        )

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
        document_id = request.POST.get('document_id', None)
        start_timestamp = request.POST.get('start_timestamp', None)
        end_timestamp = request.POST.get('end_timestamp', None)
        LOGGER.info('score=%s, item_id=%s', score, item_id)
        if score and item_id and start_timestamp and end_timestamp:
            duration = float(end_timestamp) - float(start_timestamp)
            LOGGER.debug(float(start_timestamp))
            LOGGER.debug(float(end_timestamp))
            LOGGER.info(
                'start=%s, end=%s, duration=%s',
                start_timestamp,
                end_timestamp,
                duration,
            )

            current_item = current_task.next_item_for_user(request.user)
            if (
                current_item.itemID != int(item_id)
                or current_item.id != int(task_id)
                or current_item.documentID != document_id
            ):
                _msg = 'Item ID %s does not match item %s, will not save!'
                LOGGER.debug(_msg, item_id, current_item.itemID)

            else:
                utc_now = datetime.utcnow().replace(tzinfo=utc)

                # pylint: disable=E1101
                DirectAssessmentContextResult.objects.create(
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
        request.user, return_completed_items=True
    )
    if not current_item:
        LOGGER.info('No current item detected, redirecting to dashboard')
        return redirect('dashboard')

    # completed_items_check = current_task.completed_items_for_user(
    #     request.user)
    completed_blocks = int(completed_items / 10)
    _msg = 'completed_items=%s, completed_blocks=%s'
    LOGGER.info(_msg, completed_items, completed_blocks)

    source_language = current_task.marketSourceLanguage()
    target_language = current_task.marketTargetLanguage()

    t4 = datetime.now()

    # Define priming question
    #
    # Default:
    #   How accurately does the above candidate text convey the original
    #   semantics of the source text? Slider ranges from
    #   <em>Not at all</em> (left) to <em>Perfectly</em> (right).
    #
    # We currently allow specific overrides, based on campaign name.
    reference_label = 'Source text'
    candidate_label = 'Candidate translation'
    priming_question_text = (
        'How accurately does the above candidate text convey the original '
        'semantics of the source text? Slider ranges from '
        '<em>Not at all</em> (left) to <em>Perfectly</em> (right).'
    )

    if current_item.isCompleteDocument:
        priming_question_text = (
            'How accurately does the above candidate document convey the '
            'original semantics of the source document? Slider ranges from '
            '<em>Not at all</em> (left) to <em>Perfectly</em> (right).'
        )

    _reference_campaigns = ('HumanEvalFY19{0}'.format(x) for x in ('7B',))

    _adequacy_campaigns = ('HumanEvalFY19{0}'.format(x) for x in ('51', '57', '63'))

    _fluency_campaigns = ('HumanEvalFY19{0}'.format(x) for x in ('52', '58', '64'))

    if campaign.campaignName in _reference_campaigns:
        reference_label = 'Reference text'
        candidate_label = 'Candidate translation'
        priming_question_text = (
            'How accurately does the above candidate text convey the original '
            'semantics of the reference text? Slider ranges from '
            '<em>Not at all</em> (left) to <em>Perfectly</em> (right).'
        )

    elif campaign.campaignName in _adequacy_campaigns:
        reference_label = 'Candidate A'
        candidate_label = 'Candidate B'
        priming_question_text = (
            'How accurately does candidate text B convey the original '
            'semantics of candidate text A? Slider ranges from '
            '<em>Not at all</em> (left) to <em>Perfectly</em> (right).'
        )

    elif campaign.campaignName in _fluency_campaigns:
        reference_label = 'Candidate A'
        candidate_label = 'Candidate B'
        priming_question_text = (
            'Which of the two candidate texts is more fluent? Slider marks '
            'preference for <em>Candidate A</em> (left), no difference '
            '(middle) or preference for <em>Candidate B</em> (right).'
        )

    context = {
        'active_page': 'direct-assessment',
        'reference_label': reference_label,
        'reference_text': current_item.sourceText,
        'reference_context_left': None,  # current_item.sourceContextLeft,
        'reference_context_right': None,  # current_item.sourceContextRight,
        'candidate_label': candidate_label,
        'candidate_text': current_item.targetText,
        'candidate_context_left': None,  # current_item.targetContextLeft,
        'candidate_context_right': None,  # current_item.targetContextRight,
        'priming_question_text': priming_question_text,
        'item_id': current_item.itemID,
        'task_id': current_item.id,
        'document_id': current_item.documentID,
        'isCompleteDocument': current_item.isCompleteDocument,
        'completed_blocks': completed_blocks,
        'items_left_in_block': 10 - (completed_items - completed_blocks * 10),
        'source_language': source_language,
        'target_language': target_language,
        'debug_times': (t2 - t1, t3 - t2, t4 - t3, t4 - t1),
        'template_debug': 'debug' in request.GET,
        'campaign': campaign.campaignName,
        'datask_id': current_task.id,
        'trusted_user': current_task.is_trusted_user(request.user),
    }
    context.update(BASE_CONTEXT)

    return render(request, 'EvalView/direct-assessment-context.html', context)


# pylint: disable=C0103,C0330
@login_required
def direct_assessment_document(request, code=None, campaign_name=None):
    """
    Direct assessment document annotation view.
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

    LOGGER.info(
        'Rendering direct assessment document view for user "%s".',
        request.user.username or "Anonymous",
    )

    current_task = None

    # Try to identify TaskAgenda for current user.
    agendas = TaskAgenda.objects.filter(user=request.user)

    if campaign:
        agendas = agendas.filter(campaign=campaign)

    for agenda in agendas:
        LOGGER.info('Identified work agenda %s', agenda)

        tasks_to_complete = []
        for serialized_open_task in agenda.serialized_open_tasks():
            open_task = serialized_open_task.get_object_instance()

            # Skip tasks which are not available anymore
            if open_task is None:
                continue

            if open_task.next_item_for_user(request.user) is not None:
                current_task = open_task
                if not campaign:
                    campaign = agenda.campaign
            else:
                tasks_to_complete.append(serialized_open_task)

        modified = False
        for task in tasks_to_complete:
            modified = agenda.complete_open_task(task) or modified

        if modified:
            agenda.save()

    if not current_task and agendas.count() > 0:
        LOGGER.info('Work agendas completed, redirecting to dashboard')
        LOGGER.info('- code=%s, campaign=%s', code, campaign)
        return redirect('dashboard')

    # If language code has been given, find a free task and assign to user.
    if not current_task:
        current_task = DirectAssessmentDocumentTask.get_task_for_user(user=request.user)

    if not current_task:
        if code is None or campaign is None:
            LOGGER.info('No current task detected, redirecting to dashboard')
            LOGGER.info('- code=%s, campaign=%s', code, campaign)
            return redirect('dashboard')

        LOGGER.info(
            'Identifying next task for code "%s", campaign="%s"',
            code,
            campaign,
        )
        next_task = DirectAssessmentDocumentTask.get_next_free_task_for_language(
            code, campaign, request.user
        )

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

    # Handling POST requests differs from the original direct_assessment/
    # direct_assessment_context view, but the input is the same: a score for the
    # single submitted item
    t2 = datetime.now()
    ajax = False
    item_saved = False
    error_msg = ''
    if request.method == "POST":
        score = request.POST.get('score', None)
        item_id = request.POST.get('item_id', None)
        task_id = request.POST.get('task_id', None)
        document_id = request.POST.get('document_id', None)
        start_timestamp = request.POST.get('start_timestamp', None)
        end_timestamp = request.POST.get('end_timestamp', None)
        ajax = bool(request.POST.get('ajax', None) == 'True')

        LOGGER.info('score=%s, item_id=%s', score, item_id)
        print(
            'Got request score={0}, item_id={1}, ajax={2}'.format(score, item_id, ajax)
        )

        # If all required information was provided in the POST request
        if score and item_id and start_timestamp and end_timestamp:
            duration = float(end_timestamp) - float(start_timestamp)
            LOGGER.debug(float(start_timestamp))
            LOGGER.debug(float(end_timestamp))
            LOGGER.info(
                'start=%s, end=%s, duration=%s',
                start_timestamp,
                end_timestamp,
                duration,
            )

            # Get all items from the document that the submitted item belongs
            # to, and all already collected scores for this document
            (
                current_item,
                block_items,
                block_results,
            ) = current_task.next_document_for_user(
                request.user, return_statistics=False
            )

            # An item from the right document was submitted
            if current_item.documentID == document_id:
                # This is the item that we expected to be annotated first,
                # which means that there is no score for the current item, so
                # create new score
                if current_item.itemID == int(item_id) and current_item.id == int(
                    task_id
                ):

                    utc_now = datetime.utcnow().replace(tzinfo=utc)
                    # pylint: disable=E1101
                    DirectAssessmentDocumentResult.objects.create(
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
                    print('Item {} (itemID={}) saved'.format(task_id, item_id))
                    item_saved = True

                # It is not the current item, so check if the result for it
                # exists
                else:
                    # Check if there is a score result for the submitted item
                    # TODO: this could be a single query, would it be better or
                    # more effective?
                    current_result = None
                    for result in block_results:
                        if not result:
                            continue
                        if result.item.itemID == int(item_id) and result.item.id == int(
                            task_id
                        ):
                            current_result = result
                            break

                    # If already scored, update the result
                    # TODO: consider adding new score, not updating the
                    # previous one
                    if current_result:
                        prev_score = current_result.score
                        current_result.score = score
                        current_result.start_time = float(start_timestamp)
                        current_result.end_time = float(end_timestamp)
                        utc_now = datetime.utcnow().replace(tzinfo=utc)
                        current_result.dateCompleted = utc_now
                        current_result.save()
                        _msg = 'Item {} (itemID={}) updated {}->{}'.format(
                            task_id, item_id, prev_score, score
                        )
                        LOGGER.debug(_msg)
                        print(_msg)
                        item_saved = True

                    # If not yet scored, check if the submitted item is from
                    # the expected document. Note that document ID is **not**
                    # sufficient, because there can be multiple documents with
                    # the same ID in the task.
                    else:
                        found_item = False
                        for item in block_items:
                            if item.itemID == int(item_id) and item.id == int(task_id):
                                found_item = item
                                break

                        # The submitted item is from the same document as the
                        # first unannotated item. It is fine, so save it
                        if found_item:
                            utc_now = datetime.utcnow().replace(tzinfo=utc)
                            # pylint: disable=E1101
                            DirectAssessmentDocumentResult.objects.create(
                                score=score,
                                start_time=float(start_timestamp),
                                end_time=float(end_timestamp),
                                item=found_item,
                                task=current_task,
                                createdBy=request.user,
                                activated=False,
                                completed=True,
                                dateCompleted=utc_now,
                            )
                            _msg = 'Item {} (itemID={}) saved, although it was not the next item'.format(
                                task_id, item_id
                            )
                            LOGGER.debug(_msg)
                            print(_msg)
                            item_saved = True

                        else:
                            error_msg = (
                                'We did not expect this item to be submitted. '
                                'If you used backward/forward buttons in your browser, '
                                'please reload the page and try again.'
                            )

                            _msg = 'Item ID {} does not match item {}, will not save!'.format(
                                item_id, current_item.itemID
                            )
                            LOGGER.debug(_msg)
                            print(_msg)

            # An item from a wrong document was submitted
            else:
                print(
                    'Different document IDs: {} != {}, will not save!'.format(
                        current_item.documentID, document_id
                    )
                )

                error_msg = (
                    'We did not expect an item from this document to be submitted. '
                    'If you used backward/forward buttons in your browser, '
                    'please reload the page and try again.'
                )

    t3 = datetime.now()

    campaign_opts = (campaign.campaignOptions or "").lower()

    # Get all items from the document that the first unannotated item in the
    # task belongs to, and collect some additional statistics
    (
        current_item,
        completed_items,
        completed_blocks,
        completed_items_in_block,
        block_items,
        block_results,
        total_blocks,
    ) = current_task.next_document_for_user(request.user)

    if not current_item:
        LOGGER.info('No current item detected, redirecting to dashboard')
        return redirect('dashboard')

    # Get item scores from the latest corresponding results
    block_scores = []
    _prev_item = None
    for item, result in zip(block_items, block_results):
        item_scores = {
            'completed': bool(result and result.score > -1),
            'current_item': bool(item.id == current_item.id),
            'score': result.score if result else -1,
        }

        # This is a hot fix for a bug in the IWSLT2022 Isometric Task batches,
        # where the document ID wasn't correctly incremented.
        # TODO: delete after the campaign is finished or fix all documents in DB
        if (
            'iwslt2022isometric' in campaign_opts
            and item.isCompleteDocument
            and item.itemID != (_prev_item.itemID + 1)
        ):
            item.itemID += 1
            item.save()
            _msg = 'Self-repaired the document item {} for user {}'.format(
                item, request.user.username
            )
            print(_msg)
            LOGGER.info(_msg)

        block_scores.append(item_scores)
        _prev_item = item

    # completed_items_check = current_task.completed_items_for_user(
    #     request.user)
    _msg = 'completed_items=%s, completed_blocks=%s'
    LOGGER.info(_msg, completed_items, completed_blocks)

    source_language = current_task.marketSourceLanguage()
    target_language = current_task.marketTargetLanguage()

    t4 = datetime.now()

    reference_label = 'Source text'
    candidate_label = 'Candidate translation'

    priming_question_texts = [
        'Below you see a document with {0} sentences in {1} (left columns) '
        'and their corresponding candidate translations in {2} (right columns). '
        'Score each candidate sentence translation in the document context. '
        'You may revisit already scored sentences and update their scores at any time '
        'by clicking at a source text.'.format(
            len(block_items) - 1, source_language, target_language
        ),
        'Assess the translation quality answering the question: ',
        'How accurately does the candidate text (right column, in bold) convey the '
        'original semantics of the source text (left column) in the document context? ',
    ]
    document_question_texts = [
        'Please score the overall document translation quality (you can score '
        'the whole document only after scoring all individual sentences first).',
        'Assess the translation quality answering the question: ',
        'How accurately does the <strong>entire</strong> candidate document translation '
        'in {0} (right column) convey the original semantics of the source document '
        'in {1} (left column)? '.format(target_language, source_language),
    ]

    speech_translation = 'speechtranslation' in campaign_opts

    use_sqm = 'sqm' in campaign_opts
    if use_sqm:
        priming_question_texts = priming_question_texts[:1]
        document_question_texts = document_question_texts[:1]

    # Special instructions for IWSLT 2022 dialect task
    if 'iwslt2022dialectsrc' in campaign_opts:
        speech_translation = True
        priming_question_texts += [
            'Please take into consideration the following aspects when assessing the translation quality:',
            '<ul>'
            '<li>The document is part of a conversation thread between two speakers, '
            'and each segment starts with either "A:" or "B:" to indicate the '
            'speaker identity.</li>'
            '<li>Some segments may contain "%pw" or "% pw" -- these correspond to '
            'partial words in the speech and should be ignored during evaluation.</li>'
            '<li>Please ignore the lack of capitalization and punctuation. Also, '
            'please ignore "incorrect" grammar and focus more on the meaning: '
            'these segments are informal conversations, so grammatical rules are '
            'not so strict.</li>',
        ]
        if current_task.marketSourceLanguageCode() == "aeb":
            priming_question_texts[
                -1
            ] += '<li>The original source is Tunisian Arabic speech. There may be some variation in the transcription.</li>'
        priming_question_texts[-1] += '</ul>'

    # Special instructions for IWSLT 2022 isometric task
    if 'iwslt2022isometric' in campaign_opts:
        priming_question_texts += [
            'Please take into consideration the following aspects when assessing the translation quality:',
            '<ul>'
            '<li>The source texts come from transcribed video content published on YouTube.</li>'
            '<li>Transcribed sentences have been split into segments based on pauses in the audio. It may happen that a single source sentence is split into multiple segments.</li>'
            '<li>Please score each segment (including very short segments) individually with regard to the source segment and the surrounding context.</li>'
            '<li>Take into account both grammar and meaning when scoring the segments.</li>'
            '<li>Please pay attention to issues like repeated or new content in the candidate translation, which is not present in the source text.</li>'
            '</ul>',
        ]

    # A part of context used in responses to both Ajax and standard POST
    # requests
    context = {
        'active_page': 'direct-assessment-document',
        'item_id': current_item.itemID,
        'task_id': current_item.id,
        'document_id': current_item.documentID,
        'completed_blocks': completed_blocks,
        'total_blocks': total_blocks,
        'items_left_in_block': len(block_items) - completed_items_in_block,
        'source_language': source_language,
        'target_language': target_language,
        'debug_times': (t2 - t1, t3 - t2, t4 - t3, t4 - t1),
        'template_debug': 'debug' in request.GET,
        'campaign': campaign.campaignName,
        'datask_id': current_task.id,
        'trusted_user': current_task.is_trusted_user(request.user),
        'sqm': use_sqm,
        'speech': speech_translation,
    }

    if ajax:
        ajax_context = {'saved': item_saved, 'error_msg': error_msg}
        context.update(ajax_context)
        context.update(BASE_CONTEXT)
        return JsonResponse(context)  # Sent response to the Ajax POST request

    page_context = {
        'items': zip(block_items, block_scores),
        'reference_label': reference_label,
        'candidate_label': candidate_label,
        'priming_question_texts': priming_question_texts,
        'document_question_texts': document_question_texts,
    }
    context.update(page_context)
    context.update(BASE_CONTEXT)

    return render(request, 'EvalView/direct-assessment-document.html', context)


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

    LOGGER.info(
        'Rendering multimodal assessment view for user "%s".',
        request.user.username or "Anonymous",
    )

    current_task = None

    # Try to identify TaskAgenda for current user.
    agendas = TaskAgenda.objects.filter(user=request.user)

    if campaign:
        agendas = agendas.filter(campaign=campaign)

    for agenda in agendas:
        modified = False
        LOGGER.info('Identified work agenda %s', agenda)

        tasks_to_complete = []
        for serialized_open_task in agenda.serialized_open_tasks():
            open_task = serialized_open_task.get_object_instance()

            # Skip tasks which are not available anymore
            if open_task is None:
                continue

            if open_task.next_item_for_user(request.user) is not None:
                current_task = open_task
                if not campaign:
                    campaign = agenda.campaign
            else:
                tasks_to_complete.append(serialized_open_task)

        for task in tasks_to_complete:
            modified = agenda.complete_open_task(task) or modified

        if modified:
            agenda.save()

    if not current_task and agendas.count() > 0:
        LOGGER.info('Work agendas completed, redirecting to dashboard')
        LOGGER.info('- code=%s, campaign=%s', code, campaign)
        return redirect('dashboard')

    # If language code has been given, find a free task and assign to user.
    if not current_task:
        current_task = MultiModalAssessmentTask.get_task_for_user(user=request.user)

    if not current_task:
        if code is None or campaign is None:
            LOGGER.info('No current task detected, redirecting to dashboard')
            LOGGER.info('- code=%s, campaign=%s', code, campaign)
            return redirect('dashboard')

        _msg = 'Identifying next task for code "%s", campaign="%s"'
        LOGGER.info(_msg, code, campaign)
        next_task = MultiModalAssessmentTask.get_next_free_task_for_language(
            code, campaign, request.user
        )

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
            LOGGER.info(
                'start=%s, end=%s, duration=%s',
                start_timestamp,
                end_timestamp,
                duration,
            )

            current_item = current_task.next_item_for_user(request.user)
            if current_item.itemID != int(item_id) or current_item.id != int(task_id):
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
        request.user, return_completed_items=True
    )
    if not current_item:
        LOGGER.info('No current item detected, redirecting to dashboard')
        return redirect('dashboard')

    # completed_items_check = current_task.completed_items_for_user(
    #     request.user)
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
        'debug_times': (t2 - t1, t3 - t2, t4 - t3, t4 - t1),
        'template_debug': 'debug' in request.GET,
        'campaign': campaign.campaignName,
        'datask_id': current_task.id,
        'trusted_user': current_task.is_trusted_user(request.user),
    }
    context.update(BASE_CONTEXT)

    return render(request, 'EvalView/multimodal-assessment.html', context)


# pylint: disable=C0103,C0330
@login_required
def pairwise_assessment(request, code=None, campaign_name=None):
    """
    Pairwise direct assessment annotation view.
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

    LOGGER.info(
        'Rendering pairwise direct assessment view for user "%s".',
        request.user.username or "Anonymous",
    )

    current_task = None

    # Try to identify TaskAgenda for current user.
    agendas = TaskAgenda.objects.filter(user=request.user)

    if campaign:
        agendas = agendas.filter(campaign=campaign)

    for agenda in agendas:
        LOGGER.info('Identified work agenda %s', agenda)

        tasks_to_complete = []
        for serialized_open_task in agenda.serialized_open_tasks():
            open_task = serialized_open_task.get_object_instance()

            # Skip tasks which are not available anymore
            if open_task is None:
                continue

            if open_task.next_item_for_user(request.user) is not None:
                current_task = open_task
                if not campaign:
                    campaign = agenda.campaign
            else:
                tasks_to_complete.append(serialized_open_task)

        modified = False
        for task in tasks_to_complete:
            modified = agenda.complete_open_task(task) or modified

        if modified:
            agenda.save()

    if not current_task and agendas.count() > 0:
        LOGGER.info('Work agendas completed, redirecting to dashboard')
        LOGGER.info('- code=%s, campaign=%s', code, campaign)
        return redirect('dashboard')

    # If language code has been given, find a free task and assign to user.
    if not current_task:
        current_task = PairwiseAssessmentTask.get_task_for_user(user=request.user)

    if not current_task:
        if code is None or campaign is None:
            LOGGER.info('No current task detected, redirecting to dashboard')
            LOGGER.info('- code=%s, campaign=%s', code, campaign)
            return redirect('dashboard')

        LOGGER.info(
            'Identifying next task for code "%s", campaign="%s"',
            code,
            campaign,
        )
        next_task = PairwiseAssessmentTask.get_next_free_task_for_language(
            code, campaign, request.user
        )

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
        score1 = request.POST.get('score', None)  # TODO: score -> score1
        score2 = request.POST.get('score2', None)
        item_id = request.POST.get('item_id', None)
        task_id = request.POST.get('task_id', None)
        start_timestamp = request.POST.get('start_timestamp', None)
        end_timestamp = request.POST.get('end_timestamp', None)

        print('score1={0}, score2={1}, item_id={2}'.format(score1, score2, item_id))
        LOGGER.info('score1=%s, score2=%s, item_id=%s', score1, score2, item_id)

        if score1 and item_id and start_timestamp and end_timestamp:
            duration = float(end_timestamp) - float(start_timestamp)
            LOGGER.debug(float(start_timestamp))
            LOGGER.debug(float(end_timestamp))
            LOGGER.info(
                'start=%s, end=%s, duration=%s',
                start_timestamp,
                end_timestamp,
                duration,
            )

            current_item = current_task.next_item_for_user(request.user)
            if current_item.itemID != int(item_id) or current_item.id != int(task_id):
                _msg = 'Item ID %s does not match item %s, will not save!'
                LOGGER.debug(_msg, item_id, current_item.itemID)

            else:
                utc_now = datetime.utcnow().replace(tzinfo=utc)

                # pylint: disable=E1101
                PairwiseAssessmentResult.objects.create(
                    score1=score1,
                    score2=score2,
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
        request.user, return_completed_items=True
    )
    if not current_item:
        LOGGER.info('No current item detected, redirecting to dashboard')
        return redirect('dashboard')

    # completed_items_check = current_task.completed_items_for_user(
    #     request.user)
    completed_blocks = int(completed_items / 10)
    _msg = 'completed_items=%s, completed_blocks=%s'
    LOGGER.info(_msg, completed_items, completed_blocks)

    source_language = current_task.marketSourceLanguage()
    target_language = current_task.marketTargetLanguage()

    t4 = datetime.now()

    # Define priming question
    #
    # Default:
    #   How accurately does the above candidate text convey the original
    #   semantics of the source text? Slider ranges from
    #   <em>Not at all</em> (left) to <em>Perfectly</em> (right).
    #
    # We currently allow specific overrides, based on campaign name.
    reference_label = 'Source text'
    candidate1_label = 'Candidate translation (1)'
    candidate2_label = 'Candidate translation (2)'

    priming_question_text = (
        'How accurately does each of the candidate text(s) below convey '
        'the original semantics of the source text above?'
    )

    if current_item.has_context():
        # Added 'bolded' to avoid confusion with context sentences that are
        # displayed in a grey color.
        priming_question_text = (
            'How accurately does each of the candidate text(s) below convey '
            'the original semantics of the bolded source text above?'
        )

    (
        candidate1_text,
        candidate2_text,
    ) = current_item.target_texts_with_diffs()

    context = {
        'active_page': 'pairwise-assessment',
        'reference_label': reference_label,
        'reference_text': current_item.segmentText,
        'context_left': current_item.context_left(),
        'context_right': current_item.context_right(),
        'candidate_label': candidate1_label,
        'candidate_text': candidate1_text,
        'candidate2_label': candidate2_label,
        'candidate2_text': candidate2_text,
        'priming_question_text': priming_question_text,
        'item_id': current_item.itemID,
        'task_id': current_item.id,
        'completed_blocks': completed_blocks,
        'items_left_in_block': 10 - (completed_items - completed_blocks * 10),
        'source_language': source_language,
        'target_language': target_language,
        'debug_times': (t2 - t1, t3 - t2, t4 - t3, t4 - t1),
        'template_debug': 'debug' in request.GET,
        'campaign': campaign.campaignName,
        'datask_id': current_task.id,
        'trusted_user': current_task.is_trusted_user(request.user),
    }
    context.update(BASE_CONTEXT)

    campaign_opts = campaign.campaignOptions or ""
    if 'sqm' in campaign_opts.lower():
        html_file = 'EvalView/pairwise-assessment-sqm.html'
    else:
        html_file = 'EvalView/pairwise-assessment.html'

    return render(request, html_file, context)


# pylint: disable=C0103,C0330
@login_required
def data_assessment(request, code=None, campaign_name=None):
    """
    Direct data assessment annotation view.
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

    LOGGER.info(
        'Rendering direct assessment view for user "%s".',
        request.user.username or "Anonymous",
    )

    current_task = None

    # Try to identify TaskAgenda for current user.
    agendas = TaskAgenda.objects.filter(user=request.user)

    if campaign:
        agendas = agendas.filter(campaign=campaign)

    for agenda in agendas:
        LOGGER.info('Identified work agenda %s', agenda)

        tasks_to_complete = []
        for serialized_open_task in agenda.serialized_open_tasks():
            open_task = serialized_open_task.get_object_instance()

            # Skip tasks which are not available anymore
            if open_task is None:
                continue

            if open_task.next_item_for_user(request.user) is not None:
                current_task = open_task
                if not campaign:
                    campaign = agenda.campaign
            else:
                tasks_to_complete.append(serialized_open_task)

        modified = False
        for task in tasks_to_complete:
            modified = agenda.complete_open_task(task) or modified

        if modified:
            agenda.save()

    if not current_task and agendas.count() > 0:
        LOGGER.info('Work agendas completed, redirecting to dashboard')
        LOGGER.info('- code=%s, campaign=%s', code, campaign)
        return redirect('dashboard')

    # If language code has been given, find a free task and assign to user.
    if not current_task:
        current_task = DataAssessmentTask.get_task_for_user(user=request.user)

    if not current_task:
        if code is None or campaign is None:
            LOGGER.info('No current task detected, redirecting to dashboard')
            LOGGER.info('- code=%s, campaign=%s', code, campaign)
            return redirect('dashboard')

        LOGGER.info(
            'Identifying next task for code "%s", campaign="%s"',
            code,
            campaign,
        )
        next_task = DataAssessmentTask.get_next_free_task_for_language(
            code, campaign, request.user
        )

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
        rank = request.POST.get('rank', None)
        item_id = request.POST.get('item_id', None)
        task_id = request.POST.get('task_id', None)
        start_timestamp = request.POST.get('start_timestamp', None)
        end_timestamp = request.POST.get('end_timestamp', None)

        _msg = 'score={} rank={} item_id={}'.format(score, rank, item_id)
        LOGGER.info(_msg)
        print(_msg)

        if score is None:
            print('No score provided, will not save!')
        elif item_id and start_timestamp and end_timestamp:
            duration = float(end_timestamp) - float(start_timestamp)
            LOGGER.debug(float(start_timestamp))
            LOGGER.debug(float(end_timestamp))
            LOGGER.info(
                'start=%s, end=%s, duration=%s',
                start_timestamp,
                end_timestamp,
                duration,
            )

            current_item = current_task.next_item_for_user(request.user)
            if current_item.itemID != int(item_id) or current_item.id != int(task_id):
                _msg = 'Item ID %s does not match item %s, will not save!'
                LOGGER.debug(_msg, item_id, current_item.itemID)

            else:
                utc_now = datetime.utcnow().replace(tzinfo=utc)

                # pylint: disable=E1101
                DataAssessmentResult.objects.create(
                    score=score,
                    rank=rank,
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
        request.user, return_completed_items=True
    )
    if not current_item:
        LOGGER.info('No current item detected, redirecting to dashboard')
        return redirect('dashboard')

    completed_blocks = int(completed_items / 10)
    _msg = 'completed_items=%s, completed_blocks=%s'
    LOGGER.info(_msg, completed_items, completed_blocks)

    source_language = current_task.marketSourceLanguage()
    target_language = current_task.marketTargetLanguage()

    t4 = datetime.now()

    source_label = 'Source text'
    target_label = 'Translation'
    top_question_text = [
        'You are presented a fragment of a document in {} and {}. '.format(
            source_language, target_language
        ),
        'Please judge the quality of the translations (taking in to '
        'account aspects like adequacy, fluency, writing ability, '
        'orthography, style, misalignments, etc.) on a scale from '
        'poor (left) to perfect (right).',
    ]
    score_question_text = [
        'Question #1: '
        'What is the quality of the translations, taking in to '
        'account aspects like adequacy, fluency, writing ability, '
        'orthography, style, misalignments, etc.?'
    ]
    rank_question_text = [
        'Question #2: '
        'Do you think any part of the translated text (left or right) '
        'has been created by machine translation rather than written '
        'by a human?'
    ]

    # There should be exactly 4 ranks, otherwise change 'col-sm-3' in the HTML view.
    # Each tuple includes radio label and radio value.
    ranks = [
        ('Definitely machine-translated', 1),
        ('Possibly machine-translated', 2),
        ('Possibly human-written', 3),
        ('Definitely human-written', 4),
    ]

    parallel_data = list(current_item.get_sentence_pairs())

    campaign_opts = (campaign.campaignOptions or "").lower()
    use_sqm = 'sqm' in campaign_opts

    if any(opt in campaign_opts for opt in ['disablemtlabel', 'disablemtrank']):
        ranks = None
        rank_question_text = None
        score_question_text[0] = score_question_text[0][13:]  # remove 'Question #1: '

    context = {
        'active_page': 'data-assessment',
        'source_label': source_label,
        'target_label': target_label,
        'parallel_data': parallel_data,
        'top_question_text': top_question_text,
        'score_question_text': score_question_text,
        'rank_question_text': rank_question_text,
        'ranks': ranks,
        'sqm': use_sqm,
        'item_id': current_item.itemID,
        'task_id': current_item.id,
        'document_domain': current_item.documentDomain,
        'source_url': current_item.sourceURL,
        'target_url': current_item.targetURL,
        'completed_blocks': completed_blocks,
        'items_left_in_block': 10 - (completed_items - completed_blocks * 10),
        'source_language': source_language,
        'target_language': target_language,
        'debug_times': (t2 - t1, t3 - t2, t4 - t3, t4 - t1),
        'show_debug': 'debug' in request.GET,
        'campaign': campaign.campaignName,
        'datask_id': current_task.id,
        'trusted_user': current_task.is_trusted_user(request.user),
    }
    context.update(BASE_CONTEXT)

    return render(request, 'EvalView/data-assessment.html', context)
