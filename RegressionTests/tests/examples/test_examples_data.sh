#!/usr/bin/env bash -x

# Exit on error
set -eo pipefail

prefix=example_data

# Create campaign from Examples/Data
$APPRAISE_MANAGE StartNewCampaign $APPRAISE_EXAMPLES/Data/manifest.json \
    --batches-json $APPRAISE_EXAMPLES/Data/batches.json \
    --csv-output $prefix.users.csv

# Check generated credentials
test -e $prefix.users.csv
diff $prefix.users.csv $prefix.users.csv.expected > $prefix.diff

# Make a few annotations
for score in $( seq 10 10 100 ); do
    $APPRAISE_MANAGE MakeAnnotation engdeu0501:6574e0e0 Data $score:1
done
for score in $( seq 5 10 100 ); do
    $APPRAISE_MANAGE MakeAnnotation engdeu0502:dfdd1289 Data $score:4
done

# Export scores without timestamps and compare with the expected output
$APPRAISE_MANAGE ExportSystemScoresToCSV example5data | cut -f-7 -d, > $prefix.scores.csv
diff $prefix.scores.csv $prefix.scores.csv.expected

# Exit with success code
exit $EXIT_CODE_SUCCESS
