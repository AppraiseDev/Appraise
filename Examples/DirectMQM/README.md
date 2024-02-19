# Appraise Evaluation System

Generating an example campaign with direct assessment tasks with SQM quality
levels. Note it uses exact same batches as standard direct assessment tasks:

```

rm -rf static appraise.log db.sqlite3 Batches;

python manage.py migrate;

DJANGO_SUPERUSER_USERNAME=test DJANGO_SUPERUSER_EMAIL="" DJANGO_SUPERUSER_PASSWORD=test python manage.py createsuperuser --noinput;

python manage.py collectstatic --no-post-process;

python manage.py StartNewCampaign Examples/DirectMQM/manifest_mqm.json \
    --batches-json Examples/DirectMQM/batches_wmt23_en-de.json \
    --csv-output Examples/DirectMQM/output_mqm.csv;

python manage.py StartNewCampaign Examples/DirectMQM/manifest_lqm.json \
    --batches-json Examples/DirectMQM/batches_wmt23_en-de.json \
    --csv-output Examples/DirectMQM/output_lqm.csv;

python manage.py runserver;

# See Examples/DirectMQM/outputs.csv for a SSO login for the annotator account
# Collect some annotations, then export annotation scores...

python3 manage.py ExportSystemScoresToCSV example15mqm
```