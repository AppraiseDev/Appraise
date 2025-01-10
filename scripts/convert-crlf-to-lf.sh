#!/bin/bash
set -e
for e in js json html css expected csv md sh log yml xml; do
  for f in $(find . -name "*.$e" | grep -v "venv"); do
    dos2unix $f
  done
done
for f in $(git status | grep modified | tr -s ' ' '\t' | cut -f3); do
  git add $f
done
