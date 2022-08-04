# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2017-10-06 21:23
from __future__ import unicode_literals

from django.db import migrations
from django.db import models


class Migration(migrations.Migration):

    dependencies = [
        ('EvalData', '0025_auto_20171006_1406'),
    ]

    operations = [
        migrations.AddField(
            model_name='textpair',
            name='_str_name',
            field=models.TextField(default='', editable=False),
        ),
        migrations.AddField(
            model_name='textpairwithimage',
            name='_str_name',
            field=models.TextField(default='', editable=False),
        ),
        migrations.AddField(
            model_name='textsegment',
            name='_str_name',
            field=models.TextField(default='', editable=False),
        ),
    ]
