# Appraise Evaluation System

Generating an example campaign for named entities evaluation:

    python manage.py StartNewCampaign Examples/DirectNamedEntities/manifest.json \
        --batches-json Examples/DirectNamedEntities/batches.json \
        --csv-output Examples/DirectNamedEntities/output.csv

    # See Examples/DirectNamedEntities/outputs.csv for a SSO login for the annotator account
    # Collect some annotations, then export annotation scores...

    python manage.py ExportSystemScoresToCSV example14namedentities
