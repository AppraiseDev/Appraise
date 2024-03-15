# Appraise Evaluation System

    python3 manage.py StartNewCampaign Examples/DataSQM/manifest.json \
        --batches-json Examples/Data/batches.json \
        --csv-output Examples/DataSQM/output.csv

    # See Examples/DataSQM/outputs.csv for a SSO login for the annotator account
    # Collect some annotations, then export annotation scores...

    python3 manage.py ExportSystemScoresToCSV example8datasqm
