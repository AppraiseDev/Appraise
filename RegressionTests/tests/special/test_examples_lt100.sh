#!/usr/bin/env bash -x

# Exit on error
set -eo pipefail

prefix=example_lt100

mkdir -p Batches

# $APPRAISE_EXAMPLES/MQM+ESA/batches_esa.json is a list of dictionaries, each containing among other fields a field "items", which is a list
# read $APPRAISE_EXAMPLES/MQM+ESA/batches_esa.json and keep only the first 10 examples in each "items" list
python3 <<EOF
import json
with open("$APPRAISE_EXAMPLES/MQM+ESA/batches_esa.json") as f:
    data = json.load(f)
for item in data:
    item["items"] = item["items"][:10]
with open("Batches/${prefix}_batches_esa.json", "w") as f:
    json.dump(data, f, indent=2)
EOF

# Create campaign from Examples/DirectMQM
$APPRAISE_MANAGE StartNewCampaign manifest_lt100.json \
    --batches-json Batches/${prefix}_batches_esa.json \
    --csv-output ${prefix}.users.csv

# Make 10 annotations
for score in $( seq 1 10 ); do
    $APPRAISE_MANAGE MakeAnnotation engdeu9704:17d9e109 Document $score --mqm '[{"start_i": 0, "end_i": 50, "severity": "major"}]'
done

# Export scores without timestamps and compare with the expected output
# Escape quotes in MQM fields
$APPRAISE_MANAGE ExportSystemScoresToCSV example15esaLT100 | sed "s/, /| /g" | cut -f-10 -d, | sed "s/| /, /g" > ${prefix}.scores.csv
diff --strip-trailing-cr ${prefix}.scores.csv ${prefix}.scores.csv.expected

# Make two more annotations, should not create any new entries in the scores file
for score in $( seq 1 3 ); do
    $APPRAISE_MANAGE MakeAnnotation engdeu9704:17d9e109 Document $score --mqm '[{"start_i": 0, "end_i": 50, "severity": "major"}]'
done

# the output should remain the same
$APPRAISE_MANAGE ExportSystemScoresToCSV example15esaLT100 | sed "s/, /| /g" | cut -f-10 -d, | sed "s/| /, /g" > ${prefix}.scores2.csv
diff --strip-trailing-cr ${prefix}.scores2.csv ${prefix}.scores.csv.expected


# Exit with success code
exit $EXIT_CODE_SUCCESS
