# Appraise Evaluation System

An example campaign for a monolingual document-level task:

    python manage.py StartNewCampaign Examples/Monolingual/manifest.json \
        --batches-json Examples/DocumentSQM+Context/batches.json \
        --csv-output Examples/Monolingual/output.csv

    # See Examples/Monolingual/outputs.csv for a SSO login for the annotator account
    # Collect some annotations, then export annotation scores...

    python manage.py ExportSystemScoresToCSV example12mono

For a monolingual annotation task, only the target language defined in
`manifest.json` is used. Note that the `batches.json` file is exactly the same
as in `Document` and `DocLevelDA` tasks. Only `targetText` and
`targetContextLeft` are used.
