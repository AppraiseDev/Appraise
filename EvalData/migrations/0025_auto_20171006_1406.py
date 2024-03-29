# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2017-10-06 21:06
from __future__ import unicode_literals

import django.db.models.deletion
from django.conf import settings
from django.db import migrations
from django.db import models


class Migration(migrations.Migration):

    dependencies = [
        ('EvalData', '0024_auto_20171006_1311'),
    ]

    operations = [
        migrations.AddField(
            model_name='metadata',
            name='_str_name',
            field=models.TextField(default='', editable=False),
        ),
        migrations.AlterField(
            model_name='directassessmentresult',
            name='activatedBy',
            field=models.ForeignKey(
                blank=True,
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='evaldata_directassessmentresult_activated_by',
                related_query_name='evaldata_directassessmentresults',
                to=settings.AUTH_USER_MODEL,
                verbose_name='Activated by',
            ),
        ),
        migrations.AlterField(
            model_name='directassessmentresult',
            name='completedBy',
            field=models.ForeignKey(
                blank=True,
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='evaldata_directassessmentresult_completed_by',
                related_query_name='evaldata_directassessmentresults',
                to=settings.AUTH_USER_MODEL,
                verbose_name='Completed by',
            ),
        ),
        migrations.AlterField(
            model_name='directassessmentresult',
            name='createdBy',
            field=models.ForeignKey(
                editable=False,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='evaldata_directassessmentresult_created_by',
                related_query_name='evaldata_directassessmentresults',
                to=settings.AUTH_USER_MODEL,
                verbose_name='Created by',
            ),
        ),
        migrations.AlterField(
            model_name='directassessmentresult',
            name='item',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='evaldata_directassessmentresult_items',
                related_query_name='evaldata_directassessmentresult_item',
                to='EvalData.TextPair',
                verbose_name='Item',
            ),
        ),
        migrations.AlterField(
            model_name='directassessmentresult',
            name='modifiedBy',
            field=models.ForeignKey(
                blank=True,
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='evaldata_directassessmentresult_modified_by',
                related_query_name='evaldata_directassessmentresults',
                to=settings.AUTH_USER_MODEL,
                verbose_name='Modified by',
            ),
        ),
        migrations.AlterField(
            model_name='directassessmentresult',
            name='retiredBy',
            field=models.ForeignKey(
                blank=True,
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='evaldata_directassessmentresult_retired_by',
                related_query_name='evaldata_directassessmentresults',
                to=settings.AUTH_USER_MODEL,
                verbose_name='Retired by',
            ),
        ),
        migrations.AlterField(
            model_name='directassessmentresult',
            name='task',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='evaldata_directassessmentresult_tasks',
                related_query_name='evaldata_directassessmentresult_task',
                to='EvalData.DirectAssessmentTask',
                verbose_name='Task',
            ),
        ),
        migrations.AlterField(
            model_name='directassessmenttask',
            name='activatedBy',
            field=models.ForeignKey(
                blank=True,
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='evaldata_directassessmenttask_activated_by',
                related_query_name='evaldata_directassessmenttasks',
                to=settings.AUTH_USER_MODEL,
                verbose_name='Activated by',
            ),
        ),
        migrations.AlterField(
            model_name='directassessmenttask',
            name='completedBy',
            field=models.ForeignKey(
                blank=True,
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='evaldata_directassessmenttask_completed_by',
                related_query_name='evaldata_directassessmenttasks',
                to=settings.AUTH_USER_MODEL,
                verbose_name='Completed by',
            ),
        ),
        migrations.AlterField(
            model_name='directassessmenttask',
            name='createdBy',
            field=models.ForeignKey(
                editable=False,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='evaldata_directassessmenttask_created_by',
                related_query_name='evaldata_directassessmenttasks',
                to=settings.AUTH_USER_MODEL,
                verbose_name='Created by',
            ),
        ),
        migrations.AlterField(
            model_name='directassessmenttask',
            name='modifiedBy',
            field=models.ForeignKey(
                blank=True,
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='evaldata_directassessmenttask_modified_by',
                related_query_name='evaldata_directassessmenttasks',
                to=settings.AUTH_USER_MODEL,
                verbose_name='Modified by',
            ),
        ),
        migrations.AlterField(
            model_name='directassessmenttask',
            name='retiredBy',
            field=models.ForeignKey(
                blank=True,
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='evaldata_directassessmenttask_retired_by',
                related_query_name='evaldata_directassessmenttasks',
                to=settings.AUTH_USER_MODEL,
                verbose_name='Retired by',
            ),
        ),
        migrations.AlterField(
            model_name='market',
            name='activatedBy',
            field=models.ForeignKey(
                blank=True,
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='evaldata_market_activated_by',
                related_query_name='evaldata_markets',
                to=settings.AUTH_USER_MODEL,
                verbose_name='Activated by',
            ),
        ),
        migrations.AlterField(
            model_name='market',
            name='completedBy',
            field=models.ForeignKey(
                blank=True,
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='evaldata_market_completed_by',
                related_query_name='evaldata_markets',
                to=settings.AUTH_USER_MODEL,
                verbose_name='Completed by',
            ),
        ),
        migrations.AlterField(
            model_name='market',
            name='createdBy',
            field=models.ForeignKey(
                editable=False,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='evaldata_market_created_by',
                related_query_name='evaldata_markets',
                to=settings.AUTH_USER_MODEL,
                verbose_name='Created by',
            ),
        ),
        migrations.AlterField(
            model_name='market',
            name='modifiedBy',
            field=models.ForeignKey(
                blank=True,
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='evaldata_market_modified_by',
                related_query_name='evaldata_markets',
                to=settings.AUTH_USER_MODEL,
                verbose_name='Modified by',
            ),
        ),
        migrations.AlterField(
            model_name='market',
            name='retiredBy',
            field=models.ForeignKey(
                blank=True,
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='evaldata_market_retired_by',
                related_query_name='evaldata_markets',
                to=settings.AUTH_USER_MODEL,
                verbose_name='Retired by',
            ),
        ),
        migrations.AlterField(
            model_name='metadata',
            name='activatedBy',
            field=models.ForeignKey(
                blank=True,
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='evaldata_metadata_activated_by',
                related_query_name='evaldata_metadatas',
                to=settings.AUTH_USER_MODEL,
                verbose_name='Activated by',
            ),
        ),
        migrations.AlterField(
            model_name='metadata',
            name='completedBy',
            field=models.ForeignKey(
                blank=True,
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='evaldata_metadata_completed_by',
                related_query_name='evaldata_metadatas',
                to=settings.AUTH_USER_MODEL,
                verbose_name='Completed by',
            ),
        ),
        migrations.AlterField(
            model_name='metadata',
            name='createdBy',
            field=models.ForeignKey(
                editable=False,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='evaldata_metadata_created_by',
                related_query_name='evaldata_metadatas',
                to=settings.AUTH_USER_MODEL,
                verbose_name='Created by',
            ),
        ),
        migrations.AlterField(
            model_name='metadata',
            name='modifiedBy',
            field=models.ForeignKey(
                blank=True,
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='evaldata_metadata_modified_by',
                related_query_name='evaldata_metadatas',
                to=settings.AUTH_USER_MODEL,
                verbose_name='Modified by',
            ),
        ),
        migrations.AlterField(
            model_name='metadata',
            name='retiredBy',
            field=models.ForeignKey(
                blank=True,
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='evaldata_metadata_retired_by',
                related_query_name='evaldata_metadatas',
                to=settings.AUTH_USER_MODEL,
                verbose_name='Retired by',
            ),
        ),
        migrations.AlterField(
            model_name='multimodalassessmentresult',
            name='activatedBy',
            field=models.ForeignKey(
                blank=True,
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='evaldata_multimodalassessmentresult_activated_by',
                related_query_name='evaldata_multimodalassessmentresults',
                to=settings.AUTH_USER_MODEL,
                verbose_name='Activated by',
            ),
        ),
        migrations.AlterField(
            model_name='multimodalassessmentresult',
            name='completedBy',
            field=models.ForeignKey(
                blank=True,
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='evaldata_multimodalassessmentresult_completed_by',
                related_query_name='evaldata_multimodalassessmentresults',
                to=settings.AUTH_USER_MODEL,
                verbose_name='Completed by',
            ),
        ),
        migrations.AlterField(
            model_name='multimodalassessmentresult',
            name='createdBy',
            field=models.ForeignKey(
                editable=False,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='evaldata_multimodalassessmentresult_created_by',
                related_query_name='evaldata_multimodalassessmentresults',
                to=settings.AUTH_USER_MODEL,
                verbose_name='Created by',
            ),
        ),
        migrations.AlterField(
            model_name='multimodalassessmentresult',
            name='modifiedBy',
            field=models.ForeignKey(
                blank=True,
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='evaldata_multimodalassessmentresult_modified_by',
                related_query_name='evaldata_multimodalassessmentresults',
                to=settings.AUTH_USER_MODEL,
                verbose_name='Modified by',
            ),
        ),
        migrations.AlterField(
            model_name='multimodalassessmentresult',
            name='retiredBy',
            field=models.ForeignKey(
                blank=True,
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='evaldata_multimodalassessmentresult_retired_by',
                related_query_name='evaldata_multimodalassessmentresults',
                to=settings.AUTH_USER_MODEL,
                verbose_name='Retired by',
            ),
        ),
        migrations.AlterField(
            model_name='multimodalassessmenttask',
            name='activatedBy',
            field=models.ForeignKey(
                blank=True,
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='evaldata_multimodalassessmenttask_activated_by',
                related_query_name='evaldata_multimodalassessmenttasks',
                to=settings.AUTH_USER_MODEL,
                verbose_name='Activated by',
            ),
        ),
        migrations.AlterField(
            model_name='multimodalassessmenttask',
            name='completedBy',
            field=models.ForeignKey(
                blank=True,
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='evaldata_multimodalassessmenttask_completed_by',
                related_query_name='evaldata_multimodalassessmenttasks',
                to=settings.AUTH_USER_MODEL,
                verbose_name='Completed by',
            ),
        ),
        migrations.AlterField(
            model_name='multimodalassessmenttask',
            name='createdBy',
            field=models.ForeignKey(
                editable=False,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='evaldata_multimodalassessmenttask_created_by',
                related_query_name='evaldata_multimodalassessmenttasks',
                to=settings.AUTH_USER_MODEL,
                verbose_name='Created by',
            ),
        ),
        migrations.AlterField(
            model_name='multimodalassessmenttask',
            name='modifiedBy',
            field=models.ForeignKey(
                blank=True,
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='evaldata_multimodalassessmenttask_modified_by',
                related_query_name='evaldata_multimodalassessmenttasks',
                to=settings.AUTH_USER_MODEL,
                verbose_name='Modified by',
            ),
        ),
        migrations.AlterField(
            model_name='multimodalassessmenttask',
            name='retiredBy',
            field=models.ForeignKey(
                blank=True,
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='evaldata_multimodalassessmenttask_retired_by',
                related_query_name='evaldata_multimodalassessmenttasks',
                to=settings.AUTH_USER_MODEL,
                verbose_name='Retired by',
            ),
        ),
        migrations.AlterField(
            model_name='textpair',
            name='activatedBy',
            field=models.ForeignKey(
                blank=True,
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='evaldata_textpair_activated_by',
                related_query_name='evaldata_textpairs',
                to=settings.AUTH_USER_MODEL,
                verbose_name='Activated by',
            ),
        ),
        migrations.AlterField(
            model_name='textpair',
            name='completedBy',
            field=models.ForeignKey(
                blank=True,
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='evaldata_textpair_completed_by',
                related_query_name='evaldata_textpairs',
                to=settings.AUTH_USER_MODEL,
                verbose_name='Completed by',
            ),
        ),
        migrations.AlterField(
            model_name='textpair',
            name='createdBy',
            field=models.ForeignKey(
                editable=False,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='evaldata_textpair_created_by',
                related_query_name='evaldata_textpairs',
                to=settings.AUTH_USER_MODEL,
                verbose_name='Created by',
            ),
        ),
        migrations.AlterField(
            model_name='textpair',
            name='modifiedBy',
            field=models.ForeignKey(
                blank=True,
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='evaldata_textpair_modified_by',
                related_query_name='evaldata_textpairs',
                to=settings.AUTH_USER_MODEL,
                verbose_name='Modified by',
            ),
        ),
        migrations.AlterField(
            model_name='textpair',
            name='retiredBy',
            field=models.ForeignKey(
                blank=True,
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='evaldata_textpair_retired_by',
                related_query_name='evaldata_textpairs',
                to=settings.AUTH_USER_MODEL,
                verbose_name='Retired by',
            ),
        ),
        migrations.AlterField(
            model_name='textpairwithimage',
            name='activatedBy',
            field=models.ForeignKey(
                blank=True,
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='evaldata_textpairwithimage_activated_by',
                related_query_name='evaldata_textpairwithimages',
                to=settings.AUTH_USER_MODEL,
                verbose_name='Activated by',
            ),
        ),
        migrations.AlterField(
            model_name='textpairwithimage',
            name='completedBy',
            field=models.ForeignKey(
                blank=True,
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='evaldata_textpairwithimage_completed_by',
                related_query_name='evaldata_textpairwithimages',
                to=settings.AUTH_USER_MODEL,
                verbose_name='Completed by',
            ),
        ),
        migrations.AlterField(
            model_name='textpairwithimage',
            name='createdBy',
            field=models.ForeignKey(
                editable=False,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='evaldata_textpairwithimage_created_by',
                related_query_name='evaldata_textpairwithimages',
                to=settings.AUTH_USER_MODEL,
                verbose_name='Created by',
            ),
        ),
        migrations.AlterField(
            model_name='textpairwithimage',
            name='modifiedBy',
            field=models.ForeignKey(
                blank=True,
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='evaldata_textpairwithimage_modified_by',
                related_query_name='evaldata_textpairwithimages',
                to=settings.AUTH_USER_MODEL,
                verbose_name='Modified by',
            ),
        ),
        migrations.AlterField(
            model_name='textpairwithimage',
            name='retiredBy',
            field=models.ForeignKey(
                blank=True,
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='evaldata_textpairwithimage_retired_by',
                related_query_name='evaldata_textpairwithimages',
                to=settings.AUTH_USER_MODEL,
                verbose_name='Retired by',
            ),
        ),
        migrations.AlterField(
            model_name='textsegment',
            name='activatedBy',
            field=models.ForeignKey(
                blank=True,
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='evaldata_textsegment_activated_by',
                related_query_name='evaldata_textsegments',
                to=settings.AUTH_USER_MODEL,
                verbose_name='Activated by',
            ),
        ),
        migrations.AlterField(
            model_name='textsegment',
            name='completedBy',
            field=models.ForeignKey(
                blank=True,
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='evaldata_textsegment_completed_by',
                related_query_name='evaldata_textsegments',
                to=settings.AUTH_USER_MODEL,
                verbose_name='Completed by',
            ),
        ),
        migrations.AlterField(
            model_name='textsegment',
            name='createdBy',
            field=models.ForeignKey(
                editable=False,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='evaldata_textsegment_created_by',
                related_query_name='evaldata_textsegments',
                to=settings.AUTH_USER_MODEL,
                verbose_name='Created by',
            ),
        ),
        migrations.AlterField(
            model_name='textsegment',
            name='modifiedBy',
            field=models.ForeignKey(
                blank=True,
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='evaldata_textsegment_modified_by',
                related_query_name='evaldata_textsegments',
                to=settings.AUTH_USER_MODEL,
                verbose_name='Modified by',
            ),
        ),
        migrations.AlterField(
            model_name='textsegment',
            name='retiredBy',
            field=models.ForeignKey(
                blank=True,
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='evaldata_textsegment_retired_by',
                related_query_name='evaldata_textsegments',
                to=settings.AUTH_USER_MODEL,
                verbose_name='Retired by',
            ),
        ),
    ]
