# Appraise Evaluation System

Generating an example campaign with pairwise assessment tasks:

    # From the admin panel, create a campaign with just a name, e.g. 'campaign5pair'
    python manage.py init_campaign Examples/ToyPairwiseDA/manifest.json --csv-output Examples/ToyPairwiseDA/output.csv
    # From the admin panel, add .json batches to the campaign 'campaign5pair'
    python manage.py validatecampaigndata campaign5pair
    python manage.py ProcessCampaignData campaign5pair Pairwise
    python manage.py UpdateEvalDataModels
    python manage.py init_campaign Examples/ToyPairwiseDA/manifest.json --csv-output Examples/ToyPairwiseDA/output2.csv
    # From the admin panel, assign user(s) to the created Pairwise assessment task
    # Login with an annotator account and update the profile to have English and German as supported languages
    # After some nnotations have been collected ...
    python manage.py ExportSystemScoresToCSV campaign5pair

