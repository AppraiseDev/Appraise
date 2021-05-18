# Appraise Evaluation System

Generating an example document-level evaluation campaign with an entire
document on screen and Scalar Quality Metric (SQM) instead of Direct Assessment
(DA). Note that batches.json used for this view has the same format as for a
DocLevelDA task.

    python manage.py init_campaign Examples/SQMDocument/manifest.json

    # From the admin panel, create a campaign with the name 'example6SQMdoc'
    # From the admin panel, add Examples/Document/batches.json and add the batch to the campaign 'example6SQMdoc'

    python manage.py validatecampaigndata example6SQMdoc
    python manage.py ProcessCampaignData example6SQMdoc Document
    python manage.py UpdateEvalDataModels
    python manage.py init_campaign Examples/SQMDocument/manifest.json \
        --csv-output Examples/SQMDocument/init_campaign.csv

    # See Examples/SQMDocument/outputs.csv for a SSO login for the annotator account
    # Collect some annotations, then export annotation scores...

    python manage.py ExportSystemScoresToCSV example6SQMdoc
