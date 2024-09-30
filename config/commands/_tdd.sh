# @yaml
# docstring: Reproduces the current bug by running a test that was designed to fail as long as the bug exists.
# tdd: true
tdd_repro() {
    # set -euo pipefail
    if [ -z "$TEST_CMD_FAIL_TO_PASS" ]; then
        echo "ERROR: env var \$TEST_CMD_FAIL_TO_PASS missing."
        exit 1
    fi
    pushd $REPO_ROOT > /dev/null
    echo -e "Running tests to reproduce the bug (from $PWD):\n >$TEST_CMD_FAIL_TO_PASS\n"
    eval "$TEST_CMD_FAIL_TO_PASS"

    # include the continuation file if it exists
    if [ -f "$MANUAL_INPUT_CONTINUATION_FILE" ]; then
        cat $MANUAL_INPUT_CONTINUATION_FILE
        rm $MANUAL_INPUT_CONTINUATION_FILE
    fi
    popd > /dev/null
}

# # @yaml
# # docstring: Run all tests to check for regressions. This might execute multiple individual test runs.
# # tdd: true
# tdd_run_all() {
#     # Assert that the file exists
#     if [ ! -f "$PASS_TO_PASS_FILE" ]; then
#         echo "ERROR: File $PASS_TO_PASS_FILE not found."
#         exit 1
#     fi

#     echo "tdd_run_all is disabled for now. Don't use it."
#     exit 1

#     # Read PASS_TO_PASS_FILE line by line and execute the command
#     while IFS= read -r line || [[ -n "$line" ]]; do
#         # Trim leading and trailing whitespace
#         line=$(echo "$line" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')
        
#         # Skip empty lines
#         if [ -n "$line" ]; then
#             eval "$TEST_CMD $line"
#         fi
#     done < "$PASS_TO_PASS_FILE"
# }
