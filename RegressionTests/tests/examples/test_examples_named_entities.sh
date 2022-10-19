#!/usr/bin/env bash -x

# Exit on error
set -eo pipefail

prefix=example_named_entities

# Create campaign from Examples/Direct
$APPRAISE_MANAGE StartNewCampaign $APPRAISE_EXAMPLES/DirectNamedEntities/manifest.json \
    --batches-json $APPRAISE_EXAMPLES/DirectNamedEntities/batches.json \
    --csv-output $prefix.users.csv

# Check generated credentials
test -e $prefix.users.csv
diff $prefix.users.csv $prefix.users.csv.expected > $prefix.diff

# Make a few annotations
for score in 0 1 2 3 5 0 1 2 3 5; do
    $APPRAISE_MANAGE MakeAnnotation engdeu0e01:3c1604b9 Direct $score
done

# Export scores without timestamps and compare with the expected output
$APPRAISE_MANAGE ExportSystemScoresToCSV example14namedentities | cut -f-7 -d, > $prefix.scores.csv
diff $prefix.scores.csv $prefix.scores.csv.expected

# Exit with success code
exit $EXIT_CODE_SUCCESS
