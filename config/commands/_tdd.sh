# @yaml
# docstring: Reproduces the current bug by running a test that was designed to fail as long as the bug exists.
repro_bug() {
    $TEST_CMD $FAIL_TO_PASS
}

# @yaml
# docstring: Run all tests to check for regressions. This might execute multiple individual test runs.
run_all_tests() {
    # Assert that the file exists
    if [ ! -f "$PASS_TO_PASS_FILE" ]; then
        echo "ERROR: File $PASS_TO_PASS_FILE not found."
        exit 1
    fi

    # Read PASS_TO_PASS_FILE line by line and execute the command
    while IFS= read -r line || [[ -n "$line" ]]; do
        # Trim leading and trailing whitespace
        line=$(echo "$line" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')
        
        # Skip empty lines
        if [ -n "$line" ]; then
            $TEST_CMD "$line"
        fi
    done < "$PASS_TO_PASS_FILE"
}
