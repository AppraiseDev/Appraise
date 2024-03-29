# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2017-06-02 15:17
from __future__ import unicode_literals

from django.db import migrations
from django.db import models


class Migration(migrations.Migration):

    dependencies = [
        ('Campaign', '0002_auto_20170501_1437'),
    ]

    operations = [
        migrations.AlterField(
            model_name='campaign',
            name='campaignName',
            field=models.CharField(
                help_text='(max. 250 characters)',
                max_length=250,
                verbose_name='Campaign name',
            ),
        ),
        migrations.AlterField(
            model_name='campaignteam',
            name='teamName',
            field=models.CharField(
                help_text='(max. 250 characters)',
                max_length=250,
                verbose_name='Team name',
            ),
        ),
    ]
