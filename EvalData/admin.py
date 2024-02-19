"""
Appraise evaluation framework

See LICENSE for usage details
"""
# pylint: disable=C0330
from datetime import datetime

from django.contrib import admin
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.timezone import utc

from .models import *


# TODO:chrife: find a way to use SELECT-based filtering widgets
class BaseMetadataAdmin(admin.ModelAdmin):
    """
    Model admin for abstract base metadata object model.
    """

    list_display = ['modifiedBy', 'dateModified']
    list_filter = ['activated', 'completed', 'retired']
    search_fields = [
        'createdBy__username',
        'activatedBy__username',
        'completedBy__username',
        'retiredBy__username',
        'modifiedBy__username',
        '_str_name',
    ]

    # pylint: disable=C0111,R0903
    class Meta:
        abstract = True

    fieldsets = (
        (
            'Advanced options',
            {
                'classes': ('collapse',),
                'fields': ('activated', 'completed', 'retired'),
            },
        ),
    )

    def save_model(self, request, obj, form, change):
        """
        Given a model instance save it to the database.
        """
        utc_now = datetime.utcnow().replace(tzinfo=utc)

        if not hasattr(obj, 'createdBy') or obj.createdBy is None:
            obj.createdBy = request.user
            obj.dateCreated = utc_now
            obj.save()

        if obj.activated:
            if not hasattr(obj, 'activatedBy') or obj.activatedBy is None:
                obj.activatedBy = request.user
                obj.dateActivated = utc_now
                obj.save()

        if obj.completed:
            if not hasattr(obj, 'completedBy') or obj.completedBy is None:
                obj.completedBy = request.user
                obj.dateCompleted = utc_now
                obj.save()

        if obj.retired:
            if not hasattr(obj, 'retiredBy') or obj.retiredBy is None:
                obj.retiredBy = request.user
                obj.dateRetired = utc_now
                obj.save()

        obj.modifiedBy = request.user
        obj.dateModified = utc_now
        obj.save()

        super(BaseMetadataAdmin, self).save_model(request, obj, form, change)


class MarketAdmin(BaseMetadataAdmin):
    """
    Model admin for Market instances.
    """

    list_display = [
        '__str__',
        'sourceLanguageCode',
        'targetLanguageCode',
        'domainName',
    ] + BaseMetadataAdmin.list_display  # type: ignore
    list_filter = [
        'sourceLanguageCode',
        'targetLanguageCode',
        'domainName',
    ] + BaseMetadataAdmin.list_filter  # type: ignore
    search_fields = ['marketID'] + BaseMetadataAdmin.search_fields  # type: ignore

    fieldsets = (  # type: ignore
        (
            None,
            {
                'fields': (
                    [
                        'sourceLanguageCode',
                        'targetLanguageCode',
                        'domainName',
                    ]
                )
            },
        ),
    ) + BaseMetadataAdmin.fieldsets  # type: ignore


class MetadataAdmin(BaseMetadataAdmin):
    """
    Model admin for Metadata instances.
    """

    list_display = [
        'market',
        'corpusName',
        'versionInfo',
        'source',
    ] + BaseMetadataAdmin.list_display  # type: ignore
    list_filter = [
        'market__marketID',
        'corpusName',
        'versionInfo',
    ] + BaseMetadataAdmin.list_filter  # type: ignore
    search_fields = [
        'market__marketID',
        'corpusName',
        'versionInfo',
        'source',
    ] + BaseMetadataAdmin.search_fields  # type: ignore

    fieldsets = (
        (
            None,
            {'fields': (['market', 'corpusName', 'versionInfo', 'source'])},
        ),
    ) + BaseMetadataAdmin.fieldsets  # type: ignore


class TextSegmentAdmin(BaseMetadataAdmin):
    """
    Model admin for TextSegment instances.
    """

    list_display = [
        'metadata',
        'itemID',
        'itemType',
        'segmentID',
        'segmentText',
    ] + BaseMetadataAdmin.list_display  # type: ignore
    list_filter = [
        'metadata__corpusName',
        'metadata__versionInfo',
        'metadata__market__sourceLanguageCode',
        'metadata__market__targetLanguageCode',
        'metadata__market__domainName',
        'itemType',
    ] + BaseMetadataAdmin.list_filter  # type: ignore
    search_fields = [
        'segmentID',
        'segmentText',
    ] + BaseMetadataAdmin.search_fields  # type: ignore

    fieldsets = (
        (
            None,
            {
                'fields': (
                    [
                        'metadata',
                        'itemID',
                        'itemType',
                        'segmentID',
                        'segmentText',
                    ]
                )
            },
        ),
    ) + BaseMetadataAdmin.fieldsets  # type: ignore


