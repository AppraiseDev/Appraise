#!/usr/bin/env bash -x

# Exit on error
set -eo pipefail

prefix=example_direct

# Create campaign from Examples/Direct
$APPRAISE_MANAGE StartNewCampaign $APPRAISE_EXAMPLES/Direct/manifest.json \
    --batches-json $APPRAISE_EXAMPLES/Direct/batches.json \
    --csv-output $prefix.users.csv

# Check generated credentials
test -e $prefix.users.csv
diff $prefix.users.csv $prefix.users.csv.expected > $prefix.diff

# Make a few annotations
for score in $( seq 10 10 100 ); do
    $APPRAISE_MANAGE MakeAnnotation engdeu0101:5ddd60c3 Direct $score
done

# Export scores without timestamps and compare with the expected output
$APPRAISE_MANAGE ExportSystemScoresToCSV example1 | cut -f-7 -d, > $prefix.scores.csv
diff $prefix.scores.csv $prefix.scores.csv.expected

# Exit with success code
exit $EXIT_CODE_SUCCESS
