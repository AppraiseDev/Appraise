"""
Appraise evaluation framework

See LICENSE for usage details
"""
from collections import defaultdict
from collections import OrderedDict
from hashlib import md5
from json import JSONDecodeError
from json import load

from django.contrib.auth.models import User
from django.core.management.base import CommandError

from Campaign.models import Campaign
from Campaign.models import CampaignTeam
from Dashboard.models import LANGUAGE_CODES_AND_NAMES
from Dashboard.models import validate_language_code
from EvalData.models import CAMPAIGN_TASK_TYPES
from EvalData.models import Market
from EvalData.models import Metadata
from EvalData.models import ObjectID
from EvalData.models import TaskAgenda


def _create_uniform_task_map(annotators, tasks, redudancy):
    """
    Creates task maps, uniformly distributed across given annotators.
    Returns a list of tuples.
    """
    _total_tasks = tasks * redudancy
    if annotators == 0 or _total_tasks % annotators > 0:
        return None

    _tasks_per_annotator = _total_tasks // annotators

    _results = []
    _current_task_id = 0
    for _unused_annotator_id in range(annotators):
        _annotator_tasks = []
        for annotator_task in range(_tasks_per_annotator):
            task_id = (_current_task_id + annotator_task) % _total_tasks
            _annotator_tasks.append(task_id)
            _current_task_id = task_id
        _current_task_id += 1
        _results.append(tuple(_annotator_tasks))

    print('Uniform task map:', _results)
    return _results


def _create_linear_task_map(annotators, tasks, redudancy):
    """
    Creates task maps assigning batches to annotators in batch original order.
    If redundancy equals to the number of annotators, each annotator will have the same exact tasks assigned.
    Returns a list of tuples.
    """
    _total_tasks = tasks * redudancy
    if annotators == 0 or _total_tasks % annotators > 0:
        return None
    _tasks_per_annotator = _total_tasks // annotators

    _results = []
    _current_task_id = 0
    for _ in range(annotators):
        _annotator_tasks = []
        for _ in range(_tasks_per_annotator):
            _annotator_tasks.append(_current_task_id)
            _current_task_id = (_current_task_id + 1) % _total_tasks
        _results.append(tuple(_annotator_tasks))

    print('Linear task map:', _results)
    return _results


def _identify_super_users():
    """
    Identify QuerySet of super users for the current Django instance.

    Raises CommandError if no super user can be found.
    """
    superusers = User.objects.filter(is_superuser=True)
    if not superusers.exists():
        raise CommandError('Failure to identify superuser')

    return superusers


def _get_campaign_instance(campaign_name):
    """
    Gets campaign instance for given campaign name.

    Paramters:
    - campaign_name:str specifies name of Campaign instance.
    """
    _campaign = Campaign.objects.filter(campaignName=campaign_name)
    if not _campaign.exists():
        raise CommandError(
            'Campaign {0!r} does not exist. '.format(campaign_name)
            + 'No task agendas have been assigned. '
            'This message is expected if you are initializing a new campaign '
            'and have not created it in the admin panel. '
            'Create a new campaign or check for a misspelling and try again.'
        )

    return _campaign[0]


def _get_or_create_campaign_team(name, owner, tasks, redudancy):
    """
    Creates CampaignTeam instance, if it does not exist yet.

    Returns reference to CampaignTeam instance.
    """
    # pylint: disable-msg=no-member
    _cteam = CampaignTeam.objects.get_or_create(
        teamName=name,
        owner=owner,
        requiredAnnotations=100,  # (tasks * redudancy), # TODO: fix
        requiredHours=50,  # (tasks * redudancy) / 2,
        createdBy=owner,
    )
    _cteam[0].members.add(owner)
    _cteam[0].save()
    return _cteam[0]


def _get_or_create_market(source_code, target_code, domain_name, owner):
    """
    Creates Market instance, if it does not exist yet.

    Returns reference to Market instance.
    """
    # pylint: disable-msg=no-member
    _market, _unused_created_signal = Market.objects.get_or_create(
        sourceLanguageCode=source_code,
        targetLanguageCode=target_code,
        domainName=domain_name,
        createdBy=owner,
    )
    return _market


def _get_or_create_meta(market, corpus_name, version_info, source, owner):
    """
    Creates Meta instance, if it does not exist yet.

    Returns reference to Meta instance.
    """
    # pylint: disable-msg=no-member
    _meta, _unused_created_signal = Metadata.objects.get_or_create(
        market=market,
        corpusName=corpus_name,
        versionInfo=version_info,
        source=source,
        createdBy=owner,
    )
    return _meta


