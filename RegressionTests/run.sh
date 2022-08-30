#!/usr/bin/env bash

# Appraise evaluation framework
# See LICENSE for usage details

SHELL=/bin/bash


##########################################################################
# Helper functions

export LC_ALL=C.UTF-8

function log {
    echo [$(date "+%m/%d/%Y %T")] $@
}

function logn {
    echo -n [$(date "+%m/%d/%Y %T")] $@
}

function format_time {
    dt=$(echo "$2 - $1" | bc 2>/dev/null)
    dh=$(echo "$dt/3600" | bc 2>/dev/null)
    dt2=$(echo "$dt-3600*$dh" | bc 2>/dev/null)
    dm=$(echo "$dt2/60" | bc 2>/dev/null)
    ds=$(echo "$dt2-60*$dm" | bc 2>/dev/null)
    LANG=C printf "%02d:%02d:%02.3fs" $dh $dm $ds
}


##########################################################################
# Setup environment

log "Appraise Git commit: $( git rev-parse --verify HEAD | cut -c-7)"

export APPRAISE_TESTS_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
export APPRAISE_ROOT=$( realpath $APPRAISE_TESTS_DIR/../ )
export APPRAISE_DATABASE=development.db
export APPRAISE_DB_NAME=default
export APPRAISE_EXAMPLES="$APPRAISE_ROOT/Examples"
# Disable Django Debug Toolbar for regression testing
export APPRAISE_DEBUG=

log "Appraise root directory: $APPRAISE_ROOT"

# Set absolute path to python executable
export APPRAISE_PYTHON=${PYTHONBIN:-"$APPRAISE_ROOT/venv/bin/python3"}
test -f $APPRAISE_PYTHON || APPRAISE_PYTHON=$(command -v python3)
log "Python executable: $APPRAISE_PYTHON"
log "Python version: $($APPRAISE_PYTHON --version)"
export APPRAISE_MANAGE="$APPRAISE_PYTHON $APPRAISE_ROOT/manage.py"

if ! command -v $APPRAISE_PYTHON > /dev/null; then
    echo "Python environment not found. Did you follow INSTALL.md?"
    exit 1
fi

# This is quite fragile, but seems to work for now. Other (quickly) tested
# approaches for running regression tests on a dedicated database:
#
# 1. Setting up a new database name and using --database in management
#   commands, but custom commands do not support this yet, and I'm not sure if
#   it's possible to switch the database on the fly.
# 2. Using custom local_settings.py file, but it would be mostly a copy of the
#   basic settings.py and could overwrite developer's custom local settings.
#
# Setup a database for regression tests.
log "Using database: $APPRAISE_DATABASE"
sed -ri.bak "s/development\\.db/$APPRAISE_DATABASE/g" "$APPRAISE_ROOT/Appraise/settings.py"

# Prepare database
$APPRAISE_PYTHON manage.py migrate --database $APPRAISE_DB_NAME
$APPRAISE_PYTHON manage.py flush   --database $APPRAISE_DB_NAME --no-input

# Create superuser
$APPRAISE_PYTHON manage.py createsuperuser --database $APPRAISE_DB_NAME \
    --no-input --username admin --email admin@appraise.org


##########################################################################
# Run regression tests

# Default directory with all regression tests is 'tests'
test_prefixes="$APPRAISE_TESTS_DIR/tests"
if [ $# -ge 1 ]; then
    test_prefixes=$1
fi
test_dirs=$(find $test_prefixes -type d | grep -v "/_")

# Exit codes
export EXIT_CODE_SUCCESS=0

success=true
count_all=0
count_failed=0
count_passed=0

declare -a tests_failed

time_start=$(date +%s.%N)

log "Running regression tests..."
for test_dir in $test_dirs; do
    log "Checking directory: $test_dir"

    for test_path in $(ls -A $test_dir/test_*.sh 2>/dev/null); do
        test_file=$( basename $test_path )
        test_name="${test_file%.*}"
        test_time_start=$(date +%s.%N)
        ((++count_all))

        logn "Running $( realpath --relative-to=. $test_path ) ..."

        # Tests are executed from their directory
        cd $test_dir

        # Run test
        $SHELL -x $test_file 2> $test_file.log 1>&2
        exit_code=$?

        # Check exit code
        if [ $exit_code -eq $EXIT_CODE_SUCCESS ]; then
            ((++count_passed))
            echo " OK"
        else
            ((++count_failed))
            tests_failed+=($test_path)
            echo " failed"
            success=false
        fi

        # Report time
        test_time_end=$(date +%s.%N)
        test_time=$(format_time $test_time_start $test_time_end)
        log "Test took $test_time"

        cd $APPRAISE_ROOT
    done
done

time_end=$(date +%s.%N)
time_total=$(format_time $time_start $time_end)


##########################################################################
# Clean up

# Restore the original development database in Appraise settings
test -e Appraise/settings.py.bak && mv Appraise/settings.py.bak Appraise/settings.py


##########################################################################
# Show summary
prev_log="$APPRAISE_TESTS_DIR/previous.log"
rm -f $prev_log

# Print failed tests
if [ -n "$tests_failed" ]; then
    echo "---------------------"
fi
[[ -z "$tests_failed" ]] || echo "Failed:" | tee -a $prev_log
for test_name in "${tests_failed[@]}"; do
    echo "  - $test_name" | tee -a $prev_log
done

# Print summary
echo "---------------------" | tee -a $prev_log
echo -n "Ran $count_all tests in $time_total, $count_passed passed, $count_failed failed" | tee -a $prev_log
echo "" | tee -a $prev_log

# Return exit code
$success && [ $count_all -gt 0 ]
