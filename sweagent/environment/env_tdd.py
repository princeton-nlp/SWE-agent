from __future__ import annotations

import json
import re

from swebench.harness.constants import SWEbenchInstance
from swebench.harness.utils import get_test_directives


def parse_django_test(test: str) -> str:
    pattern = r'^(\w+)\s+\(([\w_.]+)\)$'
    match = re.match(pattern, test)
    if match:
        test_name, class_name = match.groups()
        return f"{class_name}.{test_name}"
    raise ValueError(f"Invalid Django test format in `FAIL_TO_PASS`: '{test}'")

def parse_pytest_tox_test(test: str) -> str:
    pattern = r'^[\w./:_-]+(::\w+)*$'
    if re.match(pattern, test):
        return test
    raise ValueError(f"Invalid pytest/tox test format: {test}")

def make_fail_to_pass_test_cmd(record: SWEbenchInstance, test_cmd: str) -> str:
    fail_to_pass = json.loads(record["FAIL_TO_PASS"])
    repo = record["repo"]

    if not fail_to_pass:
        return test_cmd

    if repo == "sympy/sympy":
        fail_to_pass_files = get_test_directives(record)
        return f"bin/test -C --verbose -E -k {' '.join(fail_to_pass)} -- {' '.join(fail_to_pass_files)}"
    else:
        command = test_cmd.split()[0]
        if command == "pytest" or command == "tox":
            # NOTE: Most repos fall into this bracket.
            # NOTE2: This might not work for all of tox, but of swebench repos, only sphinx uses tox, and that should work.
            test_args = " ".join(parse_pytest_tox_test(test) for test in fail_to_pass)
        elif repo == "django/django":
            test_args = " ".join(parse_django_test(test) for test in fail_to_pass)
        else:
            raise ValueError(f"Unsupported repo '{repo}' - don't know how to run these tests: {test_cmd}")
        
        separator = " " if test_cmd.endswith("--") else " -- "
        return f"{test_cmd}{separator}{test_args}"


def make_pass_to_pass_test_cmd():
    # TODO: Pre-process PASS_TO_PASS regression tests.
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
