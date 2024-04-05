#!/usr/bin/env python3
import sys
import os

def print_flake8_output(input_string, show_line_numbers=False):
    for value in input_string.split("\n"):
        parts = value.split()
        if not show_line_numbers:
            print(f"- {' '.join(parts[1:])}")
        else:
            line_nums = ":".join(parts[0].split(":")[1:])
            print(f"- {line_nums} {' '.join(parts[1:])}")

def print_eslint_output(input_string: str, show_line_numbers=False):
    for value in input_string.split("\n")[:-2]:
        parts = value.split(":")
        [*msg, error] = parts[-1].strip().split()
        if not show_line_numbers:
            print(f"- {error} {' '.join(msg)}")
        else:
            line_nums = ":".join(value.split(":")[1:3])
            print(f"- {line_nums} {error} {' '.join(msg)}")

if __name__ == "__main__":
    lint_output = sys.argv[1]
    language = os.getenv("AGENT_LANG")
    match language:
        case "python":
            print_flake8_output(lint_output)
        case "javascript":
            print_eslint_output(lint_output)
        case _:  # default case
            pass