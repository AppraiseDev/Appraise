# Appraise Evaluation System

    python3 manage.py StartNewCampaign Examples/PairwiseDocESA/manifest.json \
        --batches-json Examples/PairwiseDocESA/batches.json \
        --csv-output Examples/PairwiseDocESA/output.csv

    # See Examples/PairwiseDocESA/outputs.csv for a SSO login for the annotator account
    # Collect some annotations, then export annotation scores...

    python3 manage.py ExportSystemScoresToCSV example18docnewuiesa

# Score Descriptions

  score = Math.max(0, 100 - 4 * number_of_minor_errors  - 20 * number_of_major_errors)
