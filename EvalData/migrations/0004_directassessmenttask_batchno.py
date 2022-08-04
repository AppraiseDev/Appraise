# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2017-06-02 14:13
from __future__ import unicode_literals

from django.db import migrations
from django.db import models


class Migration(migrations.Migration):

    dependencies = [
        ('EvalData', '0003_auto_20170602_0447'),
    ]

    operations = [
        migrations.AddField(
            model_name='directassessmenttask',
            name='batchNo',
            field=models.PositiveIntegerField(
                default=-1, help_text='(1-based)', verbose_name='Batch No'
            ),
            preserve_default=False,
        ),
    ]
