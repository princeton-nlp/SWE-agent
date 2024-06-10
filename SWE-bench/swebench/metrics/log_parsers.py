import re

from swebench.metrics.constants import TestStatus


def parse_log_pytest(log: str) -> dict:
    """
    Parser for test logs generated with PyTest framework

    Args:
        log (str): log content
    Returns:
        dict: test case to test status mapping
    """
    test_status_map = {}
    for line in log.split("\n"):
        if any([line.startswith(x.value) for x in TestStatus]):
            # Additional parsing for FAILED status
            if line.startswith(TestStatus.FAILED.value):
                line = line.replace(" - ", " ")
            test_case = line.split()
            if len(test_case) <= 1:
                continue
            test_status_map[test_case[1]] = test_case[0]
    return test_status_map


def parse_log_pytest_options(log: str) -> dict:
    """
    Parser for test logs generated with PyTest framework with options

    Args:
        log (str): log content
    Returns:
        dict: test case to test status mapping
    """
    option_pattern = re.compile(r'(.*?)\[(.*)\]')
    test_status_map = {}
    for line in log.split("\n"):
        if any([line.startswith(x.value) for x in TestStatus]):
            # Additional parsing for FAILED status
            if line.startswith(TestStatus.FAILED.value):
                line = line.replace(" - ", " ")
            test_case = line.split()
            if len(test_case) <= 1:
                continue
            has_option = option_pattern.search(test_case[1])
            if has_option:
                main, option = has_option.groups()
                if option.startswith('/') and not option.startswith('//') and '*' not in option:
                    option = "/" + option.split('/')[-1]
                test_name = f'{main}[{option}]'
            else:
                test_name = test_case[1]
            test_status_map[test_name] = test_case[0]
    return test_status_map


def parse_log_django(log: str) -> dict:
    """
    Parser for test logs generated with Django tester framework

    Args:
        log (str): log content
    Returns:
        dict: test case to test status mapping
    """
    test_status_map = {}
    lines = log.split("\n")
    for line in lines:
        line = line.strip()
        if line.endswith(" ... ok"):
            test = line.split(" ... ok")[0]
            test_status_map[test] = TestStatus.PASSED.value
        if " ... skipped" in line:
            test = line.split(" ... skipped")[0]
            test_status_map[test] = TestStatus.SKIPPED.value
        if line.endswith(" ... FAIL"):
            test = line.split(" ... FAIL")[0]
            test_status_map[test] = TestStatus.FAILED.value
        if line.startswith("FAIL:"):
            test = line.split()[1].strip()
            test_status_map[test] = TestStatus.FAILED.value
        if line.endswith(" ... ERROR"):
            test = line.split(" ... ERROR")[0]
            test_status_map[test] = TestStatus.ERROR.value
        if line.startswith("ERROR:"):
            test = line.split()[1].strip()
            test_status_map[test] = TestStatus.ERROR.value
    return test_status_map


def parse_log_pytest_v2(log):
    """
    Parser for test logs generated with PyTest framework (Later Version)

    Args:
        log (str): log content
    Returns:
        dict: test case to test status mapping
    """
    test_status_map = {}
    escapes = "".join([chr(char) for char in range(1, 32)])
    for line in log.split("\n"):
        line = re.sub(r"\[(\d+)m", "", line)
        translator = str.maketrans("", "", escapes)
        line = line.translate(translator)
        if any([line.startswith(x.value) for x in TestStatus]):
            if line.startswith(TestStatus.FAILED.value):
                line = line.replace(" - ", " ")
            test_case = line.split()
            test_status_map[test_case[1]] = test_case[0]
    return test_status_map


def parse_log_seaborn(log):
    """
    Parser for test logs generated with seaborn testing framework

    Args:
        log (str): log content
    Returns:
        dict: test case to test status mapping
    """
    test_status_map = {}
    for line in log.split("\n"):
        if line.startswith(TestStatus.FAILED.value):
            test_case = line.split()[1]
            test_status_map[test_case] = TestStatus.FAILED.value
        elif f" {TestStatus.PASSED.value} " in line:
            parts = line.split()
            if parts[1] == TestStatus.PASSED.value:
                test_case = parts[0]
                test_status_map[test_case] = TestStatus.PASSED.value
        elif line.startswith(TestStatus.PASSED.value):
            parts = line.split()
            test_case = parts[1]
            test_status_map[test_case] = TestStatus.PASSED.value
    return test_status_map


def parse_log_sympy(log):
    """
    Parser for test logs generated with Sympy framework

    Args:
        log (str): log content
    Returns:
        dict: test case to test status mapping
    """
    test_status_map = {}
    pattern = r"(_*) (.*)\.py:(.*) (_*)"
    matches = re.findall(pattern, log)
    for match in matches:
        test_case = f"{match[1]}.py:{match[2]}"
        test_status_map[test_case] = TestStatus.FAILED.value
    for line in log.split("\n"):
        line = line.strip()
        if line.startswith("test_"):
            if line.endswith(" E"):
                test = line.split()[0]
                test_status_map[test] = TestStatus.ERROR.value
            if line.endswith(" F"):
                test = line.split()[0]
                test_status_map[test] = TestStatus.FAILED.value
            if line.endswith(" ok"):
                test = line.split()[0]
                test_status_map[test] = TestStatus.PASSED.value
    return test_status_map


parse_log_astroid = parse_log_pytest
parse_log_flask = parse_log_pytest
parse_log_marshmallow = parse_log_pytest
parse_log_matplotlib = parse_log_pytest
parse_log_pvlib = parse_log_pytest
parse_log_pyvista = parse_log_pytest
parse_log_sqlfluff = parse_log_pytest
parse_log_xarray = parse_log_pytest

parse_log_pydicom = parse_log_pytest_options
parse_log_requests = parse_log_pytest_options
parse_log_pylint = parse_log_pytest_options

parse_log_astropy = parse_log_pytest_v2
parse_log_scikit = parse_log_pytest_v2
parse_log_sphinx = parse_log_pytest_v2


MAP_REPO_TO_PARSER = {
    "astropy/astropy": parse_log_astropy,
    "django/django": parse_log_django,
    "marshmallow-code/marshmallow": parse_log_marshmallow,
    "matplotlib/matplotlib": parse_log_matplotlib,
    "mwaskom/seaborn": parse_log_seaborn,
    "pallets/flask": parse_log_flask,
    "psf/requests": parse_log_requests,
    "pvlib/pvlib-python": parse_log_pvlib,
    "pydata/xarray": parse_log_xarray,
    "pydicom/pydicom": parse_log_pydicom,
    "pylint-dev/astroid": parse_log_astroid,
    "pylint-dev/pylint": parse_log_pylint,
    "pytest-dev/pytest": parse_log_pytest,
    "pyvista/pyvista": parse_log_pyvista,
    "scikit-learn/scikit-learn": parse_log_scikit,
    "sqlfluff/sqlfluff": parse_log_sqlfluff,
    "sphinx-doc/sphinx": parse_log_sphinx,
    "sympy/sympy": parse_log_sympy,
}
