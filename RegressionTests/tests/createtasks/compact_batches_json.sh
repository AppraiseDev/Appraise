#!/usr/bin/env bash
grep -vP '"sourceContext|"sourceText|"targetContext|"targetText' | tr '\n' ' ' | sed -r -e 's/([\}]),?/\1\n/g' -e 's/\[/\[\n/g'
