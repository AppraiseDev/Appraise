# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2017-06-02 14:39
from __future__ import unicode_literals

import django.db.models.deletion
from django.db import migrations
from django.db import models


class Migration(migrations.Migration):

    dependencies = [
        ('EvalData', '0006_directassessmenttask_batchdata'),
    ]

    operations = [
        migrations.AlterField(
            model_name='directassessmenttask',
            name='batchData',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='evaldata_directassessmenttask_campaigndata',
                related_query_name='evaldata_directassessmenttasks',
                to='Campaign.CampaignData',
                verbose_name='Campaign data',
            ),
        ),
    ]
