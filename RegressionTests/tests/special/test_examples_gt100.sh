#!/usr/bin/env bash -x

# Exit on error
set -eo pipefail

prefix=example_gt100

mkdir -p Batches

# duplicate the last 10 examples in the list but increase "itemID" by one
python3 <<EOF
import json
with open("$APPRAISE_EXAMPLES/MQM+ESA/batches_esa.json") as f:
    data = json.load(f)
for task in data:
    task["items"] += [{**item, "itemID": item["itemID"] + 1} for item in task["items"][-10:]]
with open("Batches/${prefix}_batches_esa.json", "w") as f:
    json.dump(data, f, indent=2)
EOF

# Create campaign from Examples/DirectMQM
$APPRAISE_MANAGE StartNewCampaign manifest_gt100.json \
    --batches-json Batches/${prefix}_batches_esa.json \
    --csv-output ${prefix}.users.csv

# Make 120 annotations
for score in $( seq 1 110 ); do
    $APPRAISE_MANAGE MakeAnnotation engdeu9604:e0829752 Document $score --mqm '[{"start_i": 0, "end_i": 50, "severity": "major"}]'
done

# Export scores without timestamps and compare with the expected output, it should be only 110 annotations
# Escape quotes in MQM fields
$APPRAISE_MANAGE ExportSystemScoresToCSV example15esaGT100 | sed "s/, /| /g" | cut -f-10 -d, | sed "s/| /, /g" > ${prefix}.scores.csv
diff --strip-trailing-cr ${prefix}.scores.csv ${prefix}.scores.csv.expected

# Exit with success code
exit $EXIT_CODE_SUCCESS
