#!/usr/bin/env bash
set -x
for pfx in wmt21_baseline wmt22_selected; do
    for ext in json csv log stats; do
        cp $pfx.$ext $pfx.$ext.expected
    done
done
