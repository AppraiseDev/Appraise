"""
Appraise evaluation framework

See LICENSE for usage details
"""
from .base_models import *
from .data_assessment import *
from .direct_assessment import *
from .direct_assessment_context import *
from .direct_assessment_document import *
from .multi_modal_assessment import *
from .pairwise_assessment import *
from .task_agenda import *

# Task definitions: user-friendly name, task class, task result class, URL name
TASK_DEFINITIONS = (
    (
        'Direct',
        DirectAssessmentTask,
        DirectAssessmentResult,
        'direct-assessment',
    ),
    (
        'DocLevelDA',
        DirectAssessmentContextTask,
        DirectAssessmentContextResult,
        'direct-assessment-context',
    ),
    (
        'Document',
        DirectAssessmentDocumentTask,
        DirectAssessmentDocumentResult,
        'direct-assessment-document',
    ),
    (
        'MultiModal',
        MultiModalAssessmentTask,
        MultiModalAssessmentResult,
        'multimodal-assessment',
    ),
    (
        'Pairwise',
        PairwiseAssessmentTask,
        PairwiseAssessmentResult,
        'pairwise-assessment',
    ),
    (
        'Data',
        DataAssessmentTask,
        DataAssessmentResult,
        'data-assessment',
    ),
)

# Map convenient task type names into their corresponding task classes
CAMPAIGN_TASK_TYPES = {tup[0]:tup[1] for tup in TASK_DEFINITIONS}

# List of task result types
RESULT_TYPES = tuple([tup[2] for tup in TASK_DEFINITIONS])
