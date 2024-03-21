# Appraise Evaluation System

    python3 manage.py StartNewCampaign Examples/PairwiseDocNewUI/manifest.json \
        --batches-json Examples/PairwiseDocNewUI/batches.json \
        --csv-output Examples/PairwiseDocNewUI/output.csv

    # See Examples/PairwiseDocNewUI/outputs.csv for a SSO login for the annotator account
    # Collect some annotations, then export annotation scores...

    python3 manage.py ExportSystemScoresToCSV example17docnewui
