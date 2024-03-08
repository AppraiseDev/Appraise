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

# Exit with success code
exit $EXIT_CODE_SUCCESS
