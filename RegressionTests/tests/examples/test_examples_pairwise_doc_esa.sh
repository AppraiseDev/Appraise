#!/usr/bin/env bash -x

# Exit on error
set -eo pipefail

prefix=example_pairwise_doc_esa

# Create campaign from Examples\PairwiseDocESA
$APPRAISE_MANAGE StartNewCampaign $APPRAISE_EXAMPLES/PairwiseDocESA/manifest.json \
    --batches-json $APPRAISE_EXAMPLES/PairwiseDocESA/batches.json \
    --csv-output $prefix.users.csv

# Check generated credentials
test -e $prefix.users.csv
diff $prefix.users.csv $prefix.users.csv.expected > $prefix.diff

# Make a few annotations
for score in $( seq 10 10 90 ); do
    $APPRAISE_MANAGE MakeAnnotation deueng1201:a600717f PairwiseDocumentESA $score:$(( $score + 10 )) --mqm '[{"start_i": 0, "end_i": 50, "severity": "major"}]' '[{"start_i": 0, "end_i": 50, "severity": "major"}]'
done

# Export scores without timestamps and compare with the expected output
$APPRAISE_MANAGE ExportSystemScoresToCSV example18docnewuiesa | sed "s/, /| /g" | cut -f-10 -d, | sed "s/| /, /g" > $prefix.scores.csv
diff $prefix.scores.csv $prefix.scores.csv.expected

# Exit with success code
exit $EXIT_CODE_SUCCESS
