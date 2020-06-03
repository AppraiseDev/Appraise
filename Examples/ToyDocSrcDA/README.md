# Appraise Evaluation System

Generating an example document-level evaluation WMT19 campaign:

    python create_wmt19_tasks.py Examples/ToyDocSrcDA/sources/newstest2019-ende-src.en.sgm Examples/ToyDocSrcDA/references/newstest2019-ende-ref.de.sgm \
        Examples/ToyDocSrcDA/system-outputs/ '*.sgm' \
        Examples/ToyDocSrcDA/batch eng deu 2 false | tee Examples/ToyDocSrcDA/create_wmt19_tasks.log
    # From the admin panel, create campaign2doc
    python manage.py init_campaign Examples/ToyDocSrcDA/manifest.json
    # From the admin panel, add .json batches to the campaign2doc
    python manage.py validatecampaigndata campaign2doc
    python manage.py ProcessCampaignData campaign2doc DocLevelDA
    python manage.py UpdateEvalDataModels
    python manage.py init_campaign Examples/ToyDocSrcDA/manifest.json --csv-output Examples/ToyDocSrcDA/init_campaign.csv
    # Login with an annotator account and update the profile to have English and German as supported languages

