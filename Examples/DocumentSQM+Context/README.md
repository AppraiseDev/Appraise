# Appraise Evaluation System

An example campaign featuring document-level DA tasks using SQM quality levels
and displaying static source and target contexts:

    python manage.py StartNewCampaign Examples/DocumentSQM+Context/manifest.json \
        --batches-json Examples/DocumentSQM+Context/batches.json \
        --csv-output Examples/DocumentSQM+Context/output.csv

    # See Examples/DocumentSQM+Context/outputs.csv for a SSO login for the annotator account
    # Collect some annotations, then export annotation scores...

    python manage.py ExportSystemScoresToCSV example9docsqm

Note that the `batches.json` file can remain exactly the same as in `Document`
and `DocLevelDA` tasks. Displaying document context requires adding it into
`sourceContextLeft` and `targetContextLeft` keys in the first and last item of
each document in `batches.json`.
