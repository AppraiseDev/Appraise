from django.db import migrations
from django.db import models


class Migration(migrations.Migration):

    dependencies = [
        ( 'EvalData', '0049_auto_20220629_1315', ),
    ]

    operations = [
        migrations.AddField(
            model_name='TextPair',
            name='mqm',
            field=models.TextField(
                blank=True, null=True, verbose_name='MQM'
            ),
        ),

        migrations.AddField(
            model_name='DirectAssessmentResult',
            name='mqm',
            field=models.TextField(
                blank=True, null=True, verbose_name='MQM'
            ),
        ),
    ]
