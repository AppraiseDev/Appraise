# Appraise Evaluation System

Generating an example document-level evaluation campaign with an entire
document on screen view. Note that batches.json used for this view has the same
format as for a DocLevelDA task.

    python manage.py init_campaign Examples/MQMDocument/manifest.json

    # From the admin panel, create a campaign with the name 'example7MQMdoc'
    # From the admin panel, add batches.json and add the batch to the campaign 'example7MQMdoc'

    python manage.py validatecampaigndata example7MQMdoc
    python manage.py ProcessCampaignData example7MQMdoc Document
    python manage.py UpdateEvalDataModels
    python manage.py init_campaign Examples/MQMDocument/manifest.json \
        --csv-output Examples/MQMDocument/init_campaign.csv

    # See Examples/MQMDocument/outputs.csv for a SSO login for the annotator account
    # Collect some annotations, then export annotation scores...

    python manage.py ExportSystemScoresToCSV example7MQMdoc
