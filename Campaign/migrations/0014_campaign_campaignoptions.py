# Generated by Django 2.2.26 on 2022-02-17 16:34
from django.db import migrations
from django.db import models


class Migration(migrations.Migration):

    dependencies = [
        ('Campaign', '0014_auto_20210804_0940'),
    ]

    operations = [
        migrations.AddField(
            model_name='campaign',
            name='campaignOptions',
            field=models.TextField(
                blank=True, null=True, verbose_name='Campaign task-specific options'
            ),
        ),
    ]
