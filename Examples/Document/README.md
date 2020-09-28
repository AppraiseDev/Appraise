# Appraise Evaluation System

Generating an example document-level evaluation campaign with an entire
document on screen view. Note that batches.json used for this view has the same
format as for a DocLevelDA task.

    python manage.py init_campaign Examples/Document/manifest.json
    # From the admin panel, create a campaign with the name 'example4docfull'
    python manage.py init_campaign Examples/Document/manifest.json

    # From the admin panel, add batches.json and add the batch to the campaign 'example4docfull'
    python manage.py validatecampaigndata example4docfull
    python manage.py ProcessCampaignData example4docfull Document
    python manage.py UpdateEvalDataModels
    python manage.py init_campaign Examples/Document/manifest.json \
        --csv-output Examples/Document/init_campaign.csv

    # Login into an annotator account and update the profile adding English and
    #   German as supported languages
