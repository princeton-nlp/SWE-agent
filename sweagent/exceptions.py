from typing import Any, Literal

"""This module contains all custom exceptions used by the SWE-agent."""


class FormatError(Exception):
    """Raised when the model response cannot properly be parsed into thought and actions."""


class FunctionCallingFormatError(FormatError):
    """Format error exception used by the function
    calling parser."""

    def __init__(
        self,
        message: str,
        error_code: Literal[
            "missing", "multiple", "incorrect_args", "invalid_json", "invalid_command", "missing_arg", "unexpected_arg"
        ],
        **extra_info: Any,
    ):
        super().__init__(message + f" [error_code={error_code}]")
        self.message = message
        self.extra_info = {"error_code": error_code, **extra_info}


class ContextWindowExceededError(Exception):
    """Raised when the context window of a LM is exceeded"""


class CostLimitExceededError(Exception):
    """Raised when we exceed a cost limit"""


class InstanceCostLimitExceededError(CostLimitExceededError):
    """Raised when we exceed the cost limit set for one task instance"""


class TotalCostLimitExceededError(CostLimitExceededError):
    """Raised when we exceed the total cost limit"""