class TextSegmentWithTwoTargetsAdmin(BaseMetadataAdmin):
    """
    Model admin for TextPair instances.
    """

    list_display = [
        '__str__',
        'itemID',
        'itemType',
        'segmentID',
        'segmentText',
        'target1ID',
        'target1Text',
        'target2ID',
        'target2Text',
    ] + BaseMetadataAdmin.list_display  # type: ignore
    list_filter = [
        'metadata__corpusName',
        'metadata__versionInfo',
        'metadata__market__sourceLanguageCode',
        'metadata__market__targetLanguageCode',
        'metadata__market__domainName',
        'itemType',
    ] + BaseMetadataAdmin.list_filter  # type: ignore
    search_fields = [
        'segmentID',
        'segmentText',
        'target1ID',
        'target1Text',
        'target2ID',
        'target2Text',
    ] + BaseMetadataAdmin.search_fields  # type: ignore

    fieldsets = (
        (
            None,
            {
                'fields': (
                    [
                        'metadata',
                        'itemID',
                        'itemType',
                        'segmentID',
                        'segmentText',
                        'target1ID',
                        'target1Text',
                        'target2ID',
                        'target2Text',
                    ]
                )
            },
        ),
    ) + BaseMetadataAdmin.fieldsets  # type: ignore


class TextPairAdmin(BaseMetadataAdmin):
    """
    Model admin for TextPair instances.
    """

    list_display = [
        '__str__',
        'itemID',
        'itemType',
        'sourceID',
        'sourceText',
        'targetID',
        'targetText',
    ] + BaseMetadataAdmin.list_display  # type: ignore
    list_filter = [
        'metadata__corpusName',
        'metadata__versionInfo',
        'metadata__market__sourceLanguageCode',
        'metadata__market__targetLanguageCode',
        'metadata__market__domainName',
        'itemType',
    ] + BaseMetadataAdmin.list_filter  # type: ignore
    search_fields = [
        'sourceID',
        'sourceText',
        'targetID',
        'targetText',
    ] + BaseMetadataAdmin.search_fields  # type: ignore

    fieldsets = (
        (
            None,
            {
                'fields': (
                    [
                        'metadata',
                        'itemID',
                        'itemType',
                        'sourceID',
                        'sourceText',
                        'targetID',
                        'targetText',
                    ]
                )
            },
        ),
    ) + BaseMetadataAdmin.fieldsets  # type: ignore


class TextPairWithContextAdmin(BaseMetadataAdmin):
    """
    Model admin for TextPairWithContext instances.
    """

    list_display = [
        '__str__',
        'itemID',
        'itemType',
        'documentID',
        'isCompleteDocument',
        'sourceID',
        'sourceText',
        'sourceContextLeft',
        'sourceContextRight',
        'targetID',
        'targetText',
        'targetContextLeft',
        'targetContextRight',
    ] + BaseMetadataAdmin.list_display  # type: ignore
    list_filter = [
        'metadata__corpusName',
        'metadata__versionInfo',
        'metadata__market__sourceLanguageCode',
        'metadata__market__targetLanguageCode',
        'metadata__market__domainName',
        'itemType',
        'isCompleteDocument',
    ] + BaseMetadataAdmin.list_filter  # type: ignore
    search_fields = [
        'documentID',
        'sourceID',
        'targetID',
        'sourceText',
        'sourceContextLeft',
        'sourceContextRight',
        'targetText',
        'targetContextLeft',
        'targetContextRight',
    ] + BaseMetadataAdmin.search_fields  # type: ignore

    fieldsets = (
        (
            None,
            {
                'fields': (
                    [
                        'metadata',
                        'itemID',
                        'itemType',
                        'documentID',
                        'isCompleteDocument',
                        'sourceID',
                        'sourceText',
                        'sourceContextLeft',
                        'sourceContextRight',
                        'targetID',
                        'targetText',
                        'targetContextLeft',
                        'targetContextRight',
                    ]
                )
            },
        ),
    ) + BaseMetadataAdmin.fieldsets  # type: ignore


