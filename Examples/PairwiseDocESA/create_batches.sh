#!/bin/bash
set -x
python3 ../../Scripts/create_wmt22_pairwise_tasks.py -o batches -f ../PairwiseDocNewUI/example.tsv --tsv \
    --max-segs 100 -s deu -t eng -A system-A -B system-B --rng-seed 1111 --no-qc |& tee batches.run.log