def _get_tasks_by_market(tasks, context):
    """
    Gets tasks by market, converting QuerySet to dictionary of lists of tasks.

    Assignment scheme:

    - T1 U1 U2
    - T2 U3 U4
    - T3 U1 U2
    - T4 U3 U4

    To assign this, we duplicate tasks, per market, based on REDUNDANCY

    Parameters:
    - tasks:QuerySet contains task instances to extract market keys for;
    - context:dict specifices CAMPAIGN_NO and REDUNDANCY.

    Raises:
    - CommandError in case of missing required key.

    Returns:
    - tasks_by_market:dict[list[str]] organises tasks by market.
    """
    required_keys = ('CAMPAIGN_NO', 'REDUNDANCY')
    _validate_required_keys(context, required_keys)

    # Hexadecimal ids are zero-prefixed and have at least two digits
    format_str = '{{0}}{{1:0{0}x}}'.format(
        max(len(hex(context.get('CAMPAIGN_NO'))[2:]), 2)
    )

    tasks_by_market = defaultdict(list)
    for task in tasks.order_by('id'):
        market_code = '{0}{1}'.format(
            task.marketSourceLanguageCode().replace('-', ''),
            task.marketTargetLanguageCode().replace('-', ''),
        )
        key = format_str.format(market_code.lower(), context.get('CAMPAIGN_NO'))
        tasks_by_market[key].append(task)

    for key in tasks_by_market.keys():
        _single_copy = list(tasks_by_market[key])
        tasks_by_market[key] = _single_copy * context.get("REDUNDANCY")

    return tasks_by_market


def _get_tasks_map_for_language_pair(source_code, target_code, context):
    """
    Gets tasks-to-annotators map for given language pair.

    Parameters:
    - source_code:str specifies source language ISO 639-2/3 code;
    - target_code:str specifies target language ISO 639-2/3 code;
    - context:dict specifices REDUNDANCY and TASKS_TO_ANNOTATORS.

    Raises:
    - CommandError in case of missing required key.

    Returns:
    - tasks_map:list[int] encodes number of annotators and assigned tasks.
    """
    required_keys = ('REDUNDANCY', 'TASKS_TO_ANNOTATORS')
    _validate_required_keys(context, required_keys)

    _tasks_map = context.get('TASKS_TO_ANNOTATORS').get((source_code, target_code))
    if _tasks_map is None:
        _msg = 'No TASKS_TO_ANNOTATORS mapping for {0}'.format(
            (source_code, target_code)
        )
        raise LookupError(_msg)

    if sum([len(x) for x in _tasks_map]) % context.get('REDUNDANCY') > 0:
        _msg = 'Bad TASKS_TO_ANNOTATORS mapping for {0}'.format(
            (source_code, target_code)
        )
        raise ValueError(_msg)

    return _tasks_map


def _load_campaign_manifest(json_path):
    """Loads campaign manifest data from JSON file.

    Parameters:
    - json_path:str specifies path to JSON file containing manifest.

    Raises:
    - CommandError in case of errors parsing/loading from JSON file.

    Returns:
    - campaign_data:dict[str]->any campaign data parsed from JSON file.
    """
    with open(json_path, encoding='utf-8') as json_file:
        try:
            campaign_data = load(json_file)

        except JSONDecodeError as exc:
            raise CommandError(exc)

        else:
            return campaign_data


def _identify_codes_for_key(key):
    """
    Given some market key, identifies source and target language codes.
    """
    key = key.lower()

    target_pos = 0
    source_code = ""
    for code in LANGUAGE_CODES_AND_NAMES:
        cmp_code = code.lower().replace('-', '')
        if key.startswith(cmp_code):
            if len(cmp_code) > len(source_code):
                source_code = code
                target_pos = len(cmp_code)

    key = key[target_pos:]
    target_code = ""
    for code in LANGUAGE_CODES_AND_NAMES:
        cmp_code = code.lower().replace('-', '')
        if key.startswith(cmp_code):
            if len(cmp_code) > len(target_code):
                target_code = code

    return (source_code, target_code)


