# Appraise Evaluation System

Generating an example campaign with pairwise assessment tasks:

    python manage.py init_campaign Examples/Pairwise/manifest.json
    # From the admin panel, create a campaign with the name 'example3pair'
    python manage.py init_campaign Examples/Pairwise/manifest.json

    # From the admin panel, add batches.json and add the batch to the campaign 'example3pair'
    python manage.py validatecampaigndata example3pair
    python manage.py ProcessCampaignData example3pair Pairwise
    python manage.py UpdateEvalDataModels
    python manage.py init_campaign Examples/Pairwise/manifest.json \
        --csv-output Examples/Pairwise/output.csv

    # From the admin panel, assign user(s) to the created pairwise assessment task
    # Login into an annotator account and update the profile adding English and
    #   German as supported languages
    # Collect some annotations...

    python manage.py ExportSystemScoresToCSV example3pair

