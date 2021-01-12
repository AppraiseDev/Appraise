# Appraise Evaluation System

Generating an example campaign with direct assessment tasks:

    python manage.py init_campaign Examples/Direct/manifest.json

    # From the admin panel, create a campaign with the name 'example1'
    # From the admin panel, add batches.json and add the batch to the campaign 'example1'

    python manage.py validatecampaigndata example1
    python manage.py ProcessCampaignData example1 Direct
    python manage.py UpdateEvalDataModels
    python manage.py init_campaign Examples/Direct/manifest.json \
        --csv-output Examples/Direct/output.csv

    # See Examples/Direct/outputs.csv for a SSO login for the annotator account
    # Collect some annotations, then export annotation scores...

    python manage.py ExportSystemScoresToCSV example1
