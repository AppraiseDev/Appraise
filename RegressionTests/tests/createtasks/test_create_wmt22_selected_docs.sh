#!/usr/bin/env bash -x

# Exit on error
set -eo pipefail

prefix=wmt22_selected

rm -f $prefix*.{log,csv,json,stats,diff}

$APPRAISE_PYTHON $APPRAISE_ROOT/Scripts/create_wmt22_tasks.py \
    -f newstest2021.de-fr.example.xml -o $prefix -s deu -t fra --rng-seed 2222 \
    --selected-docs selected_docids.tsv --static-context 5 \
    | tee $prefix.full.log

test -s $prefix.full.log
test -s $prefix.csv
test -s $prefix.json

grep -P ">>>|Total" < $prefix.full.log > $prefix.log
$APPRAISE_PYTHON compute_batch_stats.py < $prefix.json > $prefix.stats

diff --strip-trailing-cr $prefix.log.expected $prefix.log | tee $prefix.log.diff
diff --strip-trailing-cr $prefix.csv.expected $prefix.csv | tee $prefix.csv.diff
diff --strip-trailing-cr $prefix.json.expected $prefix.json | tee $prefix.json.diff
diff --strip-trailing-cr $prefix.stats.expected $prefix.stats | tee $prefix.stats.diff

# Exit with success code
exit $EXIT_CODE_SUCCESS
