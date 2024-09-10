# Appraise Evaluation System

Generating an example campaign with pairwise assessment tasks:

    python3 manage.py init_campaign Examples/Pairwise/manifest.json
    # From the admin panel, create a campaign with the name 'example3pair'

    # From the admin panel, add batches.json and add the batch to the campaign 'example3pair'
    python3 manage.py validatecampaigndata example3pair
    python3 manage.py ProcessCampaignData example3pair Pairwise
    python3 manage.py UpdateEvalDataModels
    python3 manage.py init_campaign Examples/Pairwise/manifest.json \
        --csv-output Examples/Pairwise/output.csv

    # See Examples/Pairwise/outputs.csv for a SSO login for the annotator account
    # Collect some annotations, then export annotation scores...

    python3 manage.py ExportSystemScoresToCSV example3pair
