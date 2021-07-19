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
export APPRAISE_DATABASE=regressiontests.db
export APPRAISE_DB_NAME=default
export APPRAISE_EXAMPLES="$APPRAISE_ROOT/Examples"

log "Appraise root directory: $APPRAISE_ROOT"

# Set absolute path to python executable
export APPRAISE_PYTHON="$APPRAISE_ROOT/venv/bin/python3"
export APPRAISE_MANAGE="$APPRAISE_PYTHON $APPRAISE_ROOT/manage.py"
log "Python executable: $APPRAISE_PYTHON"

if ! test -f $APPRAISE_PYTHON; then
    echo "Python environment not found. Did you run install.sh?"
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

# Exit codes
export EXIT_CODE_SUCCESS=0

success=true
count_all=0
count_failed=0
count_passed=0

time_start=$(date +%s.%N)

log "Running regression tests..."
for test_path in $(ls $APPRAISE_TESTS_DIR/tests/test_*.sh); do
    test_dir=$( dirname $test_path )
    test_file=$( basename $test_path )

    # Tests are executed from their directory
    cd $test_dir

    logn "Running $( realpath --relative-to=. $test_path ) ..."
    test_time_start=$(date +%s.%N)
    ((++count_all))

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

    cd $APPRAISE_ROOT

    # Report time
    test_time_end=$(date +%s.%N)
    test_time=$(format_time $test_time_start $test_time_end)
    log "Test took $test_time"
done

time_end=$(date +%s.%N)
time_total=$(format_time $time_start $time_end)


##########################################################################
# Clean up

# Restore the original development database in Appraise settings
test -e Appraise/settings.py.bak && mv Appraise/settings.py.bak Appraise/settings.py


##########################################################################
# Print summary
prev_log="$APPRAISE_TESTS_DIR/previous.log"
rm -f $prev_log

echo "---------------------" | tee -a $prev_log
echo -n "Ran $count_all tests in $time_total, $count_passed passed, $count_failed failed" | tee -a $prev_log
echo "" | tee -a $prev_log

# Return exit code
$success && [ $count_all -gt 0 ]
