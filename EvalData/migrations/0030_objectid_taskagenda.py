# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2017-10-12 01:30
from __future__ import unicode_literals

import django.db.models.deletion
from django.conf import settings
from django.db import migrations
from django.db import models


class Migration(migrations.Migration):

    dependencies = [
        ('Campaign', '0008_auto_20171006_1436'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('EvalData', '0029_auto_20171006_1549'),
    ]

    operations = [
        migrations.CreateModel(
            name='ObjectID',
            fields=[
                (
                    'id',
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name='ID',
                    ),
                ),
                (
                    'typeName',
                    models.CharField(
                        help_text='(max. 100 characters)',
                        max_length=100,
                        verbose_name='Type name',
                    ),
                ),
                (
                    'primaryID',
                    models.CharField(
                        help_text='(max. 50 characters)',
                        max_length=50,
                        verbose_name='Primary ID',
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name='TaskAgenda',
            fields=[
                (
                    'id',
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name='ID',
                    ),
                ),
                (
                    '_completed_tasks',
                    models.ManyToManyField(
                        blank=True,
                        related_name='evaldata_taskagenda_completedtasks',
                        related_query_name='evaldata_taskagendas_completed',
                        to='EvalData.ObjectID',
                        verbose_name='Completed tasks',
                    ),
                ),
                (
                    '_open_tasks',
                    models.ManyToManyField(
                        blank=True,
                        related_name='evaldata_taskagenda_opentasks',
                        related_query_name='evaldata_taskagendas_open',
                        to='EvalData.ObjectID',
                        verbose_name='Open tasks',
                    ),
                ),
                (
                    'campaign',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to='Campaign.Campaign',
                        verbose_name='Campaign',
                    ),
                ),
                (
                    'user',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                        verbose_name='User',
                    ),
                ),
            ],
        ),
    ]
