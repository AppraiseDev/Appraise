# Appraise Evaluation System

Generating an example document-level evaluation campaign with an entire
document on screen view. Note that batches.json used for this view has the same
format as for a DocLevelDA task.

    python3 manage.py init_campaign Examples/Document/manifest.json

    # From the admin panel, create a campaign with the name 'example4fulldoc'
    # From the admin panel, add batches.json and add the batch to the campaign 'example4fulldoc'

    python3 manage.py validatecampaigndata example4fulldoc
    python3 manage.py ProcessCampaignData example4fulldoc Document
    python3 manage.py UpdateEvalDataModels
    python3 manage.py init_campaign Examples/Document/manifest.json \
        --csv-output Examples/Document/init_campaign.csv

    # See Examples/Document/outputs.csv for a SSO login for the annotator account
    # Collect some annotations, then export annotation scores...

    python3 manage.py ExportSystemScoresToCSV example4fulldoc