def _map_tasks_to_users_by_market(tasks, usernames, context):
    """
    Map tasks to users, by market, and considering TASKS_TO_ANNOTATORS.

    Parameters:
    - tasks:QuerySet contains task instances to map to users;
    - usernames:list specifies user names for campaign;
    - context:dict specifices CAMPAIGN_NO, REDUNDANCY and TASKS_TO_ANNOTATORS.

    Raises:
    - CommandError in case of missing required key or tasks/users issues.

    Returns:
    - tasks_to_users:dict[list[tuple(User,Task)]] maps tasks to users.
    """
    required_keys = ('CAMPAIGN_NO', 'REDUNDANCY', 'TASKS_TO_ANNOTATORS')
    _validate_required_keys(context, required_keys)

    # Organise tasks by market
    tasks_by_market = _get_tasks_by_market(tasks, context)
    # print('Tasks by market:', {k:[x._generate_str_name() for x in xs] for k, xs in tasks_by_market.items()})

    # Create map containing pairs (user, task)
    tasks_to_users_map = defaultdict(list)

    for key in tasks_by_market:
        # Constrain set of users to those matching current market
        _usernames = (x for x in usernames if x.startswith(key))
        users = User.objects.filter(username__in=_usernames)

        source_code, target_code = _identify_codes_for_key(key)

        try:
            _tasks_map = _get_tasks_map_for_language_pair(
                source_code, target_code, context
            )

        except (LookupError, ValueError) as _exc:
            print(str(_exc))
            continue

        _tasks_for_current_key = tasks_by_market[key]

        # Check that len(_tasks_for_current_key) == sum([len(tasks_for_user)])
        _available_tasks = len(_tasks_for_current_key)
        _required_tasks = sum([len(x) for x in _tasks_map])
        if _available_tasks != _required_tasks:
            _msg = 'Mismatch of available/required tasks ({0} != {1})'.format(
                _available_tasks, _required_tasks
            )
            raise CommandError(_msg)

        for user, tasks_for_user in zip(users.order_by('id'), _tasks_map):
            batches_for_user = []
            for task_id in tasks_for_user:
                batches_for_user.append(_tasks_for_current_key[task_id].batchNo)
                tasks_to_users_map[key].append((_tasks_for_current_key[task_id], user))
            print(
                'Mapping task(s) to user:',
                source_code,
                target_code,
                user,
                'taskID=',
                tasks_for_user,
                'batchNo=',
                batches_for_user,
            )

    return tasks_to_users_map


def _process_campaign_agendas(usernames, context, only_activated=True):
    """
    Processes TaskAgenda instances for campaign specified by CAMPAIGN_NAME.

    Parameters:
    - usernames:list specifies user names for campaign;
    - context:dict specifices CAMPAIGN_NO, REDUNDANCY, TASKS_TO_ANNOTATORS and
      TASK_TYPE;
    - only_activated:bool only include activated tasks for agenda creation.

    Raises:
    - CommandError in case of missing required key.
    """
    required_keys = (
        'CAMPAIGN_NO',
        'REDUNDANCY',
        'TASKS_TO_ANNOTATORS',
        'TASK_TYPE',
    )
    _validate_required_keys(context, required_keys)

    # Get Campaign instance for campaign name
    _campaign = _get_campaign_instance(context.get('CAMPAIGN_NAME'))
    print('Identified Campaign {0!r}'.format(context.get('CAMPAIGN_NAME')))
    print('Task type: {}'.format(context['TASK_TYPE']))

    # Get all tasks for this campaign
    _task_type = CAMPAIGN_TASK_TYPES[context['TASK_TYPE']]
    tasks = _task_type.objects.filter(campaign=_campaign)
    print('Identified {} task(s)'.format(len(tasks)))

    # Constrain to only activated, if requested
    if only_activated:
        tasks = tasks.filter(activated=True)
        print('Identified {} activated task(s)'.format(len(tasks)))

    # Map tasks to users, by market, and considering TASKS_TO_ANNOTATORS
    tasks_to_users_map = _map_tasks_to_users_by_market(tasks, usernames, context)

    for key in tasks_to_users_map:
        print('[{0}]'.format(key))
        for task, user in tasks_to_users_map[key]:
            print(user, '-->', task.id)

            agenda = TaskAgenda.objects.filter(user=user, campaign=_campaign)

            if not agenda.exists():
                agenda = TaskAgenda.objects.create(user=user, campaign=_campaign)
            else:
                agenda = agenda[0]

            serialized_t = ObjectID.objects.get_or_create(
                typeName=_task_type.__name__, primaryID=task.id
            )

            # Only process current task if it is new
            if agenda.contains_task(serialized_t[0]):
                continue

            _task_done_for_user = task.next_item_for_user(user) is None
            if _task_done_for_user:
                agenda.complete_task(serialized_t[0])

            else:
                agenda.activate_task(serialized_t[0])


