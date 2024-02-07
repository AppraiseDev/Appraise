# Appraise Evaluation System

Generating an example campaign with pairwise direct assessment tasks using SQM
quality levels. Note that this example uses exact same batches as
`Examples/Pairwise`:

    python3 manage.py StartNewCampaign Examples/PairwiseSQM/manifest.json \
        --batches-json Examples/Pairwise/batches.json \
        --csv-output Examples/PairwiseSQM/output.csv

    # See Examples/PairwiseSQM/outputs.csv for a SSO login for the annotator account
    # Collect some annotations, then export annotation scores...

    python3 manage.py ExportSystemScoresToCSV example7sqm