class TextPairWithImageAdmin(BaseMetadataAdmin):
    """
    Model admin for TextPairWithImage instances.
    """

    list_display = [
        '__str__',
        'itemID',
        'itemType',
        'sourceID',
        'sourceText',
        'targetID',
        'targetText',
        'imageURL',
    ] + BaseMetadataAdmin.list_display  # type: ignore
    list_filter = [
        'metadata__corpusName',
        'metadata__versionInfo',
        'metadata__market__sourceLanguageCode',
        'metadata__market__targetLanguageCode',
        'metadata__market__domainName',
        'itemType',
    ] + BaseMetadataAdmin.list_filter  # type: ignore
    search_fields = [
        'sourceID',
        'sourceText',
        'targetID',
        'targetText',
    ] + BaseMetadataAdmin.search_fields  # type: ignore

    fieldsets = (
        (
            None,
            {
                'fields': (
                    [
                        'metadata',
                        'itemID',
                        'itemType',
                        'sourceID',
                        'sourceText',
                        'targetID',
                        'targetText',
                        'imageURL',
                    ]
                )
            },
        ),
    ) + BaseMetadataAdmin.fieldsets  # type: ignore


class DirectAssessmentTaskAdmin(BaseMetadataAdmin):
    """
    Model admin for DirectAssessmentTask instances.
    """

    list_display = [
        'dataName',
        'batchNo',
        'campaign',
        'requiredAnnotations',
    ] + BaseMetadataAdmin.list_display  # type: ignore
    list_filter = [
        'campaign__campaignName',
        'campaign__batches__market__targetLanguageCode',
        'campaign__batches__market__sourceLanguageCode',
        'batchData',
    ] + BaseMetadataAdmin.list_filter  # type: ignore
    search_fields = [
        'campaign__campaignName',
        'assignedTo',
    ] + BaseMetadataAdmin.search_fields  # type: ignore

    fieldsets = (
        (
            None,
            {
                'fields': (
                    [
                        'batchData',
                        'batchNo',
                        'campaign',
                        'items',
                        'requiredAnnotations',
                        'assignedTo',
                    ]
                )
            },
        ),
    ) + BaseMetadataAdmin.fieldsets  # type: ignore


class DirectAssessmentResultAdmin(BaseMetadataAdmin):
    """
    Model admin for DirectAssessmentResult instances.
    """

    list_display = [
        '__str__',
        'score',
        'start_time',
        'end_time',
        'duration',
        'item_type',
    ] + BaseMetadataAdmin.list_display  # type: ignore
    list_filter = [
        'item__itemType',
        'task__completed',
    ] + BaseMetadataAdmin.list_filter  # type: ignore
    search_fields = [
        # nothing model specific
    ] + BaseMetadataAdmin.search_fields  # type: ignore

    readonly_fields = ('item', 'task')

    fieldsets = (
        (None, {'fields': (['score', 'start_time', 'end_time'])}),
        ('Related', {'fields': (['item', 'task'])}),
    ) + BaseMetadataAdmin.fieldsets  # type: ignore


class DirectAssessmentContextTaskAdmin(BaseMetadataAdmin):
    """
    Model admin for DirectAssessmentContextTask instances.
    """

    list_display = [
        'dataName',
        'batchNo',
        'campaign',
        'requiredAnnotations',
    ] + BaseMetadataAdmin.list_display  # type: ignore
    list_filter = [
        'campaign__campaignName',
        'campaign__batches__market__targetLanguageCode',
        'campaign__batches__market__sourceLanguageCode',
        'batchData',
    ] + BaseMetadataAdmin.list_filter  # type: ignore
    search_fields = [
        'campaign__campaignName',
        'assignedTo',
    ] + BaseMetadataAdmin.search_fields  # type: ignore

    fieldsets = (
        (
            None,
            {
                'fields': (
                    [
                        'batchData',
                        'batchNo',
                        'campaign',
                        'items',
                        'requiredAnnotations',
                        'assignedTo',
                    ]
                )
            },
        ),
    ) + BaseMetadataAdmin.fieldsets  # type: ignore


