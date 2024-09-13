from __future__ import annotations

import json
import re
from enum import Enum
from typing import Callable

from swebench.harness.constants import SWEbenchInstance

# These are the general categories for test_cmd from swebench's constants.py.
class InstanceTestCategory(Enum):
    SymPy = "sympy"
    PytestTox = "pytest_tox"
    Django = "django"
    Unsupported = "unsupported"


# ###########################################################################
# parse_* functions
# ###########################################################################


def parse_sympy_test(test: str) -> str:
    # Check that the test name is a valid Python function name and starts with 'test_'
    pattern = r"^test_[A-Za-z_][A-Za-z0-9_]*$"
    if re.match(pattern, test):
        return test
    raise ValueError(f"[TDD Failure] Invalid SymPy test format: '{test}'")


def parse_pytest_tox_test(test: str) -> str:
    # <file_path>::<python_identifier>
    pattern = r"^[\w./:_-]+(?:::[^\s]+)*$"
    if re.match(pattern, test):
        return test
    raise ValueError(f"[TDD Failure] Invalid pytest/tox test format: {test}")


def parse_django_test(test: str) -> str:
    pattern = r"^(\w+)\s+\(([\w_.]+)\)$"
    match = re.match(pattern, test)
    if match:
        test_name, class_name = match.groups()
        return f"{class_name}.{test_name}"
    raise ValueError(
        f"[TDD Failure] Invalid Django test format in `FAIL_TO_PASS`: '{test}'"
    )


# Map parse functions to InstanceTestCategory values
PARSE_FUNCTIONS: dict[InstanceTestCategory, Callable[[str], str]] = {
    InstanceTestCategory.SymPy: parse_sympy_test,
    InstanceTestCategory.PytestTox: parse_pytest_tox_test,
    InstanceTestCategory.Django: parse_django_test,
}


# ###########################################################################
# {@link categorize_instance}
# ###########################################################################


# NOTE: Most of this function is Claude-generated.
# I gave it swebench's `constants.py` and the original function that categorized by `test_cmd` instead.
def categorize_instance(record: SWEbenchInstance) -> InstanceTestCategory:
    repo = record.get("repo", "")
    if repo == "sympy/sympy":
        return InstanceTestCategory.SymPy
    elif repo == "django/django":
        return InstanceTestCategory.Django
    elif repo in [
        "scikit-learn/scikit-learn",
        "pallets/flask",
        "scipy/scipy",
        "pandas-dev/pandas",
        "pytest-dev/pytest",
        "matplotlib/matplotlib",
        "sphinx-doc/sphinx",
        "astropy/astropy",
        "pylint-dev/pylint",
        "pydata/xarray",
        "sqlfluff/sqlfluff",
        "dbt-labs/dbt-core",
        "pyvista/pyvista",
        "PyCQA/astroid",
        "marshmallow-code/marshmallow",
        "pvlib/pvlib-python",
        "pydicom/pydicom",
        "psf/requests",
    ]:
        return InstanceTestCategory.PytestTox
    else:
        raise ValueError(
            f"[TDD Failure] Unsupported repository for instance {record['instance_id']} in repo {record['repo']}. Check swebench's `constants.py`."
        )

# ###########################################################################
# {@link verify_fail_to_pass}
# ###########################################################################

# Function to verify all arguments and parse tests
def verify_fail_to_pass(record) -> list[str]:
    # Basic sanity checks.
    if "FAIL_TO_PASS" not in record:
        raise ValueError("[TDD Failure] Missing 'FAIL_TO_PASS' in record")
    try:
        fail_to_pass = json.loads(record["FAIL_TO_PASS"])
    except json.JSONDecodeError as e:
        raise ValueError(f"[TDD Failure] 'FAIL_TO_PASS' contains invalid JSON: {e} -- FAIL_TO_PASS='{record['FAIL_TO_PASS']}'")
    if not isinstance(fail_to_pass, list):
        raise ValueError("[TDD Failure] 'FAIL_TO_PASS' must be a list")
    if not fail_to_pass:
        raise ValueError("[TDD Failure] 'FAIL_TO_PASS' must not be empty")

    # Make sure that `FAIL_TO_PASS` can be passed for this instance.
    category = categorize_instance(record)
    parse_function = PARSE_FUNCTIONS.get(category)
    if not parse_function:
        raise ValueError(
            f"[TDD Failure] Unsupported category '{category}' for validation"
        )
    parsed_tests = [parse_function(test) for test in fail_to_pass]
    return parsed_tests
