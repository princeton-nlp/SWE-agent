# @yaml
# docstring: Reproduces the current bug by running a test that was designed to fail as long as the bug exists.
# tdd: true
tdd_repro() {
    # set -euo pipefail

    # TODO: better commands.
    extra_args="-E -k test_col_insert --tb"
    TEST_CMD="PYTHONWARNINGS='ignore::UserWarning,ignore::SyntaxWarning,ignore::DeprecationWarning' bin/test -C --verbose"
    # TEST_CMD="PYTHONWARNINGS='ignore::UserWarning,ignore::SyntaxWarning' bin/test -C --verbose"

    final_cmd="$TEST_CMD $extra_args $FAIL_TO_PASS"
    echo -e "Running tests to reproduce the bug:\n >$final_cmd\n"
    eval "$final_cmd"
}

# @yaml
# docstring: Run all tests to check for regressions. This might execute multiple individual test runs.
# tdd: true
tdd_run_all() {
    # Assert that the file exists
    if [ ! -f "$PASS_TO_PASS_FILE" ]; then
        echo "ERROR: File $PASS_TO_PASS_FILE not found."
        exit 1
    fi

    echo "tdd_run_all disabled for now."
    exit 1

    # Read PASS_TO_PASS_FILE line by line and execute the command
    while IFS= read -r line || [[ -n "$line" ]]; do
        # Trim leading and trailing whitespace
        line=$(echo "$line" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')
        
        # Skip empty lines
        if [ -n "$line" ]; then
            eval "$TEST_CMD $line"
        fi
    done < "$PASS_TO_PASS_FILE"
}
