# Appraise Evaluation System

Generating an example campaign with pairwise assessment tasks:

    python manage.py init_campaign Examples/Pairwise/manifest.json
    # From the admin panel, create a campaign with the name 'example3pair'

    # From the admin panel, add batches.json and add the batch to the campaign 'example3pair'
    python manage.py validatecampaigndata example3pair
    python manage.py ProcessCampaignData example3pair Pairwise
    python manage.py UpdateEvalDataModels
    python manage.py init_campaign Examples/Pairwise/manifest.json \
        --csv-output Examples/Pairwise/output.csv

    # See Examples/Pairwise/outputs.csv for a SSO login for the annotator account
    # Collect some annotations, then export annotation scores...

    python manage.py ExportSystemScoresToCSV example3pair
