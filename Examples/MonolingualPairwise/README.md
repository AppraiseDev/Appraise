# Appraise Evaluation System

    python manage.py StartNewCampaign Examples/MonolingualPairwise/manifest.json \
        --batches-json Examples/PairwiseDocument/batches.json \
        --csv-output Examples/MonolingualPairwise/output.csv

    # See Examples/PairwiseDocument/outputs.csv for a SSO login for the annotator account
    # Collect some annotations, then export annotation scores...

    python manage.py ExportSystemScoresToCSV example13monopair

You can use the same batches as for the `PairwiseDocument` task type. Source
texts and contexts will be ignored.

Note that the static source context (if needed) for this task should be
included in the key named `segmentContextLeft` in the `batches.json` file. This
is different than `sourceContextLeft` in the *Document* task type.
