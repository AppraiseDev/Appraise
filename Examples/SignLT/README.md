# Appraise Evaluation System

An example campaign featuring document-level DA tasks for sign languages:

    python manage.py StartNewCampaign Examples/SignLT/manifest.json \
        --batches-json Examples/SignLT/batches.sgg-deu.json Examples/SignLT/batches.deu-sgg.json \
        --csv-output Examples/SignLT/output.csv

    # See Examples/SignLT/outputs.csv for a SSO login for the annotator account
    # Collect some annotations, then export annotation scores...

    python manage.py ExportSystemScoresToCSV example11signlt
