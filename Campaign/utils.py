"""
Appraise evaluation framework

See LICENSE for usage details
"""
from hashlib import md5

from django.contrib.auth.models import User

from Campaign.models import Campaign, CampaignTeam
from EvalData.models import (
    DirectAssessmentTask,
    TaskAgenda,
    ObjectID,
    Market,
    Metadata,
)


def _create_uniform_task_map(annotators, tasks, redudancy):
    """
    Creates task maps, uniformly distributed across given annotators.
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
            task_id = (_current_task_id + annotator_task) % tasks
            _annotator_tasks.append(task_id)
            _current_task_id = task_id
        _current_task_id += 1
        _results.append(tuple(_annotator_tasks))

    return _results


def _identify_super_users():
    """
    Identify QuerySet of super users for the current Django instance.

    Raises CommandError if no super user can be found.
    """
    superusers = User.objects.filter(is_superuser=True)
    if not superusers.exists():
        _msg = 'Failure to identify superuser'
        raise CommandError(_msg)

    return superusers


def _process_market_and_metadata(language_pairs, owner, **kwargs):
    """
    Create Market and Metadata instances for given language pairs.

    Parameters:
    - language_pairs:list[tuple(str, str), ...] list of language pairs;
    - owner:User sets the creator/owner of Market and Metadata objects;
    - **kwargs allows to override defaults for other settings.
    """
    _context = dict(**kwargs)

    for _src, _tgt in language_pairs:
        _market = _get_or_create_market(
            source_code=_src,
            target_code=_tgt,
            domain_name=_context.get('domain_name', 'AppenFY19'),
            owner=owner,
        )

        _meta = _get_or_create_meta(
            market=_market,
            corpus_name=_context.get('corpus_name', 'AppenFY19'),
            version_info=_context.get('version_info', '1.0'),
            source=_context.get('source', 'official'),
            owner=owner,
        )


def _process_users(language_pairs, context):
    """
    Create User instances for given language pairs.

    Parameters:
    - language_pairs:list[tuple(str, str), ...] list of language pairs;
    - context:dict specifies additional context:
      CAMPAIGN_KEY, CAMPAIGN_NO, REDUNDANCY and TASKS_TO_ANNOTATORS.
    """
    CAMPAIGN_KEY = context.get('CAMPAIGN_KEY')
    CAMPAIGN_NO = context.get('CAMPAIGN_NO')
    _credentials = {}
    for _src, _tgt in language_pairs:
        _tasks_map = _get_tasks_map_for_language_pair(_src, _tgt, context)
        _annotators = len(_tasks_map)

        for user_id in range(_annotators):
            username = '{0}{1}{2:02x}{3:02x}'.format(
                _src, _tgt, CAMPAIGN_NO, user_id + 1
            )

            hasher = md5()
            hasher.update(username.encode('utf8'))
            hasher.update(CAMPAIGN_KEY.encode('utf8'))
            secret = hasher.hexdigest()[:8]

            if not User.objects.filter(username=username).exists():
                new_user = User.objects.create_user(
                    username=username, password=secret
                )
                new_user.save()

            _credentials[username] = secret

    return _credentials


def _process_campaign_teams(language_pairs, owner, context):
    """
    Adds User objects to CampaignTeam instances for given language pairs.

    Parameters:
    - language_pairs:list[tuple(str, str), ...] list of language pairs;
    - owner:User sets the creator/owner of related campaign objects;
    - context:dict specifies additional context:
      CAMPAIGN_NAME, CAMPAIGN_NO, REDUNDANCY and TASKS_TO_ANNOTATORS.
    """
    CAMPAIGN_NAME = context.get('CAMPAIGN_NAME')
    CAMPAIGN_NO = context.get('CAMPAIGN_NO')
    REDUNDANCY = context.get('REDUNDANCY')
    TASKS_TO_ANNOTATORS = context.get('TASKS_TO_ANNOTATORS')
    for _src, _tgt in language_pairs:
        try:
            _tasks_map = _get_tasks_map_for_language_pair(
                _src, _tgt, context
            )

        except (LookupError, ValueError) as _exc:
            self.stdout.write(str(_exc))
            continue

        _tasks = sum([len(x) for x in _tasks_map]) // REDUNDANCY
        _annotators = len(_tasks_map)

        campaign_team_object = _get_or_create_campaign_team(
            CAMPAIGN_NAME, owner, _tasks, _annotators
        )

        for user_id in range(_annotators):
            username = '{0}{1}{2:02x}{3:02x}'.format(
                _src, _tgt, CAMPAIGN_NO, user_id + 1
            )

            user_object = User.objects.get(username=username)
            if user_object not in campaign_team_object.members.all():
                print(
                    '{0} --> {1}'.format(
                        campaign_team_object.teamName, user_object.username
                    )
                )
                campaign_team_object.members.add(user_object)


def _get_tasks_map_for_language_pair(source_code, target_code, context):
    """
    Gets tasks-to-annotators map for given language pair.

    Parameter:
    - source_code:str specifies source language ISO 639-2/3 code;
    - target_code:str specifies target language ISO 639-2/3 code;
    - context:dict specifices REDUNDANCY and TASKS_TO_ANNOTATORS.

    Returns:
    - tasks_map:list[int] encodes number of annotators and assigned tasks.
    """
    TASKS_TO_ANNOTATORS = context.get('TASKS_TO_ANNOTATORS')
    REDUNDANCY = context.get('REDUNDANCY')
    _tasks_map = TASKS_TO_ANNOTATORS.get((source_code, target_code))
    if _tasks_map is None:
        _msg = 'No TASKS_TO_ANNOTATORS mapping for {0}'.format(
            (source_code, target_code)
        )
        raise LookupError(_msg)

    if sum([len(x) for x in _tasks_map]) % REDUNDANCY > 0:
        _msg = 'Bad TASKS_TO_ANNOTATORS mapping for {0}'.format(
            (source_code, target_code)
        )
        raise ValueError(_msg)

    return _tasks_map


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