class DirectAssessmentContextResultAdmin(BaseMetadataAdmin):
    """
    Model admin for DirectAssessmentContextResult instances.
    """

    list_display = [
        '__str__',
        'score',
        'start_time',
        'end_time',
        'duration',
        'item_type',
    ] + BaseMetadataAdmin.list_display  # type: ignore
    list_filter = [
        'item__itemType',
        'task__completed',
        'item__isCompleteDocument',
    ] + BaseMetadataAdmin.list_filter  # type: ignore
    search_fields = [
        # nothing model specific
    ] + BaseMetadataAdmin.search_fields  # type: ignore

    readonly_fields = ('item', 'task')

    fieldsets = (
        (None, {'fields': (['score', 'start_time', 'end_time'])}),
        ('Related', {'fields': (['item', 'task'])}),
    ) + BaseMetadataAdmin.fieldsets  # type: ignore


class DirectAssessmentDocumentTaskAdmin(DirectAssessmentContextTaskAdmin):
    """
    Model admin for DirectAssessmentDocumentTask instances.
    """

    pass


class DirectAssessmentDocumentResultAdmin(DirectAssessmentContextResultAdmin):
    """
    Model admin for DirectAssessmentDocumentResult instances.
    """

    pass


class MultiModalAssessmentTaskAdmin(BaseMetadataAdmin):
    """
    Model admin for MultiModalAssessmentTask instances.
    """

    list_display = [
        'dataName',
        'batchNo',
        'campaign',
        'requiredAnnotations',
    ] + BaseMetadataAdmin.list_display  # type: ignore
    list_filter = [
        'campaign__campaignName',
        'campaign__batches__market__targetLanguageCode',
        'campaign__batches__market__sourceLanguageCode',
        'batchData',
    ] + BaseMetadataAdmin.list_filter  # type: ignore
    search_fields = [
        'campaign__campaignName',
        'assignedTo',
    ] + BaseMetadataAdmin.search_fields  # type: ignore

    fieldsets = (
        (
            None,
            {
                'fields': (
                    [
                        'batchData',
                        'batchNo',
                        'campaign',
                        'items',
                        'requiredAnnotations',
                        'assignedTo',
                    ]
                )
            },
        ),
    ) + BaseMetadataAdmin.fieldsets  # type: ignore


class MultiModalAssessmentResultAdmin(BaseMetadataAdmin):
    """
    Model admin for MultiModalAssessmentResult instances.
    """

    list_display = [
        '__str__',
        'score',
        'start_time',
        'end_time',
        'duration',
        'item_type',
    ] + BaseMetadataAdmin.list_display  # type: ignore
    list_filter = [
        'item__itemType',
        'task__completed',
    ] + BaseMetadataAdmin.list_filter  # type: ignore
    search_fields = [
        # nothing model specific
    ] + BaseMetadataAdmin.search_fields  # type: ignore

    fieldsets = (
        (
            None,
            {'fields': (['score', 'start_time', 'end_time', 'item', 'task'])},
        ),
    ) + BaseMetadataAdmin.fieldsets  # type: ignore


class WorkAgendaAdmin(admin.ModelAdmin):
    """
    Model admin for WorkAgenda object model.
    """

    list_display = ['user', 'campaign', 'completed']
    list_filter = ['campaign']
    search_fields = [
        'user__username',
        'campaign__campaignName',
    ]


class TaskAgendaAdmin(admin.ModelAdmin):
    """
    Model admin for TaskAgenda object model.
    """

    actions = ['reset_taskagenda']

    list_display = ['user', 'campaign', 'completed']
    list_filter = ['campaign']
    search_fields = [
        'user__username',
        'campaign__campaignName',
    ]

    def get_actions(self, request):
        """
        Reset task agenda action requires reset_taskagenda permission.
        """
        actions = super(TaskAgendaAdmin, self).get_actions(request)
        if 'reset_taskagenda' in actions:
            if not request.user.has_perm('EvalData.reset_taskagenda'):
                del actions['reset_taskagenda']
        return actions

    def reset_taskagenda(self, request, queryset):
        """
        Handles reset task agenda admin action for TaskAgenda instances.
        """
        agendas_selected = queryset.count()
        if agendas_selected > 1:
            _msg = (
                "You can only reset one task agenda at a time. "
                "No items have been changed."
            )
            self.message_user(request, _msg, level=messages.WARNING)
            return HttpResponseRedirect(reverse('admin:EvalData_taskagenda_changelist'))

        _pk = request.POST.getlist(admin.helpers.ACTION_CHECKBOX_NAME)
        return HttpResponseRedirect(reverse('reset-taskagenda', args=_pk))

    reset_taskagenda.short_description = "Reset task agenda"  # type: ignore


