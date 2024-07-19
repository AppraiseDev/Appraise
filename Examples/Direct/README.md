# Appraise Evaluation System

Generating an example campaign with direct assessment tasks:

    python3 manage.py init_campaign Examples/Direct/manifest.json

    # From the admin panel, create a campaign with the name 'example1'
    # From the admin panel, add batches.json and add the batch to the campaign 'example1'

    python3 manage.py validatecampaigndata example1
    python3 manage.py ProcessCampaignData example1 Direct
    python3 manage.py UpdateEvalDataModels
    python3 manage.py init_campaign Examples/Direct/manifest.json \
        --csv-output Examples/Direct/output.csv

    # See Examples/Direct/outputs.csv for a SSO login for the annotator account
    # Collect some annotations, then export annotation scores...

    python3 manage.py ExportSystemScoresToCSV example1

Alternatively run this single command to create the campaign:

    python3 manage.py StartNewCampaign Examples/Direct/manifest.json \
        --batches-json Examples/Direct/batches.json \
        --csv-output Examples/Direct/output.csv
