# Appraise Evaluation System

    python manage.py StartNewCampaign Examples/PairwiseDocument/manifest.json \
        --batches-json Examples/PairwiseDocument/batches.json \
        --csv-output Examples/PairwiseDocument/output.csv

    # See Examples/PairwiseDocument/outputs.csv for a SSO login for the annotator account
    # Collect some annotations, then export annotation scores...

    python manage.py ExportSystemScoresToCSV example10pairdoc