class PairwiseAssessmentTaskAdmin(BaseMetadataAdmin):
    """
    Model admin for PairwiseAssessmentTask instances.
    """

    list_display = [
        'dataName',
        'batchNo',
        'campaign',
        'requiredAnnotations',
    ] + BaseMetadataAdmin.list_display  # type: ignore
    list_filter = [
        'campaign__campaignName',
        'campaign__batches__market__targetLanguageCode',
        'campaign__batches__market__sourceLanguageCode',
        'batchData',
    ] + BaseMetadataAdmin.list_filter  # type: ignore
    search_fields = [
        'campaign__campaignName',
        'assignedTo',
    ] + BaseMetadataAdmin.search_fields  # type: ignore

    fieldsets = (
        (
            None,
            {
                'fields': (
                    [
                        'batchData',
                        'batchNo',
                        'campaign',
                        'items',
                        'requiredAnnotations',
                        'assignedTo',
                    ]
                )
            },
        ),
    ) + BaseMetadataAdmin.fieldsets  # type: ignore


class PairwiseAssessmentResultAdmin(BaseMetadataAdmin):
    """
    Model admin for PairwiseAssessmentResult instances.
    """

    list_display = [
        '__str__',
        'score1',
        'score2',
        'start_time',
        'end_time',
        'duration',
        'item_type',
    ] + BaseMetadataAdmin.list_display  # type: ignore
    list_filter = [
        'item__itemType',
        'task__completed',
    ] + BaseMetadataAdmin.list_filter  # type: ignore
    search_fields = [
        # nothing model specific
    ] + BaseMetadataAdmin.search_fields  # type: ignore

    readonly_fields = ('item', 'task')

    fieldsets = (
        (
            None,
            {'fields': (['score1', 'score2', 'start_time', 'end_time'])},
        ),
        ('Related', {'fields': (['item', 'task'])}),
    ) + BaseMetadataAdmin.fieldsets  # type: ignore


class PairwiseAssessmentDocumentTaskAdmin(BaseMetadataAdmin):
    """
    Model admin for PairwiseAssessmentDocumentTask instances.
    """

    list_display = [
        'dataName',
        'batchNo',
        'campaign',
        'requiredAnnotations',
    ] + BaseMetadataAdmin.list_display  # type: ignore
    list_filter = [
        'campaign__campaignName',
        'campaign__batches__market__targetLanguageCode',
        'campaign__batches__market__sourceLanguageCode',
        'batchData',
    ] + BaseMetadataAdmin.list_filter  # type: ignore
    search_fields = [
        'campaign__campaignName',
        'assignedTo',
    ] + BaseMetadataAdmin.search_fields  # type: ignore

    fieldsets = (
        (
            None,
            {
                'fields': (
                    [
                        'batchData',
                        'batchNo',
                        'campaign',
                        'items',
                        'requiredAnnotations',
                        'assignedTo',
                    ]
                )
            },
        ),
    ) + BaseMetadataAdmin.fieldsets  # type: ignore


class PairwiseAssessmentDocumentResultAdmin(BaseMetadataAdmin):
    """
    Model admin for PairwiseAssessmentDocumentResult instances.
    """

    list_display = [
        '__str__',
        'score1',
        'score2',
        'start_time',
        'end_time',
        'duration',
        'item_type',
    ] + BaseMetadataAdmin.list_display  # type: ignore
    list_filter = [
        'item__itemType',
        'task__completed',
        'item__isCompleteDocument',
    ] + BaseMetadataAdmin.list_filter  # type: ignore
    search_fields = [
        # nothing model specific
    ] + BaseMetadataAdmin.search_fields  # type: ignore

    readonly_fields = ('item', 'task')

    fieldsets = (
        (
            None,
            {'fields': (['score1', 'score2', 'start_time', 'end_time'])},
        ),
        ('Related', {'fields': (['item', 'task'])}),
    ) + BaseMetadataAdmin.fieldsets  # type: ignore


