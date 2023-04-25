#!/usr/bin/env bash -x

# Exit on error
set -eo pipefail

prefix=example_pairwise_errors

# Create campaign from Examples/PairwiseSQM with added 'ReportCriticalErrors' option
$APPRAISE_MANAGE StartNewCampaign <(cat $APPRAISE_EXAMPLES/PairwiseSQM/manifest.json | sed 's/"SQM"/"SQM;ReportCriticalErrors"/') \
    --batches-json $APPRAISE_EXAMPLES/Pairwise/batches.json \
    --csv-output $prefix.users.csv

# Check generated credentials
test -e $prefix.users.csv
diff $prefix.users.csv $prefix.users.csv.expected > $prefix.diff

# Make a few annotations
for score in $( seq 10 10 50 ); do
    $APPRAISE_MANAGE MakeAnnotation engdeu0701:55780fa8 Pairwise $score:$(( $score + 10 )) \
        --target-errors serious-semantic-error1:serious-semantic-error2
done

for score in $( seq 60 10 90 ); do
    $APPRAISE_MANAGE MakeAnnotation engdeu0701:55780fa8 Pairwise $score:$(( $score + 10 )) \
        --source-error error-in-source-text --target-errors None:serious-semantic-error3
done

# Export scores without timestamps and compare with the expected output
$APPRAISE_MANAGE ExportSystemScoresToCSV example7sqm | cut -f-9 -d, > $prefix.scores.csv
diff $prefix.scores.csv $prefix.scores.csv.expected

# Exit with success code
exit $EXIT_CODE_SUCCESS
