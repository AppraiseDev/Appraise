# Appraise Evaluation System

    python3 manage.py init_campaign Examples/Data/manifest.json

    # From the admin panel, create a campaign with the name 'example5data'
    # From the admin panel, add batches.json and add the batch to the campaign 'example5data'

    python3 manage.py validatecampaigndata example5data
    python3 manage.py ProcessCampaignData example5data Data
    python3 manage.py UpdateEvalDataModels
    python3 manage.py init_campaign Examples/Data/manifest.json \
        --csv-output Examples/Data/output.csv

    # See Examples/Data/outputs.csv for a SSO login for the annotator account
    # Collect some annotations, then export annotation scores...

    python3 manage.py ExportSystemScoresToCSV example5data