class DataAssessmentTaskAdmin(BaseMetadataAdmin):
    """
    Model admin for DataAssessmentTask instances.
    """

    list_display = [
        'dataName',
        'batchNo',
        'campaign',
        'requiredAnnotations',
    ] + BaseMetadataAdmin.list_display  # type: ignore
    list_filter = [
        'campaign__campaignName',
        'campaign__batches__market__targetLanguageCode',
        'campaign__batches__market__sourceLanguageCode',
        'batchData',
    ] + BaseMetadataAdmin.list_filter  # type: ignore
    search_fields = [
        'campaign__campaignName',
        'assignedTo',
    ] + BaseMetadataAdmin.search_fields  # type: ignore

    fieldsets = (
        (
            None,
            {
                'fields': (
                    [
                        'batchData',
                        'batchNo',
                        'campaign',
                        'items',
                        'requiredAnnotations',
                        'assignedTo',
                    ]
                )
            },
        ),
    ) + BaseMetadataAdmin.fieldsets  # type: ignore


class DataAssessmentResultAdmin(BaseMetadataAdmin):
    """
    Model admin for DataAssessmentResult instances.
    """

    list_display = [
        '__str__',
        'score',
        'start_time',
        'end_time',
        'duration',
        'item_type',
    ] + BaseMetadataAdmin.list_display  # type: ignore
    list_filter = [
        'item__itemType',
        'task__completed',
    ] + BaseMetadataAdmin.list_filter  # type: ignore
    search_fields = [
        # nothing model specific
    ] + BaseMetadataAdmin.search_fields  # type: ignore

    readonly_fields = ('item', 'task')

    fieldsets = (
        (None, {'fields': (['score', 'start_time', 'end_time'])}),
        ('Related', {'fields': (['item', 'task'])}),
    ) + BaseMetadataAdmin.fieldsets  # type: ignore


admin.site.register(Market, MarketAdmin)
admin.site.register(Metadata, MetadataAdmin)
admin.site.register(TextSegment, TextSegmentAdmin)
admin.site.register(TextPair, TextPairAdmin)
admin.site.register(TextPairWithContext, TextPairWithContextAdmin)
admin.site.register(TextPairWithImage, TextPairWithImageAdmin)
admin.site.register(TextSegmentWithTwoTargets, TextSegmentWithTwoTargetsAdmin)
admin.site.register(DataAssessmentTask, DataAssessmentTaskAdmin)
admin.site.register(DataAssessmentResult, DataAssessmentResultAdmin)
admin.site.register(DirectAssessmentTask, DirectAssessmentTaskAdmin)
admin.site.register(DirectAssessmentResult, DirectAssessmentResultAdmin)
admin.site.register(DirectAssessmentContextTask, DirectAssessmentContextTaskAdmin)
admin.site.register(DirectAssessmentContextResult, DirectAssessmentContextResultAdmin)
admin.site.register(DirectAssessmentDocumentTask, DirectAssessmentDocumentTaskAdmin)
admin.site.register(DirectAssessmentDocumentResult, DirectAssessmentDocumentResultAdmin)
admin.site.register(MultiModalAssessmentTask, MultiModalAssessmentTaskAdmin)
admin.site.register(MultiModalAssessmentResult, MultiModalAssessmentResultAdmin)
admin.site.register(PairwiseAssessmentTask, PairwiseAssessmentTaskAdmin)
admin.site.register(PairwiseAssessmentResult, PairwiseAssessmentResultAdmin)
admin.site.register(PairwiseAssessmentDocumentTask, PairwiseAssessmentDocumentTaskAdmin)
admin.site.register(
    PairwiseAssessmentDocumentResult, PairwiseAssessmentDocumentResultAdmin
)
admin.site.register(WorkAgenda, WorkAgendaAdmin)
admin.site.register(TaskAgenda, TaskAgendaAdmin)
