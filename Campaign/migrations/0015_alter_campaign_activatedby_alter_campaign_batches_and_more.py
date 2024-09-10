# Generated by Django 4.2.10 on 2024-02-19 16:58

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("Campaign", "0014_campaign_campaignoptions"),
    ]

    operations = [
        migrations.AlterField(
            model_name="campaign",
            name="activatedBy",
            field=models.ForeignKey(
                blank=True,
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="%(app_label)s_%(class)s_activated_by",
                related_query_name="%(app_label)s_%(class)ss",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Activated by",
            ),
        ),
        migrations.AlterField(
            model_name="campaign",
            name="batches",
            field=models.ManyToManyField(
                blank=True,
                related_name="%(app_label)s_%(class)s_batches",
                related_query_name="%(app_label)s_%(class)ss",
                to="Campaign.campaigndata",
                verbose_name="Batches",
            ),
        ),
        migrations.AlterField(
            model_name="campaign",
            name="completedBy",
            field=models.ForeignKey(
                blank=True,
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="%(app_label)s_%(class)s_completed_by",
                related_query_name="%(app_label)s_%(class)ss",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Completed by",
            ),
        ),
        migrations.AlterField(
            model_name="campaign",
            name="createdBy",
            field=models.ForeignKey(
                editable=False,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="%(app_label)s_%(class)s_created_by",
                related_query_name="%(app_label)s_%(class)ss",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Created by",
            ),
        ),
        migrations.AlterField(
            model_name="campaign",
            name="modifiedBy",
            field=models.ForeignKey(
                blank=True,
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="%(app_label)s_%(class)s_modified_by",
                related_query_name="%(app_label)s_%(class)ss",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Modified by",
            ),
        ),
        migrations.AlterField(
            model_name="campaign",
            name="retiredBy",
            field=models.ForeignKey(
                blank=True,
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="%(app_label)s_%(class)s_retired_by",
                related_query_name="%(app_label)s_%(class)ss",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Retired by",
            ),
        ),
        migrations.AlterField(
            model_name="campaign",
            name="teams",
            field=models.ManyToManyField(
                blank=True,
                related_name="%(app_label)s_%(class)s_teams",
                related_query_name="%(app_label)s_%(class)ss",
                to="Campaign.campaignteam",
                verbose_name="Teams",
            ),
        ),
        migrations.AlterField(
            model_name="campaigndata",
            name="activatedBy",
            field=models.ForeignKey(
                blank=True,
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="%(app_label)s_%(class)s_activated_by",
                related_query_name="%(app_label)s_%(class)ss",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Activated by",
            ),
        ),
        migrations.AlterField(
            model_name="campaigndata",
            name="completedBy",
            field=models.ForeignKey(
                blank=True,
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="%(app_label)s_%(class)s_completed_by",
                related_query_name="%(app_label)s_%(class)ss",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Completed by",
            ),
        ),
        migrations.AlterField(
            model_name="campaigndata",
            name="createdBy",
            field=models.ForeignKey(
                editable=False,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="%(app_label)s_%(class)s_created_by",
                related_query_name="%(app_label)s_%(class)ss",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Created by",
            ),
        ),
        migrations.AlterField(
            model_name="campaigndata",
            name="modifiedBy",
            field=models.ForeignKey(
                blank=True,
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="%(app_label)s_%(class)s_modified_by",
                related_query_name="%(app_label)s_%(class)ss",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Modified by",
            ),
        ),
        migrations.AlterField(
            model_name="campaigndata",
            name="retiredBy",
            field=models.ForeignKey(
                blank=True,
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="%(app_label)s_%(class)s_retired_by",
                related_query_name="%(app_label)s_%(class)ss",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Retired by",
            ),
        ),
        migrations.AlterField(
            model_name="campaignteam",
            name="activatedBy",
            field=models.ForeignKey(
                blank=True,
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="%(app_label)s_%(class)s_activated_by",
                related_query_name="%(app_label)s_%(class)ss",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Activated by",
            ),
        ),
        migrations.AlterField(
            model_name="campaignteam",
            name="completedBy",
            field=models.ForeignKey(
                blank=True,
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="%(app_label)s_%(class)s_completed_by",
                related_query_name="%(app_label)s_%(class)ss",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Completed by",
            ),
        ),
        migrations.AlterField(
            model_name="campaignteam",
            name="createdBy",
            field=models.ForeignKey(
                editable=False,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="%(app_label)s_%(class)s_created_by",
                related_query_name="%(app_label)s_%(class)ss",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Created by",
            ),
        ),
        migrations.AlterField(
            model_name="campaignteam",
            name="members",
            field=models.ManyToManyField(
                related_name="%(app_label)s_%(class)s_members",
                related_query_name="%(app_label)s_%(class)ss",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Team members",
            ),
        ),
        migrations.AlterField(
            model_name="campaignteam",
            name="modifiedBy",
            field=models.ForeignKey(
                blank=True,
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="%(app_label)s_%(class)s_modified_by",
                related_query_name="%(app_label)s_%(class)ss",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Modified by",
            ),
        ),
        migrations.AlterField(
            model_name="campaignteam",
            name="owner",
            field=models.ForeignKey(
                help_text="(must be staff member)",
                limit_choices_to={"is_staff": True},
                on_delete=django.db.models.deletion.PROTECT,
                related_name="%(app_label)s_%(class)s_owner",
                related_query_name="%(app_label)s_%(class)ss",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Team owner",
            ),
        ),
        migrations.AlterField(
            model_name="campaignteam",
            name="retiredBy",
            field=models.ForeignKey(
                blank=True,
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="%(app_label)s_%(class)s_retired_by",
                related_query_name="%(app_label)s_%(class)ss",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Retired by",
            ),
        ),
    ]
