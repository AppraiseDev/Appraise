# Appraise Evaluation System

Generating an example document-level evaluation WMT19 campaign:

    python3 create_wmt19_tasks.py \
        Examples/DocLevelDA/sources/newstest2019-ende-src.en.sgm \
        Examples/DocLevelDA/references/newstest2019-ende-ref.de.sgm \
        Examples/DocLevelDA/system-outputs/ '*.sgm' \
        Examples/DocLevelDA/batches eng deu 2 true \
        | tee Examples/DocLevelDA/batches.log

    python3 manage.py init_campaign Examples/DocLevelDA/manifest.json

    # From the admin panel, create a campaign with the name 'example2doc'
    # From the admin panel, add batches.json and add the batch to the campaign 'example2doc'

    python3 manage.py validatecampaigndata example2doc
    python3 manage.py ProcessCampaignData example2doc DocLevelDA
    python3 manage.py UpdateEvalDataModels
    python3 manage.py init_campaign Examples/DocLevelDA/manifest.json \
        --csv-output Examples/DocLevelDA/init_campaign.csv

    # See Examples/DocLevelDA/outputs.csv for a SSO login for the annotator account
    # Collect some annotations, then export annotation scores...

    python3 manage.py ExportSystemScoresToCSV example2doc
