# Generated by Django 3.2.12 on 2022-10-20 08:00
from django.db import migrations
from django.db import models


class Migration(migrations.Migration):

    dependencies = [
        ('EvalData', '0051_auto_20221018_1627'),
    ]

    operations = [
        migrations.AddField(
            model_name='directassessmentdocumentresult',
            name='sourceErrors',
            field=models.TextField(
                blank=True,
                help_text='(max. 2000 characters)',
                max_length=2000,
                null=True,
                verbose_name='Source errors',
            ),
        ),
        migrations.AddField(
            model_name='pairwiseassessmentresult',
            name='sourceErrors',
            field=models.TextField(
                blank=True,
                help_text='(max. 2000 characters)',
                max_length=2000,
                null=True,
                verbose_name='Source errors',
            ),
        ),
    ]
