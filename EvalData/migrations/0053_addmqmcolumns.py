from django.db import migrations
from django.db import models


class Migration(migrations.Migration):

    dependencies = [
        ( 'EvalData', '0052_auto_20221020_0800', ),
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
        migrations.AddField(
            model_name='DirectAssessmentDocumentResult',
            name='mqm',
            field=models.TextField(
                blank=True, null=True, verbose_name='MQM'
            ),
        ),
    ]
