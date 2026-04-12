#!/usr/bin/env bash -x

# Exit on error
set -eo pipefail

prefix=example_contrastive_document

# Create campaign from Examples/ContrastiveDocument
$APPRAISE_MANAGE StartNewCampaign $APPRAISE_EXAMPLES/ContrastiveDocument/manifest.json \
    --batches-json $APPRAISE_EXAMPLES/ContrastiveDocument/batches.json \
    --csv-output $prefix.users.csv

# Check generated credentials
test -e $prefix.users.csv
diff --strip-trailing-cr $prefix.users.csv $prefix.users.csv.expected > $prefix.diff

# Make annotations: 3 items (itemID 0, 1, 2) with 3 scores each
# score format is score1:score2:score3
$APPRAISE_MANAGE MakeAnnotation engdeu1401:06d66923 ContrastiveDocument 10:20:30
$APPRAISE_MANAGE MakeAnnotation engdeu1401:06d66923 ContrastiveDocument 40:50:60
$APPRAISE_MANAGE MakeAnnotation engdeu1401:06d66923 ContrastiveDocument 70:80:90

# Export scores to CSV without timestamps and compare with the expected output
$APPRAISE_MANAGE ExportSystemScoresToCSV example20contrastivedoc | cut -f-9 -d, > $prefix.scores.csv
diff --strip-trailing-cr $prefix.scores.csv $prefix.scores.csv.expected

# Export scores to JSONL and compare with the expected output (strip timestamps for reproducibility)
$APPRAISE_MANAGE ExportSystemScoresToJSONL example20contrastivedoc \
    | python3 -c "
import sys, json
for line in sys.stdin:
    obj = json.loads(line)
    for key in ('start_time', 'end_time', 'duration', 'batch_number', 'item_database_id'):
        obj.pop(key, None)
    print(json.dumps(obj, sort_keys=True, ensure_ascii=False))
" > $prefix.scores.jsonl
diff --strip-trailing-cr $prefix.scores.jsonl $prefix.scores.jsonl.expected

# Exit with success code
exit $EXIT_CODE_SUCCESS
