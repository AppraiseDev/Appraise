"""
Campaign admin.py
"""
# pylint: disable=C0330
from django.contrib import admin

from EvalData.admin import BaseMetadataAdmin
from .models import CampaignTeam, CampaignData, Campaign


class CampaignTeamAdmin(BaseMetadataAdmin):
    """
    Model admin for CampaignTeam instances.
    """
    list_display = [
      'teamName', 'owner', 'campaignMembers', 'requiredAnnotations',
      'requiredHours', 'completionStatus'
    ] + BaseMetadataAdmin.list_display
    list_filter = [
      'owner'
    ] + BaseMetadataAdmin.list_filter
    search_fields = [
      'teamName', 'owner__username', 'owner__first_name', 'owner__last_name'
    ] + BaseMetadataAdmin.search_fields

    fieldsets = (
      (None, {
        'fields': ('teamName', 'owner', 'requiredAnnotations',
          'requiredHours')
      }),
    ) + BaseMetadataAdmin.fieldsets


class CampaignDataAdmin(BaseMetadataAdmin):
    """
    Model admin for CampaignData instances.
    """
    list_display = [
      'dataName', 'market', 'metadata', 'dataValid', 'dataReady'
    ] + BaseMetadataAdmin.list_display
    list_filter = [
      'dataValid', 'dataReady'
    ] + BaseMetadataAdmin.list_filter
    search_fields = [
      # nothing model specific
    ] + BaseMetadataAdmin.search_fields

    fieldsets = (
      (None, {
        'fields': ('dataFile', 'market', 'metadata')
      }),
    ) + BaseMetadataAdmin.fieldsets



class CampaignAdmin(BaseMetadataAdmin):
    """
    Model admin for Campaign instances.
    """
    list_display = [
      'campaignName'
    ] + BaseMetadataAdmin.list_display
    list_filter = [
      # nothing model specific
    ] + BaseMetadataAdmin.list_filter
    search_fields = [
      # nothing model specific
    ] + BaseMetadataAdmin.search_fields

    fieldsets = (
      (None, {
        'fields': ('campaignName', 'teams', 'batches')
      }),
    ) + BaseMetadataAdmin.fieldsets

admin.site.register(CampaignTeam, CampaignTeamAdmin)
admin.site.register(CampaignData, CampaignDataAdmin)
admin.site.register(Campaign, CampaignAdmin)
