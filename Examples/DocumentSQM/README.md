# Appraise Evaluation System

An example campaign featuring document-level DA tasks using SQM quality levels.

    python manage.py StartNewCampaign Examples/DocumentSQM/manifest.json \
        --batches-json Examples/Document/batches.json \
        --csv-output Examples/DocumentSQM/output.csv

    # See Examples/DocumentSQM/outputs.csv for a SSO login for the annotator account
    # Collect some annotations, then export annotation scores...

    python manage.py ExportSystemScoresToCSV example9docsqm
