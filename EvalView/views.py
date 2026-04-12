"""
Appraise evaluation framework

See LICENSE for usage details
"""

from datetime import datetime
from datetime import timezone

utc = timezone.utc

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect
from django.shortcuts import render
from django.utils.html import escape

from Appraise.settings import BASE_CONTEXT
from Appraise.utils import _get_logger
from Campaign.models import Campaign
from Dashboard.models import SIGN_LANGUAGE_CODES
from Dashboard.models import CHAR_BASED_LANGUAGE_CODES
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
from EvalData.models import PairwiseAssessmentDocumentResult
from EvalData.models import PairwiseAssessmentDocumentTask
from EvalData.models import PairwiseAssessmentResult
from EvalData.models import PairwiseAssessmentTask
from EvalData.models import ContrastiveAssessmentDocumentResult
from EvalData.models import ContrastiveAssessmentDocumentTask
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

        LOGGER.info(f'score={score}, item_id={item_id}')
        if not score or score == -1:
            LOGGER.debug(f"Score not submitted ({score}).")

        if score and item_id and start_timestamp and end_timestamp:
            duration = float(end_timestamp) - float(start_timestamp)
            LOGGER.debug(float(start_timestamp))
            LOGGER.debug(float(end_timestamp))
            LOGGER.info(
                f'start={start_timestamp,}, end={end_timestamp}, duration={duration}',
            )

            current_item = current_task.next_item_for_user(request.user)
            if current_item.itemID != int(item_id) or current_item.id != int(task_id):
                LOGGER.debug(
                    f'Item ID {item_id} does not match item {current_item.itemID}, will not save!'
                )
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

    campaign_opts = set((campaign.campaignOptions or "").lower().split(";"))

    if 'sqm' in campaign_opts:
        html_file = 'EvalView/direct-assessment-sqm.html'
    else:
        html_file = 'EvalView/direct-assessment-context.html'

    if 'namedentit' in campaign_opts:
        html_file = 'EvalView/direct-assessment-named-entities.html'

    if 'reference' in campaign_opts:
        reference_label = 'Reference text in {}'.format(target_language)
        candidate_label = 'Candidate translation in {}'.format(target_language)

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

    # hijack this function if it uses MQM
    campaign_opts = set((campaign.campaignOptions or "").lower().split(";"))
    if 'mqm' in campaign_opts or 'esa' in campaign_opts:
        return direct_assessment_document_mqmesa(campaign, current_task, request)

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
        print(f'Got request score={score}, item_id={item_id}, ajax={ajax}')

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

    # By default, source and target items are text segments
    source_item_type = 'text'
    target_item_type = 'text'
    reference_label = 'Source text'
    candidate_label = 'Candidate translation'

    monolingual_task = 'monolingual' in campaign_opts
    sign_translation = 'signlt' in campaign_opts
    speech_translation = 'speechtranslation' in campaign_opts
    static_context = 'staticcontext' in campaign_opts
    use_sqm = 'sqm' in campaign_opts
    scale_100 = 'scale100' in campaign_opts
    ui_language = 'enu'
    doc_guidelines = 'doclvlguideline' in campaign_opts

    error_types = None
    critical_error = None

    if 'wmt22signlt' in campaign_opts:
        sign_translation = True
        use_sqm = True
        ui_language = 'deu'

    if sign_translation:
        # For sign languages, source or target segments are videos
        if source_language in SIGN_LANGUAGE_CODES:
            source_item_type = 'video'
            reference_label = 'Source video'
        if target_language in SIGN_LANGUAGE_CODES:
            target_item_type = 'video'
            candidate_label = 'Candidate translation (video)'
        else:
            sign_translation = False  # disable sign-specific SQM instructions

    priming_question_texts = [
        '<p>'
        f'Below is a document in {source_language} and its translation into {target_language}, presented sentence by sentence. '
        'Your task is to rate each translation using the scale below, based on three criteria: <br/>'
        '</p>'
        '<p>'
        f'<strong>Naturalness</strong>: Does the translation sound fluent in {target_language}?<br/>'
        f'<strong>Accuracy</strong>: Does the translation correctly preserve the meaning of the source text?<br/>'
        f'<strong>Coherence</strong>: Does the sentence translation fit well in the document context?<br/>'
        '</p>'
    ]
    document_question_texts = [
        '<p>'
        'For the final step, please look again at the translated document. Provide one final, overall rating, judging it as a whole.'
        '</p>'
    ]

    if use_sqm:
        priming_question_texts = priming_question_texts[:1]
        document_question_texts = document_question_texts[:1]

    if monolingual_task:
        source_language = None

        priming_question_texts = [
            '<p>'
            f'Below is a document translated into {target_language}, presented sentence by sentence. '
            'Your task is to rate each translation using the scale below, based on two criteria: <br/>'
            '</p>'
            '<p>'
            f'<strong>Naturalness</strong>: Does the translation sound fluent in {target_language}?<br/>'
            f'<strong>Coherence</strong>: Does the sentence translation fit well in the document context?<br/>'
            '</p>'
        ]
        candidate_label = None

    if doc_guidelines:
        priming_question_texts = [
            'Below you see a document with {0} partial paragraphs in {1} (left columns) '
            'and their corresponding two candidate translations in {2} (middle and right column). '
            'Please score each paragraph of both candidate translations '
            '<u><b>paying special attention to document-level properties, '
            'such as consistency of style, selection of translation terms, formality, '
            'and so on</b></u>, in addition to the usual correctness criteria. '
            'Note that sentences in each paragraph may be separated by <i>&lt;eos&gt;</i> tags '
            'for convenience. These tags, if present, should not impact your assessment. '.format(
                len(block_items) - 1,
                source_language,
                target_language,
            ),
        ]

    # German instructions for WMT22 sign language task
    if 'wmt22signlt' in campaign_opts:
        if 'text2sign' in campaign_opts:
            priming_question_texts = [
                'Unten sehen Sie ein Dokument mit {0} Sätzen auf Deutsch (linke Spalten) '
                'und die entsprechenden möglichen Übersetzungen in Deutschschweizer '
                'Gebärdensprache (DSGS) (rechte Spalten). Bewerten Sie jede mögliche '
                'Übersetzung des Satzes im Kontext des Dokuments. '
                'Sie können bereits bewertete Sätze jederzeit durch Anklicken eines '
                'Quelltextes erneut aufrufen und die Bewertung aktualisieren.'.format(
                    len(block_items) - 1,
                ),
            ]
        elif 'sign2text-seglvl' in campaign_opts:
            priming_question_texts = [
                'Unten sehen Sie ein Set von {0} unzusammenhängenden Sätzen in Deutschschweizer '
                'Gebärdensprache (DSGS) (linke Spalten) und die entsprechenden möglichen '
                'Übersetzungen auf Deutsch (rechte Spalten). '
                'Sie können bereits bewertete Sätze jederzeit durch Anklicken eines '
                'Eingabevideos erneut aufrufen und die Bewertung aktualisieren.'.format(
                    len(block_items) - 1,
                ),
            ]
        else:
            priming_question_texts = [
                'Unten sehen Sie ein Dokument mit {0} Sätzen in Deutschschweizer '
                'Gebärdensprache (DSGS) (linke Spalten) und die entsprechenden möglichen '
                'Übersetzungen auf Deutsch (rechte Spalten). Bewerten Sie jede mögliche '
                'Übersetzung des Satzes im Kontext des Dokuments. '
                'Sie können bereits bewertete Sätze jederzeit durch Anklicken eines '
                'Eingabevideos erneut aufrufen und die Bewertung aktualisieren.'.format(
                    len(block_items) - 1,
                ),
            ]
        document_question_texts = [
            'Bitte bewerten Sie die Übersetzungsqualität des gesamten Dokuments. '
            '(Sie können das Dokument erst bewerten, nachdem Sie zuvor alle Sätze '
            'einzeln bewertet haben.)',
        ]

    # Special instructions for IWSLT 2022 dialect task
    if 'iwslt2022dialectsrc' in campaign_opts:
        speech_translation = True
        priming_question_texts += [
            'Please take into consideration the following aspects when assessing the translation quality:',
            '<ul>'
            '<li>The document is part of a conversation thread between two speakers, '
            'and each segment starts with either "A:" or "B:" to indicate the '
            'speaker identity.</li>'
            '<li>Some candidate translations may contain "%pw" or "% pw", but since they correspond to '
            'partial words in the speech they should not be considered as errors during evaluation.</li>'
            '<li>Please ignore the lack of capitalization and punctuation. Also, '
            'please ignore "incorrect" grammar and focus more on the meaning: '
            'these segments are informal conversations, so grammatical rules are '
            'not so strict.</li>',
        ]
        if current_task.marketSourceLanguageCode() == "aeb":
            priming_question_texts[-1] += (
                '<li>The original source is Tunisian Arabic speech. '
                + 'There may be some variation in the transcription.</li>'
            )
        priming_question_texts[-1] += '</ul>'

    # Special instructions for IWSLT 2022 isometric task
    if 'iwslt2022isometric' in campaign_opts:
        priming_question_texts += [
            'Please take into consideration the following aspects when assessing the translation quality:',
            '<ul>'
            '<li>The source texts come from transcribed video content published on YouTube.</li>'
            '<li>Transcribed sentences have been split into segments based on pauses in the audio. '
            'It may happen that a single source sentence is split into multiple segments.</li>'
            '<li>Please score each segment (including very short segments) individually with regard to '
            'the source segment and the surrounding context.</li>'
            '<li>Take into account both grammar and meaning when scoring the segments.</li>'
            '<li>Please pay attention to issues like repeated or new content in the candidate '
            'translation, which is not present in the source text.</li>'
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
        'source_item_type': source_item_type,
        'target_item_type': target_item_type,
        'debug_times': (t2 - t1, t3 - t2, t4 - t3, t4 - t1),
        'template_debug': 'debug' in request.GET,
        'campaign': campaign.campaignName,
        'datask_id': current_task.id,
        'trusted_user': current_task.is_trusted_user(request.user),
        # Task variations
        'errortypes': error_types,
        'criticalerror': critical_error,
        'monolingual': monolingual_task,
        'signlt': sign_translation,
        'speech': speech_translation,
        'static_context': static_context,
        'sqm': use_sqm,
        'ui_lang': ui_language,
        'scalar_slider': 'scalarslider' in campaign_opts or scale_100,
        'scale_100': scale_100,
        'collect_browser_info': 'collectbrowserinfo' in campaign_opts,
        'disable_mobile': 'disablemobile' in campaign_opts,
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


def direct_assessment_document_mqmesa(campaign, current_task, request):
    """
    Direct assessment document annotation view with MQM/ESA.
    """
    campaign_opts = set((campaign.campaignOptions or "").lower().split(";"))
    contrastive_esa = 'contrastiveesa' in campaign_opts
    wmt_layout = 'wmtlayout' in campaign_opts
    scale_100 = 'scale100' in campaign_opts
    if scale_100:
        wmt_layout = True

    # POST means that we want to store
    if request.method == "POST":
        score = request.POST.get('score', None)
        mqm = request.POST.get('mqm', None)
        item_id = request.POST.get('item_id', None)
        task_id = request.POST.get('task_id', None)
        start_timestamp = request.POST.get('start_timestamp', None)
        end_timestamp = request.POST.get('end_timestamp', None)
        ajax = bool(request.POST.get('ajax', None) == 'True')
        
        # Handle empty timestamp strings
        if not start_timestamp or start_timestamp == '':
            start_timestamp = datetime.now().timestamp()
        else:
            start_timestamp = float(start_timestamp)
            
        if not end_timestamp or end_timestamp == '':
            end_timestamp = datetime.now().timestamp()
        else:
            end_timestamp = float(end_timestamp)

        db_item = current_task.items.filter(
            itemID=item_id,
            id=task_id,
        )

        if len(db_item) == 0:
            error_msg = f'We could not find item {item_id} in task {task_id}.'
            LOGGER.error(error_msg)
            item_saved = False
        elif len(db_item) > 1:
            error_msg = (
                f'Found more than one item {item_id} in task {task_id}.'
                'This is from incorrectly set up batches'
            )
            LOGGER.error(error_msg)
            item_saved = False
        else:
            # Use update_or_create to prevent duplicate saves when items are
            # submitted multiple times (e.g., on Submit button click + Continue button click)
            result, created = DirectAssessmentDocumentResult.objects.update_or_create(
                item=list(db_item)[0],
                task=current_task,
                createdBy=request.user,
                defaults={
                    'score': score,
                    'mqm': mqm,
                    'start_time': start_timestamp,
                    'end_time': end_timestamp,
                    'activated': False,
                    'completed': True,
                    'dateCompleted': datetime.utcnow().replace(tzinfo=utc),
                }
            )
            action = 'created' if created else 'updated'
            error_msg = f'Item {task_id} (itemID={item_id}) {action}'
            LOGGER.info(error_msg)
            item_saved = True

        LOGGER.info(f'score={score}, item_id={item_id}, mqm={mqm}')
        print(f'Got request score={score}, item_id={item_id}, ajax={ajax}, mqm={mqm}')
    else:
        ajax = False

    # Get all items from the document that the first unannotated item in the
    # task belongs to, and collect some additional statistics
    if wmt_layout:
        # WMT layout uses all items in the task as a single "document"
        (
            next_item,
            items_completed,
            items_total,
            docs_completed,
            docs_total,
            doc_items,
            doc_items_results,
        ) = current_task.next_document_for_user_mqmesa(request.user)
    else:
        # Standard layout uses isCompleteDocument to determine document boundaries
        (
            next_item,
            completed_items,
            completed_blocks,
            completed_items_in_block,
            doc_items,
            doc_items_results,
            total_blocks,
        ) = current_task.next_document_for_user(request.user)
        
        # Calculate statistics for standard layout
        items_completed = completed_items
        items_total = current_task.items.count()
        docs_completed = completed_blocks
        docs_total = total_blocks

    if not next_item:
        if not ajax:
            LOGGER.info('No next item detected, redirecting to dashboard')
            return redirect('dashboard')
        else:
            context = {}
            ajax_context = {'saved': item_saved, 'error_msg': error_msg}
            context.update(ajax_context)
            context.update(BASE_CONTEXT)
            # Send response to the Ajax POST request
            return JsonResponse(context)

    # TODO: hotfix for WMT24 and WMT25
    # Tracking issue: https://github.com/AppraiseDev/Appraise/issues/185
    for item in doc_items:
        # don't escape HTML video, audio or images
        if (
            item.sourceText.strip().startswith("<video") or
            item.sourceText.strip().startswith("<audio") or
            item.sourceText.strip().startswith("<img")
        ):
            continue
        item.sourceText = escape(item.sourceText)

    # Get item scores from the latest corresponding results
    doc_items_results = [
        {
            'completed': bool(result and result.completed),
            'current_item': bool(item.id == next_item.id),
            # will be recomputed user-side anyway
            'score': result.score if result else -1,
            'mqm': result.mqm if result else item.mqm,
            'mqm_orig': item.mqm,
            'start_timestamp': result.start_time if result else "",
            'end_timestamp': result.end_time if result else "",
        }
        for item, result in zip(doc_items, doc_items_results)
    ]

    LOGGER.info(f'items_completed={items_completed}, docs_completed={docs_completed}')

    source_language = current_task.marketSourceLanguage()
    target_language = current_task.marketTargetLanguage()

    guidelines = (
        '<p>'
        f'Below you see a document in {source_language} and its translation in {target_language}. '
        'Your task:'
        '</p>'
        '<ol>'
        '<li>Read the source text and its proposed translations</li>'
        '<li>Highlight all translation errors in each translated segment.</li>'
        '<li>Rate each translated segment using the scale provided below.</li>'
        '</ol>'
    )
    if contrastive_esa:
        # escape <br/> tags in the source and target texts
        for item in doc_items:
            item.sourceText = item.sourceText.replace("&lt;eos&gt;", "<code>&lt;eos&gt;</code>").replace("&lt;br/&gt;", "<br/>")
            item.sourceText = item.sourceText.replace("\n", "<br/>")
            item.targetText = item.targetText.replace("\n", "<br/>")
        guidelines = (
            '<p>'
            f'Below you see a document in {source_language} and two different translations in {target_language}. '
            'Your task:'
            '<ol>'
            '<li>Read the source text and two competing translations.</li>'
            '<li>Highlight all translation errors in each translation.</li>'
            '<li>Rate each translation using the scale provided below.</li>'
            '</ol>'
            '</p>'
        )

    # A part of context used in responses to both Ajax and standard POST requests
    context = {
        'active_page': 'direct-assessment-document',
        'item_id': next_item.itemID,
        'task_id': next_item.id,
        'document_id': next_item.documentID,
        'items_completed': items_completed,
        'items_total': items_total,
        'docs_completed': docs_completed,
        'docs_total': docs_total,
        'items_left_in_block': len([item for item in doc_items if not item.isCompleteDocument]) - (completed_items_in_block if not wmt_layout else 0),
        'source_language': source_language,
        'target_language': target_language,
        'campaign': campaign.campaignName,
        # Task variations
        'ui_lang': "enu",
        'mqm_type': 'ESA' if 'esa' in campaign_opts else "MQM",
        'guidelines': guidelines,
        'scalar_slider': 'scalarslider' in campaign_opts or scale_100,
        'wmt_layout': wmt_layout,
        'scale_100': scale_100,
    }

    if ajax:
        ajax_context = {'saved': item_saved, 'error_msg': error_msg}
        context.update(ajax_context)
        context.update(BASE_CONTEXT)
        # Send response to the Ajax POST request
        return JsonResponse(context)

    page_context = {
        'items': list(zip(doc_items, doc_items_results)),
        'reference_label': 'Source text',
        'candidate_label': 'Candidate translation',
    }
    context.update(page_context)
    context.update(BASE_CONTEXT)

    if contrastive_esa:
        html_page = 'EvalView/direct-assessment-document-mqm-esa-contrastive.html'
    elif wmt_layout and not scale_100:
        html_page = 'EvalView/direct-assessment-document-mqm-esa-wmt.html'
    else:
        html_page = 'EvalView/direct-assessment-document-mqm-esa.html'
    return render(request, html_page, context)


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

        source_error = request.POST.get('source_error', None)
        error1 = request.POST.get('error1', None)
        error2 = request.POST.get('error2', None)

        metadata = request.POST.get('metadata', '{}')

        print(
            'score1={0}, score2={1}, item_id={2}, src_err={3}, error1={4}, error2={5}, metadata={6}'.format(
                score1, score2, item_id, source_error, error1, error2, metadata
            )
        )
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
                    sourceErrors=source_error,
                    errors1=error1,
                    errors2=error2,
                    metadata=metadata,
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
    target_language_code = current_task.marketTargetLanguageCode()

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

    # Check if target language is character-based (CJK, Thai, etc.)
    is_char_based = target_language_code in CHAR_BASED_LANGUAGE_CODES

    (
        candidate1_text,
        candidate2_text,
    ) = current_item.target_texts_with_diffs(char_based=is_char_based)

    campaign_opts = set((campaign.campaignOptions or "").lower().split(";"))

    use_sqm = False
    critical_error = False
    source_error = False
    extra_guidelines = False
    doc_guidelines = False
    guidelines_popup = False
    dialect_guidelines = False
    ui_v2 = False
    comments_required = False
    scalar_slider = False

    if 'reportcriticalerror' in campaign_opts:
        critical_error = True
        extra_guidelines = True
    if 'reportsourceerror' in campaign_opts:
        source_error = True
        extra_guidelines = True
    if 'sqm' in campaign_opts:
        use_sqm = True
        extra_guidelines = True
    if 'scalarslider' in campaign_opts:
        scalar_slider = True

    if 'v2' in campaign_opts:
        ui_v2 = True
    if 'requirecomment' in campaign_opts:
        comments_required = True

    if 'gamingdomainnote' in campaign_opts:
        priming_question_text = (
            'The presented text is a message from an online video game chat. '
            'Please take into account the video gaming genre when making your assessments. </br> '
            + priming_question_text
        )

    if extra_guidelines:
        # note this is not needed if DocLvlGuideline is enabled
        priming_question_text += '<br/> (Please see the detailed guidelines below)'

    if 'doclvlguideline' in campaign_opts:
        use_sqm = True
        doc_guidelines = True
        guidelines_popup = (
            'guidelinepopup' in campaign_opts or 'guidelinespopup' in campaign_opts
        )

    segment_text = current_item.segmentText

    if doc_guidelines:
        priming_question_text = (
            'Above you see a paragraph in {0} and below its corresponding one or two candidate translations in {1}. '
            'Please score the candidate translation(s) below following the detailed guidelines at the bottom of the page '
            '<u><b>paying special attention to document-level properties, '
            'such as consistency of style, selection of translation terms, formality, '
            'and so on</b></u>, in addition to the usual correctness criteria. '.format(
                source_language,
                target_language,
            )
        )

        # process <eos>s and unescape <br/>s
        segment_text = segment_text.replace(
            "&lt;eos&gt;", "<code>&lt;eos&gt;</code>"
        ).replace("&lt;br/&gt;", "<br/>")
        candidate1_text = candidate1_text.replace(
            "&lt;eos&gt;", "<code>&lt;eos&gt;</code>"
        ).replace("&lt;br/&gt;", "<br/>")
        candidate2_text = candidate2_text.replace(
            "&lt;eos&gt;", "<code>&lt;eos&gt;</code>"
        ).replace("&lt;br/&gt;", "<br/>")

    dialect_guidelines = any("dialectsguidelines" in opt for opt in campaign_opts)

    if dialect_guidelines:
        tgt_code = current_task.marketTargetLanguageCode()
        dialect = target_language

        # DialectsGuidelinesA asks for the main dialect for specific languages (fra, ptb, esn)
        if 'dialectsguidelinesa' in campaign_opts:
            if tgt_code == 'fra':
                dialect = "European French (Européen Français)"
            if tgt_code == 'por':
                dialect = "Brazilian Portuguese (Português do Brasil)"
            if tgt_code == 'spa':
                dialect = "European Spanish (Español Europeo)"
        # DialectsGuidelinesB asks for the secondary dialect for specific languages (frc, ptg, esj)
        elif 'dialectsguidelinesb' in campaign_opts:
            if tgt_code == 'fra':
                dialect = "Canadian French (Français Canadien)"
            if tgt_code == 'por':
                dialect = "European Portuguese (Português Europeu)"
            if tgt_code == 'spa':
                dialect = "Latin American Spanish (Español Latinoamericano)"

        # "If there are no significant differences between the candidates, please assign equal scores using the 'Match sliders' button. "
        priming_question_text = (
            "Above you see a segment in {0} and below its corresponding two candidate translations in {1}. "
            "Please evaluate the quality of the candidate translations, "
            "<b class='lang-emph'><u>focusing specifically on the use of the {2} dialect</u></b>. "
            "Pay close attention to dialect-specific language, including vocabulary, idiomatic expressions, and cultural references. "
            "<br/><br/>"
            "In addition to dialect-specific considerations, please also account for common translation errors, "
            "such as accuracy and fluency, as detailed below.".format(
                source_language,
                target_language,
                dialect,
            )
        )

    num_items_total = current_task.items.count()
    num_items_done = completed_items

    context = {
        'num_items_total': num_items_total,
        'num_items_done': num_items_done,
        'comments_required': comments_required,

        'active_page': 'pairwise-assessment',
        'reference_label': reference_label,
        'reference_text': segment_text,
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
        'sqm': use_sqm,
        'scalar_slider': scalar_slider,
        'critical_error': critical_error,
        'source_error': source_error,
        'guidelines_popup': guidelines_popup,
        'doc_guidelines': doc_guidelines,
    }
    context.update(BASE_CONTEXT)

    html_page = 'EvalView/pairwise-assessment-v2.html' if ui_v2 else 'EvalView/pairwise-assessment.html'
    return render(request, html_page, context)


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
        'You are presented a fragment of a document in {src} and {trg}. '.format(
            src=source_language, trg=target_language
        ),
        'Please judge the quality of the translations between the documents on a scale from poor (left) to perfect (right), '
        'taking in to account aspects like adequacy, fluency, writing ability, orthography, style, misalignments, etc. ',
        'Please consider these aspects in both the {src} and {trg} part. '
        'For example, poor fluency in the {src} fragment is a problem too. '
        'While you may use the context from the other sentences in the document, '
        'the translations need to be correct at the sentence level.'.format(
            src=source_language, trg=target_language
        ),
    ]
    score_question_text = [
        'Question #1: '
        'What is the quality of the translations, taking in to account aspects like '
        'adequacy, fluency, writing ability, orthography, style, misalignments, etc.?'
    ]
    rank_question_text = [
        'Question #2: '
        'Do you think any of the sentences ({src} or {trg}) '
        'were created by machine translation, rather than written by a human?'.format(
            src=source_language, trg=target_language
        ),
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

    campaign_opts = set((campaign.campaignOptions or "").lower().split(";"))
    use_sqm = 'sqm' in campaign_opts

    if any(opt in campaign_opts for opt in ['disablemtlabel', 'disablemtrank']):
        ranks = None
        rank_question_text = None
        # remove 'Question #1: '
        score_question_text[0] = score_question_text[0][13:]

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


# pylint: disable=C0103,C0330
@login_required
def pairwise_assessment_document(request, code=None, campaign_name=None):
    """
    Pairwise direct assessment document annotation view.
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
        current_task = PairwiseAssessmentDocumentTask.get_task_for_user(
            user=request.user
        )

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
        next_task = PairwiseAssessmentDocumentTask.get_next_free_task_for_language(
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
    # direct_assessment_context view
    t2 = datetime.now()
    ajax = False
    item_saved = False
    error_msg = ''
    if request.method == "POST":
        score1 = request.POST.get('score1', None)
        score2 = request.POST.get('score2', None)
        mqm1 = request.POST.get('mqm1', None)
        mqm2 = request.POST.get('mqm2', None)
        comment = request.POST.get('comment', '')
        item_id = request.POST.get('item_id', None)
        task_id = request.POST.get('task_id', None)
        document_id = request.POST.get('document_id', None)
        start_timestamp = request.POST.get('start_timestamp', None)
        end_timestamp = request.POST.get('end_timestamp', None)
        browser_info = request.POST.get('browser_info', None)
        ajax = bool(request.POST.get('ajax', None) == 'True')

        LOGGER.info('score1=%s, score2=%s, item_id=%s, mqm1=%s, mqm2=%s', score1, score2, item_id, mqm1, mqm2)
        print(
            'Got request score1={0}, score2={1}, item_id={2}, ajax={3}, mqm1={4}, mqm2={5}'.format(
                score1, score2, item_id, ajax, mqm1, mqm2
            )
        )

        # If all required information was provided in the POST request
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
                    result_data = {
                        'score1': score1,
                        'score2': score2,
                        'start_time': float(start_timestamp),
                        'end_time': float(end_timestamp),
                        'item': current_item,
                        'task': current_task,
                        'createdBy': request.user,
                        'activated': False,
                        'completed': True,
                        'dateCompleted': utc_now,
                    }
                    if browser_info:
                        result_data['browser_info'] = browser_info
                    if mqm1:
                        result_data['mqm1'] = mqm1
                    if mqm2:
                        result_data['mqm2'] = mqm2
                    if comment:
                        result_data['comment'] = comment
                    
                    PairwiseAssessmentDocumentResult.objects.create(**result_data)
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
                        prev_score1 = current_result.score1
                        prev_score2 = current_result.score2
                        current_result.score1 = score1
                        current_result.score2 = score2
                        current_result.start_time = float(start_timestamp)
                        current_result.end_time = float(end_timestamp)
                        if browser_info:
                            current_result.browser_info = browser_info
                        if mqm1:
                            current_result.mqm1 = mqm1
                        if mqm2:
                            current_result.mqm2 = mqm2
                        current_result.comment = comment
                        utc_now = datetime.utcnow().replace(tzinfo=utc)
                        current_result.dateCompleted = utc_now
                        current_result.save()
                        _msg = 'Item {} (itemID={}) updated {}->{} and {}->{}'.format(
                            task_id, item_id, prev_score1, score1, prev_score2, score2
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
                            result_data = {
                                'score1': score1,
                                'score2': score2,
                                'start_time': float(start_timestamp),
                                'end_time': float(end_timestamp),
                                'item': found_item,
                                'task': current_task,
                                'createdBy': request.user,
                                'activated': False,
                                'completed': True,
                                'dateCompleted': utc_now,
                            }
                            if browser_info:
                                result_data['browser_info'] = browser_info
                            if mqm1:
                                result_data['mqm1'] = mqm1
                            if mqm2:
                                result_data['mqm2'] = mqm2
                            if comment:
                                result_data['comment'] = comment
                            
                            PairwiseAssessmentDocumentResult.objects.create(**result_data)
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

    # Get target language code to determine if character-based tokenization is needed
    target_language_code = current_task.marketTargetLanguageCode()
    is_char_based = target_language_code in CHAR_BASED_LANGUAGE_CODES

    campaign_opts = set((campaign.campaignOptions or "").lower().split(";"))
    new_ui = 'newui' in campaign_opts
    escape_eos = 'escapeeos' in campaign_opts
    escape_br = 'escapebr' in campaign_opts
    highlight_style = 'highlightstyle' in campaign_opts
    scalar_slider = 'scalarslider' in campaign_opts
    scale_100 = 'scale100' in campaign_opts
    if scale_100:
        scalar_slider = True
    collect_browser_info = 'collectbrowserinfo' in campaign_opts
    disable_mobile = 'disablemobile' in campaign_opts
    pairwise_esa = 'pairwiseesa' in campaign_opts
    comments_seg = 'commentsseg' in campaign_opts
    comments_doc = 'commentsdoc' in campaign_opts
    
    print(f"DEBUG: campaign_opts={campaign_opts}")
    print(f"DEBUG: pairwise_esa={pairwise_esa}")
    print(f"DEBUG: target_language_code={target_language_code}, is_char_based={is_char_based}")
    print(f"DEBUG: comments_seg={comments_seg}, comments_doc={comments_doc}")

    # Get item scores from the latest corresponding results
    block_scores = []
    for item, result in zip(block_items, block_results):
        # Get target texts with injected HTML tags showing diffs
        _candidate1_text, _candidate2_text = item.target_texts_with_diffs(
            escape_html=not new_ui, char_based=is_char_based
        )
        if not new_ui:
            _source_text = escape(item.segmentText)
            _default_score = -1
        else:
            _source_text = item.segmentText
            _default_score = 50
        
        # Convert newlines to <br/> for proper rendering
        _source_text = _source_text.replace("\n", "<br/>")
        _candidate1_text = _candidate1_text.replace("\n", "<br/>")
        _candidate2_text = _candidate2_text.replace("\n", "<br/>")

        if escape_eos:
            _source_text = _source_text.replace(
                "&lt;eos&gt;", "<code>&lt;eos&gt;</code>"
            )
            _candidate1_text = _candidate1_text.replace(
                "&lt;eos&gt;", "<code>&lt;eos&gt;</code>"
            )
            _candidate2_text = _candidate2_text.replace(
                "&lt;eos&gt;", "<code>&lt;eos&gt;</code>"
            )

        if escape_br:
            _source_text = _source_text.replace("&lt;br/&gt;", "<br/>")
            _candidate1_text = _candidate1_text.replace("&lt;br/&gt;", "<br/>")
            _candidate2_text = _candidate2_text.replace("&lt;br/&gt;", "<br/>")

        item_scores = {
            'completed': bool(result and result.score1 > -1),
            'current_item': bool(item.id == current_item.id),
            'score1': result.score1 if result else _default_score,
            'score2': result.score2 if result else _default_score,
            'candidate1_text': _candidate1_text,
            'candidate2_text': _candidate2_text,
            'segment_text': _source_text,
            # Always initialize mqm1 and mqm2 for pairwise assessment document
            # to avoid undefined errors in the template
            'mqm1': '[]',
            'mqm2': '[]',
            'comment': '',
            'start_timestamp': '',
            'end_timestamp': '',
        }
        
        # Add MQM data for pairwise ESA if available
        if pairwise_esa:
            # Override with actual MQM data if it exists
            # Use getattr to safely handle cases where the field might not exist
            if result:
                mqm1_value = getattr(result, 'mqm1', None)
                mqm2_value = getattr(result, 'mqm2', None)
                
                # Debug logging
                print(f"DEBUG: result.id={result.id if result else 'None'}, mqm1_value={repr(mqm1_value)}, mqm2_value={repr(mqm2_value)}")
                
                # Use mqm1_value if it's a non-empty, non-None value
                if mqm1_value and mqm1_value != '[]':
                    item_scores['mqm1'] = mqm1_value
                elif mqm1_value == '[]':
                    # Keep the default '[]'
                    pass
                
                # Use mqm2_value if it's a non-empty, non-None value
                if mqm2_value and mqm2_value != '[]':
                    item_scores['mqm2'] = mqm2_value
                elif mqm2_value == '[]':
                    # Keep the default '[]'
                    pass
                
                item_scores['start_timestamp'] = result.start_time if result.start_time else ''
                item_scores['end_timestamp'] = result.end_time if result.end_time else ''

            if result:
                item_scores['comment'] = getattr(result, 'comment', '') or ''
        
        print(f"DEBUG: item_scores mqm1={repr(item_scores['mqm1'])}, mqm2={repr(item_scores['mqm2'])}")
        block_scores.append(item_scores)

    # completed_items_check = current_task.completed_items_for_user(
    #     request.user)
    _msg = 'completed_items=%s, completed_blocks=%s'
    LOGGER.info(_msg, completed_items, completed_blocks)

    source_language = current_task.marketSourceLanguage()
    target_language = current_task.marketTargetLanguage()

    t4 = datetime.now()

    reference_label = 'Source text'
    candidate1_label = 'Translation A'
    candidate2_label = 'Translation B'

    monolingual_task = 'monolingual' in campaign_opts
    use_sqm = 'sqm' in campaign_opts
    static_context = 'staticcontext' in campaign_opts
    doc_guidelines = 'doclvlguideline' in campaign_opts
    guidelines_popup = ('guidelinepopup' in campaign_opts or 'guidelinespopup' in campaign_opts)
    skip_doc_scores = 'skipdocumentscores' in campaign_opts
    slider_bubble = 'sliderbubble' in campaign_opts

    # new guidelines
    if not monolingual_task:
        priming_question_texts = [
            '<p>'
            f'Below is a document in {source_language} presented sentence by sentence. '
            f'Each source sentence has been translated by two different systems, A and B, into {target_language}. '
            'Your task is to rate each translation using the scale below, based on three criteria: <br/>'
            '</p>'
            '<p>'
            f'<strong>Naturalness</strong>: Does the translation sound fluent in {target_language}?<br/>'
            f'<strong>Accuracy</strong>: Does the translation correctly preserve the meaning of the source text?<br/>'
            f'<strong>Coherence</strong>: Does the sentence translation fit well in the document context?<br/>'
            '</p>'
        ]
    else:
        priming_question_texts = [
            '<p>'
            f'Below you see two document translations of a document from {source_language} into {target_language}, '
            'produced by systems A and B. '
            'Your task is to rate each translation using the scale below, based on two criteria: <br/>'
            '</p>'
            '<p>'
            f'<strong>Naturalness</strong>: Does the translation sound fluent in {target_language}?<br/>'
            f'<strong>Coherence</strong>: Does the sentence translation fit well in the document context?<br/>'
            '</p>'
        ]

    if pairwise_esa:
        if not monolingual_task:
            priming_question_texts = [
                '<p>'
                f'Below you see a document in {source_language} and two different translations in {target_language}. '
                'Your task:'
                '</p>'
                '<ol>'
                '<li>Read the source text and two competing translations.</li>'
                '<li>Highlight all translation errors in each translation.</li>'
                '<li>Rate each translation using the scale provided below.</li>'
                '</ol>'
            ]
        else:
            priming_question_texts = [
                '<p>'
                f'Below you see two different translations of a document from {source_language} into {target_language}, '
                'produced by systems A and B. '
                'Your task:'
                '</p>'
                '<ol>'
                '<li>Read two competing translations.</li>'
                '<li>Highlight all translation errors you notice in each translation.</li>'
                '<li>Rate each translation using the scale provided below.</li>'
                '</ol>'
            ]

    if skip_doc_scores:
        document_question_texts = []
    else:
        document_question_texts = [
            'For the final step, please look again at each translated document. ' 
            'Provide one final, overall rating for each translation candidate, judging it as a whole. '
        ]
    if use_sqm:
        priming_question_texts = priming_question_texts[:1]
        document_question_texts = document_question_texts[:1]

    if doc_guidelines:
        priming_question_texts = [
            'Below you see a document with {0} partial paragraphs in {1} (left columns) '
            'and their corresponding two candidate translations in {2} (middle and right column). '
            'Please score each paragraph of both candidate translations '
            '<u><b>paying special attention to document-level properties, '
            'such as consistency of formality and style, selection of translation terms, pronoun choice, '
            'and so on</b></u>, in addition to the usual correctness criteria. '.format(
                len(block_items) - 1,
                source_language,
                target_language,
            ),
        ]

    sentence_item_count = len([item for item in block_items if not item.isCompleteDocument])

    # A part of context used in responses to both Ajax and standard POST
    # requests
    context = {
        'active_page': 'pairwise-assessment-document',
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
        'monolingual': monolingual_task,
        'sqm': use_sqm,
        'scalar_slider': scalar_slider,
        'scale_100': scale_100,
        'static_context': static_context,
        'guidelines_popup': guidelines_popup,
        'doc_guidelines': doc_guidelines,
        'highlight_style': highlight_style,
        'sentence_item_count': sentence_item_count,
        'collect_browser_info': collect_browser_info,
        'disable_mobile': disable_mobile,
        'skip_doc_scores': skip_doc_scores,
        'slider_bubble': slider_bubble,
        'comments_seg': comments_seg,
        'comments_doc': comments_doc,
    }
    
    # Add ESA-specific context
    if pairwise_esa:
        context['mqm_type'] = 'ESA'  # Could check for 'mqm' in campaign_opts if needed
        context['items_completed'] = completed_items
        context['items_total'] = current_task.items.count()
        context['docs_completed'] = completed_blocks
        context['docs_total'] = total_blocks

    if ajax:
        ajax_context = {'saved': item_saved, 'error_msg': error_msg}
        context.update(ajax_context)
        context.update(BASE_CONTEXT)
        return JsonResponse(context)  # Sent response to the Ajax POST request

    page_context = {
        'items': zip(block_items, block_scores),
        'num_items': len(block_items),
        'reference_label': reference_label,
        'candidate1_label': candidate1_label,
        'candidate2_label': candidate2_label,
        'priming_question_texts': priming_question_texts,
        'document_question_texts': document_question_texts,
    }
    context.update(page_context)
    context.update(BASE_CONTEXT)

    if pairwise_esa:
        template = 'EvalView/pairwise-assessment-document-esa.html'
    elif new_ui:
        template = 'EvalView/pairwise-assessment-document-newui.html'
    else:
        template = 'EvalView/pairwise-assessment-document.html'
    return render(request, template, context)


@login_required
def contrastive_assessment_document(request, code=None, campaign_name=None):
    """
    Contrastive assessment document annotation view supporting up to 3 system
    outputs at once.
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
        'Rendering contrastive assessment document view for user "%s".',
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

    if not current_task:
        current_task = ContrastiveAssessmentDocumentTask.get_task_for_user(
            user=request.user
        )

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
        next_task = ContrastiveAssessmentDocumentTask.get_next_free_task_for_language(
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
    ajax = False
    item_saved = False
    error_msg = ''
    if request.method == "POST":
        score1 = request.POST.get('score1', None)
        score2 = request.POST.get('score2', None)
        score3 = request.POST.get('score3', None)
        mqm1 = request.POST.get('mqm1', None)
        mqm2 = request.POST.get('mqm2', None)
        mqm3 = request.POST.get('mqm3', None)
        comment = request.POST.get('comment', '')
        item_id = request.POST.get('item_id', None)
        task_id = request.POST.get('task_id', None)
        document_id = request.POST.get('document_id', None)
        start_timestamp = request.POST.get('start_timestamp', None)
        end_timestamp = request.POST.get('end_timestamp', None)
        browser_info = request.POST.get('browser_info', None)
        ajax = bool(request.POST.get('ajax', None) == 'True')

        LOGGER.info(
            'score1=%s, score2=%s, score3=%s, item_id=%s',
            score1, score2, score3, item_id,
        )

        if score1 and item_id and start_timestamp and end_timestamp:
            duration = float(end_timestamp) - float(start_timestamp)
            LOGGER.info(
                'start=%s, end=%s, duration=%s',
                start_timestamp, end_timestamp, duration,
            )

            (
                current_item,
                block_items,
                block_results,
            ) = current_task.next_document_for_user(
                request.user, return_statistics=False
            )

            if current_item.documentID == document_id:
                if current_item.itemID == int(item_id) and current_item.id == int(
                    task_id
                ):
                    utc_now = datetime.utcnow().replace(tzinfo=utc)
                    result_data = {
                        'score1': score1,
                        'score2': score2,
                        'score3': score3,
                        'start_time': float(start_timestamp),
                        'end_time': float(end_timestamp),
                        'item': current_item,
                        'task': current_task,
                        'createdBy': request.user,
                        'activated': False,
                        'completed': True,
                        'dateCompleted': utc_now,
                    }
                    if browser_info:
                        result_data['browser_info'] = browser_info
                    if mqm1:
                        result_data['mqm1'] = mqm1
                    if mqm2:
                        result_data['mqm2'] = mqm2
                    if mqm3:
                        result_data['mqm3'] = mqm3
                    if comment:
                        result_data['comment'] = comment

                    ContrastiveAssessmentDocumentResult.objects.create(**result_data)
                    item_saved = True

                else:
                    current_result = None
                    for result in block_results:
                        if not result:
                            continue
                        if result.item.itemID == int(item_id) and result.item.id == int(
                            task_id
                        ):
                            current_result = result
                            break

                    if current_result:
                        current_result.score1 = score1
                        current_result.score2 = score2
                        current_result.score3 = score3
                        current_result.start_time = float(start_timestamp)
                        current_result.end_time = float(end_timestamp)
                        if browser_info:
                            current_result.browser_info = browser_info
                        if mqm1:
                            current_result.mqm1 = mqm1
                        if mqm2:
                            current_result.mqm2 = mqm2
                        if mqm3:
                            current_result.mqm3 = mqm3
                        current_result.comment = comment
                        utc_now = datetime.utcnow().replace(tzinfo=utc)
                        current_result.dateCompleted = utc_now
                        current_result.save()
                        item_saved = True

                    else:
                        found_item = False
                        for item in block_items:
                            if item.itemID == int(item_id) and item.id == int(task_id):
                                found_item = item
                                break

                        if found_item:
                            utc_now = datetime.utcnow().replace(tzinfo=utc)
                            result_data = {
                                'score1': score1,
                                'score2': score2,
                                'score3': score3,
                                'start_time': float(start_timestamp),
                                'end_time': float(end_timestamp),
                                'item': found_item,
                                'task': current_task,
                                'createdBy': request.user,
                                'activated': False,
                                'completed': True,
                                'dateCompleted': utc_now,
                            }
                            if browser_info:
                                result_data['browser_info'] = browser_info
                            if mqm1:
                                result_data['mqm1'] = mqm1
                            if mqm2:
                                result_data['mqm2'] = mqm2
                            if mqm3:
                                result_data['mqm3'] = mqm3
                            if comment:
                                result_data['comment'] = comment

                            ContrastiveAssessmentDocumentResult.objects.create(**result_data)
                            item_saved = True

                        else:
                            error_msg = (
                                'We did not expect this item to be submitted. '
                                'If you used backward/forward buttons in your browser, '
                                'please reload the page and try again.'
                            )

            else:
                error_msg = (
                    'We did not expect an item from this document to be submitted. '
                    'If you used backward/forward buttons in your browser, '
                    'please reload the page and try again.'
                )

    t3 = datetime.now()

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

    target_language_code = current_task.marketTargetLanguageCode()
    is_char_based = target_language_code in CHAR_BASED_LANGUAGE_CODES

    campaign_opts = set((campaign.campaignOptions or "").lower().split(";"))
    scalar_slider = 'scalarslider' in campaign_opts
    scale_100 = 'scale100' in campaign_opts
    if scale_100:
        scalar_slider = True
    collect_browser_info = 'collectbrowserinfo' in campaign_opts
    disable_mobile = 'disablemobile' in campaign_opts
    contrastive_esa = 'esa' in campaign_opts
    comments_seg = 'commentsseg' in campaign_opts
    comments_doc = 'commentsdoc' in campaign_opts
    monolingual_task = 'monolingual' in campaign_opts
    use_sqm = 'sqm' in campaign_opts
    skip_doc_scores = 'skipdocumentscores' in campaign_opts
    slider_bubble = 'sliderbubble' in campaign_opts

    block_scores = []
    _default_score = -1
    for item, result in zip(block_items, block_results):
        _source_text = escape(item.segmentText)
        _candidate1_text = escape(item.target1Text) if item.target1Text else ''
        _candidate2_text = escape(item.target2Text) if item.target2Text else ''
        _candidate3_text = escape(item.target3Text) if item.target3Text else ''

        _source_text = _source_text.replace("\n", "<br/>")
        _candidate1_text = _candidate1_text.replace("\n", "<br/>")
        _candidate2_text = _candidate2_text.replace("\n", "<br/>")
        _candidate3_text = _candidate3_text.replace("\n", "<br/>")

        item_scores = {
            'completed': bool(result and result.score1 > -1),
            'current_item': bool(item.id == current_item.id),
            'score1': result.score1 if result else _default_score,
            'score2': result.score2 if result else _default_score,
            'score3': result.score3 if result else _default_score,
            'candidate1_text': _candidate1_text,
            'candidate2_text': _candidate2_text,
            'candidate3_text': _candidate3_text,
            'segment_text': _source_text,
            'mqm1': '[]',
            'mqm2': '[]',
            'mqm3': '[]',
            'comment': '',
            'start_timestamp': '',
            'end_timestamp': '',
        }

        diff_maps = item.compute_pairwise_diff_maps(char_based=is_char_based)
        item_scores.update(diff_maps)

        if result:
            if contrastive_esa:
                mqm1_value = getattr(result, 'mqm1', '[]')
                mqm2_value = getattr(result, 'mqm2', '[]')
                mqm3_value = getattr(result, 'mqm3', '[]')
                if mqm1_value and mqm1_value != '[]':
                    item_scores['mqm1'] = mqm1_value
                if mqm2_value and mqm2_value != '[]':
                    item_scores['mqm2'] = mqm2_value
                if mqm3_value and mqm3_value != '[]':
                    item_scores['mqm3'] = mqm3_value
            item_scores['comment'] = getattr(result, 'comment', '') or ''
            item_scores['start_timestamp'] = result.start_time if result.start_time else ''
            item_scores['end_timestamp'] = result.end_time if result.end_time else ''

        block_scores.append(item_scores)

    _msg = 'completed_items=%s, completed_blocks=%s'
    LOGGER.info(_msg, completed_items, completed_blocks)

    source_language = current_task.marketSourceLanguage()
    target_language = current_task.marketTargetLanguage()

    t4 = datetime.now()

    reference_label = 'Source text'
    candidate1_label = 'Translation A'
    candidate2_label = 'Translation B'
    candidate3_label = 'Translation C'

    if not monolingual_task:
        priming_question_texts = [
            '<p>'
            f'Below is a document in {source_language} presented sentence by sentence. '
            f'Each source sentence has been translated by three different systems, A, B, and C, into {target_language}. '
            'Your task is to rate each translation using the scale below, based on three criteria: <br/>'
            '</p>'
            '<p>'
            f'<strong>Naturalness</strong>: Does the translation sound fluent in {target_language}?<br/>'
            f'<strong>Accuracy</strong>: Does the translation correctly preserve the meaning of the source text?<br/>'
            f'<strong>Coherence</strong>: Does the sentence translation fit well in the document context?<br/>'
            '</p>'
        ]
    else:
        priming_question_texts = [
            '<p>'
            f'Below you see three document translations of a document from {source_language} into {target_language}, '
            'produced by systems A, B, and C. '
            'Your task is to rate each translation using the scale below, based on two criteria: <br/>'
            '</p>'
            '<p>'
            f'<strong>Naturalness</strong>: Does the translation sound fluent in {target_language}?<br/>'
            f'<strong>Coherence</strong>: Does the sentence translation fit well in the document context?<br/>'
            '</p>'
        ]

    if contrastive_esa:
        if not monolingual_task:
            priming_question_texts = [
                '<p>'
                f'Below you see a document in {source_language} and three different translations in {target_language}. '
                'Your task:'
                '</p>'
                '<ol>'
                '<li>Read the source text and three competing translations.</li>'
                '<li>Highlight all translation errors in each translation.</li>'
                '<li>Rate each translation using the scale provided below.</li>'
                '</ol>'
            ]
        else:
            priming_question_texts = [
                '<p>'
                f'Below you see three different translations of a document from {source_language} into {target_language}, '
                'produced by systems A, B, and C. '
                'Your task:'
                '</p>'
                '<ol>'
                '<li>Read three competing translations.</li>'
                '<li>Highlight all translation errors you notice in each translation.</li>'
                '<li>Rate each translation using the scale provided below.</li>'
                '</ol>'
            ]

    if skip_doc_scores:
        document_question_texts = []
    else:
        document_question_texts = [
            'For the final step, please look again at each translated document. '
            'Provide one final, overall rating for each translation candidate, judging it as a whole. '
        ]
    sentence_item_count = len([item for item in block_items if not item.isCompleteDocument])

    context = {
        'active_page': 'contrastive-assessment-document',
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
        'monolingual': monolingual_task,
        'sqm': use_sqm,
        'scalar_slider': scalar_slider,
        'scale_100': scale_100,
        'sentence_item_count': sentence_item_count,
        'collect_browser_info': collect_browser_info,
        'disable_mobile': disable_mobile,
        'skip_doc_scores': skip_doc_scores,
        'slider_bubble': slider_bubble,
        'comments_seg': comments_seg,
        'comments_doc': comments_doc,
        'contrastive_esa': contrastive_esa,
        'is_char_based': is_char_based,
    }

    if contrastive_esa:
        context['mqm_type'] = 'ESA'
        context['items_completed'] = completed_items
        context['items_total'] = current_task.items.count()
        context['docs_completed'] = completed_blocks
        context['docs_total'] = total_blocks

    if ajax:
        ajax_context = {'saved': item_saved, 'error_msg': error_msg}
        context.update(ajax_context)
        context.update(BASE_CONTEXT)
        return JsonResponse(context)

    page_context = {
        'items': zip(block_items, block_scores),
        'num_items': len(block_items),
        'reference_label': reference_label,
        'candidate1_label': candidate1_label,
        'candidate2_label': candidate2_label,
        'candidate3_label': candidate3_label,
        'priming_question_texts': priming_question_texts,
        'document_question_texts': document_question_texts,
    }
    context.update(page_context)
    context.update(BASE_CONTEXT)

    template = 'EvalView/contrastive-assessment-document.html'
    return render(request, template, context)
