# Appraise Evaluation System

Generating an example campaign with direct assessment tasks with SQM quality
levels. Note it uses exact same batches as standard direct assessment tasks:

```
# clean up previous iteration
rm -rf static appraise.log db.sqlite3 Batches;

# setup
python3 manage.py migrate;
DJANGO_SUPERUSER_USERNAME=test DJANGO_SUPERUSER_PASSWORD=test python3 manage.py createsuperuser --noinput --email "test@test.test";
python3 manage.py collectstatic --no-post-process;

python3 manage.py StartNewCampaign Examples/DirectMQM/manifest_esa.json \
    --batches-json Examples/DirectMQM/batches_wmt23_en-cs.json \
    --csv-output Examples/DirectMQM/output_esa.csv;

python3 manage.py runserver;


python3 manage.py StartNewCampaign Examples/DirectMQM/manifest_mqm.json \
   --batches-json Examples/DirectMQM/batches_wmt23_en-de.json \
   --csv-output Examples/DirectMQM/output_mqm.csv;

python3 manage.py runserver;

# See Examples/DirectMQM/outputs.csv for a SSO login for the annotator account
# Collect some annotations, then export annotation scores...

python3 manage.py ExportSystemScoresToCSV example15mqm
```