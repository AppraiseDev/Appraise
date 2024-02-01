# Appraise Evaluation System

Generating an example campaign with direct assessment tasks with SQM quality
levels. Note it uses exact same batches as standard direct assessment tasks:

```
python manage.py StartNewCampaign Examples/DirectMQM/manifest.json \
    --batches-json Examples/DirectMQM/batches.json \
    --csv-output Examples/DirectMQM/output.csv

# See Examples/DirectMQM/outputs.csv for a SSO login for the annotator account
# Collect some annotations, then export annotation scores...

python manage.py ExportSystemScoresToCSV example15mqm
```