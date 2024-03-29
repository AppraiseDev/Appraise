# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2017-06-08 04:20
from __future__ import unicode_literals

from django.db import migrations
from django.db import models


class Migration(migrations.Migration):

    dependencies = [
        ('EvalData', '0017_auto_20170605_1520'),
    ]

    operations = [
        migrations.AlterField(
            model_name='textpair',
            name='itemType',
            field=models.CharField(
                choices=[
                    ('SRC', 'Source text'),
                    ('TGT', 'Target text'),
                    ('REF', 'Reference text'),
                    ('BAD', 'Bad reference'),
                    ('CHK', 'Redundant check'),
                ],
                db_index=True,
                max_length=5,
                verbose_name='Item type',
            ),
        ),
        migrations.AlterField(
            model_name='textsegment',
            name='itemType',
            field=models.CharField(
                choices=[
                    ('SRC', 'Source text'),
                    ('TGT', 'Target text'),
                    ('REF', 'Reference text'),
                    ('BAD', 'Bad reference'),
                    ('CHK', 'Redundant check'),
                ],
                db_index=True,
                max_length=5,
                verbose_name='Item type',
            ),
        ),
    ]
