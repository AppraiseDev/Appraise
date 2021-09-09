# Appraise regression tests

This directory contains regression tests based on data from `../Examples`.
Regression tests are currently supported on Unix machines only.

Warning: regression tests temporarily modify `Appraise/settings.py`, so run the
`run.sh` script with caution.


## Usage

First install Python development environment following instructions in ../INSTALL.md.
Then run:

    bash RegressionTests/run.sh

To run only tests from a specific subdirectory, provide a path to it as the
argument, for example:

    bash RegressionTests/run.sh RegressionTests/tests/examples

An example output looks like this:

    [07/19/2021 18:11:23] Running regression tests...
    [07/19/2021 18:11:23] Running RegressionTests/tests/examples/test_examples_direct.sh ... OK
    [07/19/2021 18:11:38] Test took 00:00:15.212s
    [07/19/2021 18:11:38] Running RegressionTests/tests/examples/test_examples_pairwise.sh ... OK
    [07/19/2021 18:11:51] Test took 00:00:12.851s
    ---------------------
    Ran 2 tests in 00:00:28.345s, 2 passed, 0 failed

Standard output and error of each test are written to `test_*.sh.log` file. Use
log files for debugging if a test fails, for example:

    less RegressionTests/tests/examples/test_examples_pairwise.sh.log


## Adding new tests

To add a new regression test, simply copy one of the existing tests and make
necessary changes. Name the test file following the convention `test_*.sh` and
it will be automatically picked by the `run.sh` script. When adding new tests,
make sure that the django-admin commands, `MakeAnnotation` in particular,
support necessary task types.


## Acknowledgements

The script `run.sh` is based on the `run_mrt.sh` script from
https://github.com/marian-nmt/marian-regression-tests
