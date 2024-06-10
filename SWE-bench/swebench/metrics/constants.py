from enum import Enum

# Result Categories
FAIL_TO_PASS = "FAIL_TO_PASS"
FAIL_TO_FAIL = "FAIL_TO_FAIL"
PASS_TO_PASS = "PASS_TO_PASS"
PASS_TO_FAIL = "PASS_TO_FAIL"

# Test Status Enum
class TestStatus(Enum):
    FAILED = "FAILED"
    PASSED = "PASSED"
    SKIPPED = "SKIPPED"
    ERROR = "ERROR"

# Resolved Status Enum
class ResolvedStatus(Enum):
    NO = "RESOLVED_NO"
    PARTIAL = "RESOLVED_PARTIAL"
    FULL = "RESOLVED_FULL"
