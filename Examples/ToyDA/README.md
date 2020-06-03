# Appraise Evaluation System

Generating an example campaign with direct assessment tasks:

    # From the admin panel, create a campaign with just a name, e.g. 'campaign1'
    python manage.py init_campaign Examples/ToyDA/manifest.json --csv-output Examples/ToyDA/output.csv
    # From the admin panel, add .json batches to the campaign 'campaign1'
    python manage.py validatecampaigndata campaign1
    python manage.py ProcessCampaignData campaign1 Direct
    python manage.py UpdateEvalDataModels
    python manage.py init_campaign Examples/ToyDA/manifest.json --csv-output Examples/ToyDA/output2.csv
    # Login with an annotator account and update the profile to have English and German as supported languages

