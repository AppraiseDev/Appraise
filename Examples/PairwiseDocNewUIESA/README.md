# Appraise Evaluation System

    python3 manage.py StartNewCampaign Examples/PairwiseDocNewUIESA/manifest.json \
        --batches-json Examples/PairwiseDocNewUIESA/batches.json \
        --csv-output Examples/PairwiseDocNewUIESA/output.csv

    # See Examples/PairwiseDocNewUI-ESA/outputs.csv for a SSO login for the annotator account
    # Collect some annotations, then export annotation scores...

    python3 manage.py ExportSystemScoresToCSV example18docnewuiesa

# Score Descriptions

  score = Math.max(0, 100 - 4 * number_of_minor_errors  - 20 * number_of_major_errors)
