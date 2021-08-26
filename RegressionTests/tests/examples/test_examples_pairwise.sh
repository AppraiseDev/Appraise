#!/usr/bin/env bash -x

# Exit on error
set -eo pipefail

prefix=example_pairwise

# Create campaign from Examples/Pairwise
$APPRAISE_MANAGE StartNewCampaign $APPRAISE_EXAMPLES/Pairwise/manifest.json \
    --batches-json $APPRAISE_EXAMPLES/Pairwise/batches.json \
    --csv-output $prefix.users.csv

# Check generated credentials
test -e $prefix.users.csv
diff $prefix.users.csv $prefix.users.csv.expected > $prefix.diff

# Make a few annotations
for score in $( seq 10 10 90 ); do
    $APPRAISE_MANAGE MakeAnnotation engdeu0301:6531faf3 Pairwise $score:$(( $score + 10 ))
done

# Export scores without timestamps and compare with the expected output
$APPRAISE_MANAGE ExportSystemScoresToCSV example3pair | cut -f-7 -d, > $prefix.scores.csv
diff $prefix.scores.csv $prefix.scores.csv.expected

# Exit with success code
exit $EXIT_CODE_SUCCESS
