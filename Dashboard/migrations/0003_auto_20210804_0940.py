# Generated by Django 3.2.6 on 2021-08-04 09:40
from django.db import migrations
from django.db import models


class Migration(migrations.Migration):

    dependencies = [
        ('Dashboard', '0002_auto_20200601_1217'),
    ]

    operations = [
        migrations.AlterField(
            model_name='timedkeyvaluedata',
            name='id',
            field=models.BigAutoField(
                auto_created=True,
                primary_key=True,
                serialize=False,
                verbose_name='ID',
            ),
        ),
        migrations.AlterField(
            model_name='userinvitetoken',
            name='id',
            field=models.BigAutoField(
                auto_created=True,
                primary_key=True,
                serialize=False,
                verbose_name='ID',
            ),
        ),
    ]
