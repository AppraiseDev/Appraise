"""
Campaign admin.py
"""

# pylint: disable=C0330,import-error
from django.contrib import admin
from django.contrib.admin.filters import AllValuesFieldListFilter

from Campaign.models import Campaign
from Campaign.models import CampaignData
from Campaign.models import CampaignTeam
from Campaign.models import TrustedUser
from EvalData.admin import BaseMetadataAdmin
from django.http import HttpResponse
import csv
import zipfile
from io import StringIO
import importlib

class DropdownFilter(AllValuesFieldListFilter):
    """
    Experimental dropdown filter.
    """

    template = "Campaign/filter_select.html"


class CampaignTeamAdmin(BaseMetadataAdmin):
    """
    Model admin for CampaignTeam instances.
    """

    list_display = [
        "teamName",
        "owner",
        "teamMembers",
        "requiredAnnotations",
        "requiredHours",
        "completionStatus",
    ] + BaseMetadataAdmin.list_display  # type: ignore
    list_filter = ["owner"] + BaseMetadataAdmin.list_filter  # type: ignore
    search_fields = [
        "teamName",
        "owner__username",
        "owner__first_name",
        "owner__last_name",
    ] + BaseMetadataAdmin.search_fields  # type: ignore

    filter_horizontal = ["members"]

    fieldsets = (
        (
            None,
            {
                "fields": (
                    "teamName",
                    "owner",
                    "members",
                    "requiredAnnotations",
                    "requiredHours",
                )
            },
        ),
    ) + BaseMetadataAdmin.fieldsets  # type: ignore


class CampaignDataAdmin(BaseMetadataAdmin):
    """
    Model admin for CampaignData instances.
    """

    list_display = [
        "dataName",
        "market",
        "metadata",
        "dataValid",
        "dataReady",
    ] + BaseMetadataAdmin.list_display  # type: ignore
    list_filter = [
        "dataValid",
        "dataReady",
    ] + BaseMetadataAdmin.list_filter  # type: ignore
    search_fields = [
        # nothing model specific
    ] + BaseMetadataAdmin.search_fields  # type: ignore

    fieldsets = (
        (None, {"fields": ("dataFile", "market", "metadata")}),
    ) + BaseMetadataAdmin.fieldsets  # type: ignore


class CampaignAdmin(BaseMetadataAdmin):
    """
    Model admin for Campaign instances.
    """

    list_display = ["campaignName"] + \
        BaseMetadataAdmin.list_display + ["id"]  # type: ignore
    list_filter = [
        # nothing model specific
    ] + BaseMetadataAdmin.list_filter  # type: ignore
    search_fields = [
        # nothing model specific
    ] + BaseMetadataAdmin.search_fields  # type: ignore

    filter_horizontal = ["batches"]

    fieldsets = (
        (
            None,
            {
                "fields": (
                    "campaignName",
                    "packageFile",
                    "teams",
                    "batches",
                    "campaignOptions",
                )
            },
        ),
    ) + BaseMetadataAdmin.fieldsets  # type: ignore


    actions = ["export_results"]

    def _retrieve_csv(self, current_campaign):
        # Get the task type  corresponding to the campaign
        qs_name = current_campaign.get_campaign_type().lower()
        qs_attr = "evaldata_{0}_campaign".format(qs_name)
        qs_obj = getattr(current_campaign, qs_attr, None)
        cls = type(qs_obj.all()[0])
        cls_name = cls.__name__
        cls_name = cls_name.replace("Task", "Result")
        module = importlib.import_module(cls.__module__)
        cls = getattr(module, cls_name)

        # Now get the content
        f = StringIO()
        writer = csv.writer(f)
        csv_content = cls.get_system_data(current_campaign.id, extended_csv=True)
        for r in csv_content:
            writer.writerow(r)

        f.seek(0)
        return f


    def export_results(self, request, queryset):
        if len(queryset) == 1:
            current_campaign = queryset[0]
            csv_content = self._retrieve_csv(current_campaign)
            filename = f"results_{current_campaign.campaignName}.csv"
            response = HttpResponse(csv_content, content_type="text/csv")
            response["Content-Disposition"] = f"attachment; filename={filename}"
        else:
            response = HttpResponse(content_type='application/zip')
            response['Content-Disposition'] = 'attachment; filename="campaign_results.zip"'

            # Create a zip file with selected objects
            with zipfile.ZipFile(response, 'w') as zipf:
                for current_campaign in queryset:

                    csv_content = self._retrieve_csv(current_campaign)
                    # Add objects to the zip file, customize as per your model's data
                    # For example, you can add an object's name and description to a text file in the zip
                    filename = f"results_{current_campaign.campaignName}.csv"
                    zipf.writestr(filename, csv_content.getvalue())
        return response

    export_results.short_description = "Download results"



class TrustedUserAdmin(admin.ModelAdmin):
    """
    Model admin for Campaign instances.
    """

    list_display = ["user", "campaign"]
    list_filter = [
        ("campaign__campaignName", DropdownFilter),
        #      "campaign"
    ]
    search_fields = [  # type: ignore
        # nothing model specific
    ]

    fieldsets = ((None, {"fields": ("user", "campaign")}),)


admin.site.register(CampaignTeam, CampaignTeamAdmin)
admin.site.register(CampaignData, CampaignDataAdmin)
admin.site.register(Campaign, CampaignAdmin)
admin.site.register(TrustedUser, TrustedUserAdmin)
