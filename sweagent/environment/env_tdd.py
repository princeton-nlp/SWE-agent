from __future__ import annotations

from swebench.harness.constants import SWEbenchInstance
from swebench.harness.utils import get_test_directives

from sweagent.environment.tdd_verify import InstanceTestCategory, categorize_instance, verify_fail_to_pass


# The actual make_fail_to_pass_test_cmd function
def make_fail_to_pass_test_cmd(record: SWEbenchInstance, test_cmd: str) -> str:
    # Categorize the instance
    category = categorize_instance(record)

    # Verify arguments and parse tests
    fail_to_pass = verify_fail_to_pass(record)

    if not fail_to_pass:
        return test_cmd  # No tests to add

    if category == InstanceTestCategory.SymPy:
        fail_to_pass_files = get_test_directives(record)
        test_args = " ".join(fail_to_pass)
        return (
            f"bin/test -C --verbose -E -k {test_args} -- {' '.join(fail_to_pass_files)}"
        )
    else:
        separator = " " if test_cmd.endswith("--") else " -- "
        test_args = " ".join(fail_to_pass)
        return f"{test_cmd}{separator}{test_args}"


# Pre-process PASS_TO_PASS regression tests.
# TODO: Fix this so it runs correctly. Check for correct column entries, because not all rows have correct entries.
def make_pass_to_pass_test_cmd():
    # Problem: PASS_TO_PASS tests can be several hundred kb long which exceeds env var and shell command length limits.
    # pass_to_pass: list[str] = json.loads(self.record["PASS_TO_PASS"])
    # pass_to_pass_file = "/root/pass_to_pass.txt"
    # arg_max = int(self.communicate_with_handling("getconf ARG_MAX")) - 1000 # Give it some arbitrary leeway of 1000 characters.

    # # Take pass_to_pass tests and chunk them into larger chunks that each don't exceed arg_max.
    # chunks = []
    # current_line = ""
    # for test in pass_to_pass:
    #     test_length = len(test)
    #     if len(current_line) + test_length > arg_max:
    #         chunks.append(current_line)
    #         current_line = test
    #     else:
    #         current_line += f" {test}"
    # if current_line:
    #     chunks.append(current_line)

    # # Write the tests into multiple lines in pass_to_pass_file:
    # self.copy_string_to_container_file("\n".join(chunks), pass_to_pass_file)
    # self.communicate_with_handling(f"export PASS_TO_PASS_FILE={pass_to_pass_file}")
    pass