def _process_campaign_teams(language_pairs, owner, context):
    """
    Adds User objects to CampaignTeam instances for given language pairs.

    Parameters:
    - language_pairs:list[tuple(str, str), ...] list of language pairs;
    - owner:User sets the creator/owner of related campaign objects;
    - context:dict specifies additional context:
      CAMPAIGN_NAME, CAMPAIGN_NO, REDUNDANCY and TASKS_TO_ANNOTATORS.

    Raises:
    - CommandError in case of missing required key.
    """
    required_keys = (
        'CAMPAIGN_NAME',
        'CAMPAIGN_NO',
        'REDUNDANCY',
        'TASKS_TO_ANNOTATORS',
    )
    _validate_required_keys(context, required_keys)

    for _src, _tgt in language_pairs:
        try:
            _tasks_map = _get_tasks_map_for_language_pair(_src, _tgt, context)

        except (LookupError, ValueError) as _exc:
            print(str(_exc))
            continue

        _tasks = sum([len(x) for x in _tasks_map]) // context.get('REDUNDANCY')
        _annotators = len(_tasks_map)

        campaign_team_object = _get_or_create_campaign_team(
            context.get('CAMPAIGN_NAME'), owner, _tasks, _annotators
        )

        # Hexadecimal ids are zero-prefixed and have at least two digits
        format_str = '{{0}}{{1}}{{2:0{0}x}}{{3:0{1}x}}'.format(
            max(len(hex(context.get('CAMPAIGN_NO'))[2:]), 2),
            max(len(hex(_annotators)[2:]), 2),
        )

        for user_id in range(_annotators):
            username = format_str.format(
                _src.lower().replace('-', ''),
                _tgt.lower().replace('-', ''),
                context.get('CAMPAIGN_NO'),
                user_id + 1,
            )

            user_object = User.objects.get(username=username)
            if user_object not in campaign_team_object.members.all():
                print(
                    '{0} --> {1}'.format(
                        campaign_team_object.teamName, user_object.username
                    )
                )
                campaign_team_object.members.add(user_object)


def _process_market_and_metadata(language_pairs, owner, **kwargs):
    """
    Create Market and Metadata instances for given language pairs.

    Parameters:
    - language_pairs:list[tuple(str, str), ...] list of language pairs;
    - owner:User sets the creator/owner of Market and Metadata objects;
    - **kwargs allows to override defaults for other settings.
    """
    _context = dict(**kwargs)

    markets_and_metadata = []
    for _src, _tgt in language_pairs:
        _market = _get_or_create_market(
            source_code=_src,
            target_code=_tgt,
            domain_name=_context.get('domain_name', 'UNDEFINED'),
            owner=owner,
        )

        _meta = _get_or_create_meta(
            market=_market,
            corpus_name=_context.get('corpus_name', 'UNDEFINED'),
            version_info=_context.get('version_info', '1.0'),
            source=_context.get('source', 'official'),
            owner=owner,
        )
        markets_and_metadata.append((_market, _meta))
    return markets_and_metadata


def _process_users(language_pairs, context):
    """
    Create User instances for given language pairs.

    Parameters:
    - language_pairs:list[tuple(str, str), ...] list of language pairs;
    - context:dict specifies additional context:
      CAMPAIGN_KEY, CAMPAIGN_NO, REDUNDANCY and TASKS_TO_ANNOTATORS.
    """
    required_keys = ('CAMPAIGN_KEY', 'CAMPAIGN_NO')
    _validate_required_keys(context, required_keys)

    # Ordered dictionary is used to ensure stability in unit tests
    _credentials = OrderedDict()
    for _src, _tgt in language_pairs:
        _tasks_map = _get_tasks_map_for_language_pair(_src, _tgt, context)
        _annotators = len(_tasks_map)

        # Hexadecimal ids are zero-prefixed and have at least two digits
        format_str = '{{0}}{{1}}{{2:0{0}x}}{{3:0{1}x}}'.format(
            max(len(hex(context.get('CAMPAIGN_NO'))[2:]), 2),
            max(len(hex(_annotators)[2:]), 2),
        )

        for user_id in range(_annotators):
            username = format_str.format(
                _src.lower().replace('-', ''),
                _tgt.lower().replace('-', ''),
                context.get('CAMPAIGN_NO'),
                user_id + 1,
            )

            hasher = md5()
            hasher.update(username.encode('utf8'))
            hasher.update(context.get('CAMPAIGN_KEY').encode('utf8'))
            secret = hasher.hexdigest()[:8]

            if not User.objects.filter(username=username).exists():
                new_user = User.objects.create_user(username=username, password=secret)
                new_user.save()

            _credentials[username] = secret

    return _credentials


def _validate_language_codes(codes):
    """
    Checks that all language codes are valid.

    Parameters:
    - codes:tuple specifies language codes.

    Raises:
    - CommandError in case of invalid language code.
    """
    for code in codes:
        if not validate_language_code(code):
            raise CommandError('{0!r} contains invalid language code!'.format(code))


def _validate_required_keys(context, required_keys):
    """
    Checks that all required keys exist in given context dict.

    Parameters:
    - context:dict specifies context dictionary;
    - required_keys:tuple[str] specifies set of required keys.

    Raises:
    - CommandError in case of missing required key.
    """
    for required_key in required_keys:
        if not required_key in context.keys():
            raise ValueError(
                'context does not contain required key {0!r}'.format(required_key)
            )
